import sys
import grpc
import copy
from .proto import mafiaRPC_pb2_grpc as mafiaGRPC
from .proto.mafiaRPC_pb2 import *
from concurrent import futures
from .idgenerator import IdGenerator, EXTEND_COEF
import logging
import threading
import random
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import time

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
    CITIZEN = 2


def get_players_list_str(players: list):
    players_str = '{'
    for i in range(len(players)):
        player = players[i]
        players_str += str(player.id) + str(':') + str(player.name)
        if i + 1 != len(players):
            players_str += ', '
    players_str += '}'
    return players_str


class Event:
    def __init__(self, message):
        self.message = message

    def run(self) -> Response:
        return Response(data=self.message, status=SUCCESS)


class EventQueue(metaclass=Singleton):
    # Singleton event queue
    def __init__(self):
        self.event_queue: dict[int: list[Event]] = dict()
        self.session_action: dict[int: list[int]] = dict()
        self.session_action_lock = threading.Lock()
        self.lock = threading.Lock()

    def add_session_action(self, session_id, value):
        with self.session_action_lock:
            if session_id not in self.session_action:
                self.session_action[session_id] = []
            self.session_action[session_id].append(value)

    def get_session_actions(self, session_id):
        with self.session_action_lock:
            return self.session_action.get(session_id, [])

    def delete_session_actions(self, session_id):
        with self.session_action_lock:
            if session_id in self.session_action:
                self.session_action.pop(session_id)

    def add_event(self, player_id: int, event: Event):
        with self.lock:
            if player_id not in self.event_queue:
                self.event_queue[player_id] = []
            self.event_queue[player_id].append(event)

    def queue_has_any_event(self, player_id):
        return len(self.event_queue[player_id]) > 0

    def get_event(self, player_id):
        with self.lock:
            event = self.event_queue[player_id].pop(0)
            return event


class AddPlayerEvent(Event):
    def __init__(self, player_name, player_id):
        self.event_data = f'New player {player_name} has joined the server'
        self.player_id = player_id

    def run(self):
        return Response(status=SUCCESS, data=self.event_data)


class LeavePlayerEvent(Event):
    def __init__(self, player_name, player_id):
        self.event_data = f'Player {player_name} has left the server'
        self.player_id = player_id

    def run(self):
        return Response(status=SUCCESS, data=self.event_data)


class GameStartEvent(Event):
    def __init__(self, players, session_id):
        self.players = players
        self.players_str = get_players_list_str(players)
        self.session_id = session_id

    def run(self):
        return Response(data=f'Game Started!'
                             f'\nSession_ID: {self.session_id}'
                             f'\nPlayers: {self.players_str}', status=START_GAME)


class GameEndEvent(Event):
    def __init__(self, result):
        self.result = result

    def run(self):
        return Response(data=f'Game Ended.\n{self.result}', status=END_GAME)


class RoleDistributionEvent(Event):
    def __init__(self, _role):
        self.role = _role

    def run(self):
        return Response(data=f'Your role is {self.role}', status=ROLE_DISTRIBUTION)


class MorningNotificationEvent(Event):
    def __init__(self, killed_player):
        self.killed_player = killed_player

    def run(self):
        return Response(data=f'Mafia killed {self.killed_player}', status=MORNING_NOTIFICATION)


class VoteEvent(Event):
    def __init__(self, players, status):
        logger.debug(f'VoteEvent with status {status}')
        self.players = players
        self.players_str = get_players_list_str(players)
        self.status = status

    def run(self):
        return Response(data=f'Vote player you want to chose {self.players_str} using his ID', status=self.status)


class MafiaWakeUpEvent(Event):
    def run(self):
        pass


