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
        if self.id_generator.count_active_players() > 1:
            with notifier:
                logger.debug(f'Insert event: {event_data}')
                logger.debug(f'Active Players: {self.id_generator.count_active_players()}')
                self.event_queue_lock.acquire()
                self.event_queue.append(event_data)
                self.event_queue_lock.release()
                players = self.player_manager.get_all_players()
                logger.debug(f'Players length: {len(players)}')
                logger.debug(f'Players: {players}')
                self.add_event_barrier = threading.Barrier(len(players) - 1, action=self.RemoveEventFromQueue)
                for id in players:
                    if id != player_id:
                        self.player_manager.notify_player(id)

    def GetNewPlayerId(self, request, context):
        logger.info('New player id required')
        new_id = self.id_generator.get_id()
        logger.debug(f'Returned player id value: {new_id}')
        return PlayerId(id=new_id)

    def Subscribe(self, request: Player, context):
        logger.info(f'New player with name {request.name} and id {request.id} is subscribing: {request}')
        self.player_manager.add_player(request)
        notifier = self.player_manager.get_player_notifier(request.id)
        self.InsertEventIntoQueue(f'New player {request.name} has joined the server', request.id, notifier)

        while True:
            with notifier:
                notifier.wait()
            logger.debug('')
            if len(self.event_queue) == 0:
                return Response(data="OK", status=SUCCESS)
            response = Response(data=self.event_queue[0], status=SUCCESS)
            self.add_event_barrier.wait()
            yield response

    def Unsubscribe(self, request: Player, context) -> Response:
        logger.info(f'Player with id {request.id} is unsubscribing from server!')
        if not self.player_manager.is_player_exist(request.id):
            return Response(data="Such player does not exists!", status=FAIL)
        notifier = self.player_manager.get_player_notifier(request.id)
        self.InsertEventIntoQueue(f'Player {request.name} left server!', request.id, notifier)
        self.player_manager.notify_player(request.id)
        self.id_generator.add_id(request.id)
        self.player_manager.delete_player(request.id)
        return Response(data="OK", status=SUCCESS)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=thread_amount))
    mafiaGRPC.add_MafiaClientServicer_to_server(MafiaClientServicer(), server)
    server.add_insecure_port('[::]:5345')
    logger.debug('Starting server on port 5345')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
