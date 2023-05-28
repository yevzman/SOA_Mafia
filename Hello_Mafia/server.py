import sys
import grpc
import package.proto.mafiaRPC_pb2_grpc as mafiaGRPC
from package.proto.mafiaRPC_pb2 import Player, PlayerId, Response, Status, SUCCESS, FAIL
from concurrent import futures
from package.idgenerator import IdGenerator, EXTEND_COEF
import logging
import threading

FORMAT = '%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)


thread_amount = 10


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
            self.player_dict[_player.id] = _player
            if _player.id >= len(self.player_notifiers):
                self.__extend_notifier_list__()

    def is_player_exist(self, player_id):
        return self.player_dict.get(player_id, None) is not None

    def delete_player(self, player_id):
        with self.lock:
            if self.is_player_exist(player_id):
                self.player_dict.pop(player_id)
                self.player_notifiers[player_id] = None

    def get_player_notifier(self, player_id):
        if self.is_player_exist(player_id):
            return self.player_notifiers[player_id]

    def notify_player(self, player_id):
        with self.player_notifiers[player_id]:
            self.player_notifiers[player_id].notify_all()

    def get_all_players(self):
        return self.player_dict


class MafiaClientServicer(mafiaGRPC.MafiaClientServicer):
    def __init__(self):
        self.id_generator = IdGenerator()
        self.cond_var = threading.Condition()
        self.event_queue_lock = threading.Lock()
        self.add_event_barrier = threading.Barrier(parties=thread_amount, action=self.RemoveEventFromQueue)
        self.event_queue = []  # Players queue
        self.player_manager = PlayerManager()

    def RemoveEventFromQueue(self):
        with self.event_queue_lock:
            logger.debug(f'All Events: {self.event_queue}')
            logger.debug(f'Remove Event: {self.event_queue[0]}')
            self.event_queue.pop()

    def InsertEventIntoQueue(self, event_data, player_id, notifier):
        logger.debug(f'Active Players: {self.id_generator.count_active_players()}')
        if self.id_generator.count_active_players() > 1:
            with notifier:
                self.event_queue_lock.acquire()
                self.event_queue.append(event_data)
                self.event_queue_lock.release()
                players = self.player_manager.get_all_players()
                for id in players:
                    if id != player_id:
                        self.player_manager.notify_player(id)
                self.RemoveEventFromQueue()

    def GetNewPlayerId(self, request, context):
        logger.info('New player id required!')
        new_id = self.id_generator.get_id()
        logger.debug(f'Returned player id value: {new_id}')
        return PlayerId(id=new_id)

    def Subscribe(self, request: Player, context):
        self.player_manager.add_player(request)
        notifier = self.player_manager.get_player_notifier(request.id)
        logger.info(f'New subscriber: {request}')
        self.InsertEventIntoQueue(f'New player {request.name} has joined the server', request.id, notifier)

        while True:
            with notifier:
                notifier.wait()
            response = Response(data=self.event_queue[0], status=SUCCESS)
            yield response

    def Unsubscribe(self, request: Player, context) -> Response:
        logger.info(f'Player with id {request.id} unsubscribed from server!')
        self.id_generator.add_id(request.id)
        self.InsertEventIntoQueue(f'Player {request.name} left server!')
        return Response(data="OK", status=SUCCESS)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=thread_amount))
    mafiaGRPC.add_MafiaClientServicer_to_server(MafiaClientServicer(), server)
    server.add_insecure_port('[::]:5345')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
