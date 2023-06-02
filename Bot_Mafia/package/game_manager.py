import sys
import grpc
import proto.mafiaRPC_pb2_grpc as mafiaGRPC
from proto.mafiaRPC_pb2 import Player, PlayerId, Response, Status, SUCCESS, FAIL
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


class MafiaRole(Enum):
    MAFIA = 1
    DOCTOR = 2
    CITIZEN = 3


class Event:
    def run(self):
        raise 'Unimplemented function'


class RoleDistributionEvent(Event):
    def run(self):
        pass


class MorningNotificationEvent(Event):
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

    def is_player_exist(self, player_id):
        return self.player_dict.get(player_id, None) is not None

    def delete_player(self, player_id):
        with self.lock:
            logger.debug(f'Player with id {player_id} is deleting from PlayerManager')
            if self.is_player_exist(player_id):
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
        self.lock = threading.Lock()
        self.NEED_PLAYER = 6
        self.MAX_SESSIONS = 5
        self.CURRENT_AMOUNT_SESSION = 0
        self.notifier = threading.Condition()
        session_maker_t = threading.Thread(target=self.try_create_new_session, args=(self.notifier,))

    def after_session_end(self, future):
        with self.lock:
            self.CURRENT_AMOUNT_SESSION += 1
            res = future.result()
            for player in res:
                self.player_queue.append()

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

    def add_new_player(self, _player: Player):
        with self.lock:
            self.player_queue.append(_player)
            if len(self.player_queue) >= self.NEED_PLAYER:
                with self.notifier:
                    self.notifier.notify()


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

        self.__distribute_roles()
        self.start_game()

    def __distribute_roles(self):
        self.Mafias = random.choices(self.players, k=self.mafias_amount)
        for player in self.Mafias:
            self.roles[player] = MafiaRole.MAFIA
            del self.players[self.players.index(player)]

        self.Citizens = random.choices(self.players, k=self.citizens_amount)
        for player in self.Citizens:
            self.roles[player] = MafiaRole.CITIZEN
            del self.players[self.players.index(player)]
        self.Doctor = self.players
        self.roles[self.Doctor[0]] = MafiaRole.DOCTOR
        del self.players[0]

    def start_game(self):
        pass
