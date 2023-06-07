import sys
import grpc
from .proto import mafiaRPC_pb2_grpc as mafiaGRPC
from .proto.mafiaRPC_pb2 import Player, PlayerId, Response, Status, SUCCESS, FAIL
from concurrent import futures
from .idgenerator import IdGenerator, EXTEND_COEF
import logging
import threading
import random
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor

FORMAT = '%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class MafiaRole(Enum):
    MAFIA = 1
    DOCTOR = 2
    CITIZEN = 3


class Event:
    def run(self):
        raise 'Unimplemented function'


class EventQueue(metaclass=Singleton):
    # Singleton event queue
    def __init__(self):
        self.event_queue: dict[int: list[Event]] = []
        self.lock = threading.Lock()

    def add_event(self, player_id: int, event: Event):
        with self.lock:
            if player_id not in self.event_queue:
                self.event_queue[player_id] = []
            self.event_queue[player_id].append(event)

    def get_event(self, player_id):
        with self.lock:
            event = self.event_queue[player_id].pop(0)
            return event


class AddPlayerEvent(Event):
    def __init__(self, player_name, player_id, notifier, _callback):
        self.event_data = f'New player {player_name} has joined the server'
        self.player_notifier = notifier
        self.player_id = player_id
        self.callback = _callback

    def run(self):
        with self.notifier:
            self.callback(len(players) - 1)

            for id in players:
                if id != self.player_id:
                    self.player_manager.notify_player(id)

            return self.event_data


class RoleDistributionEvent(Event):
    def __init__(self, _role):
        self.role = _role

    def run(self):
        return Response(data=f'Your role is {self.role}')


class MorningNotificationEvent(Event):
    def __init__(self, died_player):
        pass

    def run(self):
        pass


class DayEvent(Event):
    def run(self):
        pass


class NightEvent(Event):
    def run(self):
        pass


class MafiaWakeUpEvent(Event):
    def run(self):
        pass


class DoctorWakeUpEvent(Event):
    def run(self):
        pass


class PlayerManager:
    def __init__(self):
        self.player_dict: dict[int, Player] = dict()
        self.player_notifiers: list[threading.Condition] = [threading.Condition() for i in range(1, 5, 1)]
        self.lock = threading.Lock()
        self.session_maker = SessionMaker(self)

    def __extend_notifier_list__(self):
        old_len = len(self.player_notifiers)
        new_len = int(old_len * EXTEND_COEF)
        for i in range(old_len, new_len, 1):
            self.player_notifiers.append(threading.Condition())

    def add_player(self, _player: Player):
        with self.lock:
            logger.debug(f'Player with name {_player.name} and id {_player.id} is adding into PlayerManager')
            self.player_dict[_player.id] = _player
            if _player.id >= len(self.player_notifiers):
                self.__extend_notifier_list__()
            self.session_maker.add_new_player(_player)

    def is_player_exist(self, player_id):
        return self.player_dict.get(player_id, None) is not None

    def delete_player(self, player_id):
        with self.lock:
            logger.debug(f'Player with id {player_id} is deleting from PlayerManager')
            if self.is_player_exist(player_id):
                self.session_maker.delete_player(player_id)
                self.player_dict.pop(player_id)
                self.player_notifiers[player_id] = threading.Condition()

    def get_player_notifier(self, player_id):
        if self.is_player_exist(player_id):
            return self.player_notifiers[player_id]

    def notify_player(self, player_id):
        logger.debug(f'Notify player with id {player_id}')
        with self.player_notifiers[player_id]:
            self.player_notifiers[player_id].notify_all()

    def get_all_players(self):
        return self.player_dict


class SessionMaker:
    def __init__(self, _player_manager):
        self.player_queue: list[Player] = list()
        self.player_manager = _player_manager
        self.lock = threading.Lock()
        self.NEED_PLAYER = 6
        self.MAX_SESSIONS = 5
        self.CURRENT_AMOUNT_SESSION = 0
        self.notifier = threading.Condition()
        session_maker_t = threading.Thread(target=self.try_create_new_session, args=(self.notifier,))
        session_maker_t.start()
        logger.debug('SessionMaker constructor')

    def after_session_end(self, future):
        with self.lock:
            self.CURRENT_AMOUNT_SESSION += 1
            res = future.result()
            for player in res:
                self.player_queue.append(player)

    def try_create_new_session(self, notifier: threading.Condition()):
        with ThreadPoolExecutor(max_workers=self.MAX_SESSIONS) as executor:
            with notifier:
                notifier.wait()
            if self.CURRENT_AMOUNT_SESSION < self.MAX_SESSIONS:
                players = []
                with self.lock:
                    self.CURRENT_AMOUNT_SESSION += 1
                    for i in range(self.NEED_PLAYER):
                        players.append(self.player_queue.pop())
                future = executor.submit(self.create_session, players)
                future.add_done_callback(self.after_session_end)

    def create_session(self, players):
        session_maker = SessionManager(players, self.player_manager)
        return session_maker.start_game()

    def add_new_player(self, _player: Player):
        logger.debug(f'New player {_player.name} added in SessionMaker')
        with self.lock:
            self.player_queue.append(_player)
            if len(self.player_queue) >= self.NEED_PLAYER:
                with self.notifier:
                    self.notifier.notify()

    def delete_player(self, _player_id):
        with self.lock:
            self.player_queue.remove(_player_id)


class SessionManager:
    def __init__(self, _players: list, _player_manager: PlayerManager):
        self.player_manger = _player_manager
        self.players = _players

        self.roles = dict()
        self.Citizens = []  # 3
        self.Mafias = []  # 2
        self.Doctor = []  # 1
        self.max_session_players = 6
        self.citizens_amount = 3
        self.mafias_amount = 2
        self.doctor_amount = 1

    def __notify_all_players(self):
        for player in self.players:
            notifier = self.player_manger.get_player_notifier(player)
            with notifier:
                notifier.notify()

    def __distribute_roles(self):
        event_queue = EventQueue()
        _players = self.players
        self.Mafias = random.choices(_players, k=self.mafias_amount)
        for player in self.Mafias:
            self.roles[player] = MafiaRole.MAFIA
            event_queue.add_event(player, RoleDistributionEvent('mafia'))
            del self.players[_players.index(player)]

        self.Citizens = random.choices(self.players, k=self.citizens_amount)
        for player in self.Citizens:
            self.roles[player] = MafiaRole.CITIZEN
            event_queue.add_event(player, RoleDistributionEvent('citizen'))
            del _players[_players.index(player)]
        self.Doctor = self.players
        self.roles[self.Doctor[0]] = MafiaRole.DOCTOR
        del _players[0]

        self.__notify_all_players()

    def start_game(self):
        self.__distribute_roles()

        # game events ...
        return self.players