class PlayerManager:
    def __init__(self):
        self.player_dict: dict[int, Player] = dict()
        self.player_status: dict[int, int] = dict()
        self.player_notifiers: list[threading.Condition] = [threading.Condition() for i in range(1, 5, 1)]
        self.add_lock = threading.Lock()
        self.notify_lock = threading.Lock()
        self.session_maker = SessionMaker(self)

    def __extend_notifier_list__(self):
        old_len = len(self.player_notifiers)
        new_len = int(old_len * EXTEND_COEF)
        for i in range(old_len, new_len, 1):
            self.player_notifiers.append(threading.Condition())

    def add_player(self, _player: Player):
        with self.add_lock:
            self.player_status[_player.id] = False
            logger.debug(f'Player with name {_player.name} and id {_player.id} is adding into PlayerManager')
            self.player_dict[_player.id] = _player
            if _player.id >= len(self.player_notifiers):
                self.__extend_notifier_list__()
            self.session_maker.add_new_player(_player)

    def set_in_game_status(self, player_id: int):
        with self.add_lock:
            self.player_status[player_id] = True

    def set_not_in_game_status(self, player_id):
        with self.add_lock:
            self.player_status[player_id] = False

    def is_player_exist(self, player_id):
        return self.player_dict.get(player_id, None) is not None

    def delete_player(self, player_id):
        with self.add_lock:
            logger.debug(f'Player with id {player_id} is deleting from PlayerManager')
            if self.is_player_exist(player_id):
                self.session_maker.delete_player(self.player_dict[player_id])
                self.player_dict.pop(player_id)
                self.player_notifiers[player_id] = threading.Condition()
                self.player_status[player_id] = False

    def get_player_notifier(self, player_id):
        if self.is_player_exist(player_id):
            return self.player_notifiers[player_id]

    def notify_player(self, player_id, is_in_game):
        with self.notify_lock:
            if is_in_game == self.player_status[player_id]:
                logger.debug(f'Notify player with id {player_id}')
                with self.player_notifiers[player_id]:
                    self.player_notifiers[player_id].notify_all()

    def get_all_players(self):
        return self.player_dict


class SessionMaker:
    def __init__(self, _player_manager):
        self.player_queue: list[Player] = list()
        self.player_manager: PlayerManager = _player_manager
        self.lock = threading.Lock()
        self.NEED_PLAYER = 4
        self.MAX_SESSIONS = 4
        self.CURRENT_AMOUNT_SESSION = 0
        self.notifier = threading.Condition()
        self.executor = ThreadPoolExecutor(max_workers=self.MAX_SESSIONS)
        logger.debug('SessionMaker constructor')

    def after_session_end(self, future):
        logger.debug('GAME ENDED!')
        with self.lock:
            self.CURRENT_AMOUNT_SESSION += 1

    def try_create_new_session(self):
        if self.CURRENT_AMOUNT_SESSION < self.MAX_SESSIONS:
            players: list[Player] = []
            self.CURRENT_AMOUNT_SESSION += 1
            for i in range(self.NEED_PLAYER):
                players.append(self.player_queue.pop())
                logger.debug(f'set in_game status to player {players[-1].id}')
            future = self.executor.submit(self.create_session, players)
            future.add_done_callback(self.after_session_end)

    def create_session(self, players: list[Player]):
        time.sleep(1)
        for player in players:
            self.player_manager.set_in_game_status(player.id)
        session_maker = SessionManager(players, self.player_manager)
        return session_maker.start_game()

    def add_new_player(self, _player: Player):
        logger.debug(f'New player {_player.name} added in SessionMaker')
        with self.lock:
            self.player_queue.append(_player)
        if len(self.player_queue) >= self.NEED_PLAYER:
            logger.debug('Amount of players in queue is valid for creating new session')
            self.try_create_new_session()

    def delete_player(self, _player):
        with self.lock:
            if _player in self.player_queue:
                self.player_queue.remove(_player)


class SessionManager:
    def __init__(self, _players: list[Player], _player_manager: PlayerManager):
        self.player_manger: PlayerManager = _player_manager
        self.players: list[Player] = _players
        self.alive_players: list[Player] = copy.deepcopy(self.players)

        self.roles = dict()
        self.Citizens: list[Player] = []  # 3
        self.Mafias: list[Player] = []  # 1
        self.max_session_players = 4
        self.citizens_amount = 3
        self.mafias_amount = 1
        self.session_id = _players[0].id

    def __notify_all_alive_players(self):
        for player in self.alive_players:
            self.player_manger.notify_player(player.id, is_in_game=True)

    def __start_game_notify(self):
        event_queue = EventQueue()
        for player in self.players:
            event_queue.add_event(player.id, event=GameStartEvent(self.alive_players, self.session_id))
        self.__notify_all_alive_players()

    def __end_game_notify(self, result):
        event_queue = EventQueue()
        for player in self.alive_players:
            event_queue.add_event(player.id, event=GameEndEvent(result))
        self.__notify_all_alive_players()
        for player in self.alive_players:
            self.player_manger.set_not_in_game_status(player.id)

    def __start_day_notify(self):
        event_queue = EventQueue()
        for player in self.players:
            event_queue.add_event(player.id, event=Event('Day started!'))
        self.__notify_all_alive_players()

    def __start_night_notify(self):
        event_queue = EventQueue()
        for player in self.players:
            event_queue.add_event(player.id, event=Event('Night started!'))
        self.__notify_all_alive_players()

    def __distribute_roles(self):
        event_queue = EventQueue()
        _players = copy.deepcopy(self.players)
        self.Mafias = random.choices(_players, k=self.mafias_amount)
        for player in self.Mafias:
            self.roles[player.id] = MafiaRole.MAFIA
            event_queue.add_event(player.id, RoleDistributionEvent('MAFIA'))
            del _players[_players.index(player)]
        logger.debug('Mafias: ' + get_players_list_str(self.Mafias))
        self.Citizens = _players
        for player in self.Citizens:
            self.roles[player.id] = MafiaRole.CITIZEN
            event_queue.add_event(player.id, event=RoleDistributionEvent('CITIZEN'))
        logger.debug('Citizens: ' + get_players_list_str(self.Citizens))
        self.__notify_all_alive_players()

    def __day_vote(self):
        event_queue = EventQueue()
        for player in self.alive_players:
            event_queue.add_event(player.id, event=VoteEvent(self.alive_players, status=DAY_VOTE))
        self.__notify_all_alive_players()
        need_votes = len(self.alive_players)
        while len(event_queue.get_session_actions(session_id=self.session_id)) != need_votes:
            time.sleep(0)
            continue
        votes = event_queue.get_session_actions(session_id=self.session_id)
        event_queue.delete_session_actions(session_id=self.session_id)
        player_id = max(set(votes), key=votes.count)
        return player_id

    def __night_vote(self):
        event_queue = EventQueue()
        for player in self.Mafias:
            event_queue.add_event(player.id, event=VoteEvent(self.Citizens, status=NIGHT_VOTE))
        for player in self.Mafias:
            self.player_manger.notify_player(player.id, True)
        need_votes = len(self.Mafias)
        while len(event_queue.get_session_actions(session_id=self.session_id)) != need_votes:
            time.sleep(0)
            continue
        votes = event_queue.get_session_actions(session_id=self.session_id)
        event_queue.delete_session_actions(session_id=self.session_id)
        player_id = max(set(votes), key=votes.count)
        return player_id

    def __kill_player(self, player_id):
        event_queue = EventQueue()
        player = None
        for p in self.alive_players:
            if p.id == player_id:
                player = p
        logger.debug(f'Killed player: Name {player.name} Id {player.id}')
        event_queue.add_event(player_id, Event(f'You was killed!'))
        event_queue.add_event(player_id, event=GameEndEvent('You died!'))
        self.player_manger.notify_player(player_id, True)
        if player in self.Mafias:
            logger.debug('Delete Player from Mafias')
            del self.Mafias[self.Mafias.index(player)]
        else:
            logger.debug('Delete Player from Citizens')
            del self.Citizens[self.Citizens.index(player)]
        del self.alive_players[self.alive_players.index(player)]
        self.player_manger.set_not_in_game_status(player_id)
        for p in self.alive_players:
            event_queue.add_event(p.id, Event(f'Player {player.name} died!'))
        self.__notify_all_alive_players()

    def start_game(self):
        self.__start_game_notify()
        self.__distribute_roles()

        while 0 < len(self.Mafias) < len(self.Citizens):
            logger.debug(f'Mafias: {get_players_list_str(self.Mafias)}')
            logger.debug(f'Citizens: {get_players_list_str(self.Citizens)}')
            self.__start_day_notify()
            player_id = self.__day_vote()
            self.__kill_player(player_id)   # day vote results
            logger.debug(f'Mafias: {get_players_list_str(self.Mafias)}')
            logger.debug(f'Citizens: {get_players_list_str(self.Citizens)}')
            if len(self.Mafias) == 0 or len(self.Mafias) == len(self.Citizens):
                break
            self.__start_night_notify()
            player_id = self.__night_vote()
            self.__kill_player(player_id)  # night vote results
        result = None
        if len(self.Mafias) == 0:
            result = 'Citizens won the Game!'
        else:
            result = 'Mafia won the Game!'
        self.__end_game_notify(result=result)
        return self.players
