import sys
import grpc
import package.proto.mafiaRPC_pb2_grpc as mafiaGRPC
from package.proto.mafiaRPC_pb2 import Player, PlayerId, Response, Status, SUCCESS, FAIL
from concurrent import futures
from package.idgenerator import IdGenerator, EXTEND_COEF
import logging
import threading
from package.game_manager import *

FORMAT = '%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)


thread_amount = 10
game_event_queue = EventQueue()


class MafiaClientServicer(mafiaGRPC.MafiaClientServicer):
    def __init__(self):
        self.id_generator = IdGenerator()
        self.cond_var = threading.Condition()
        self.event_queue_lock = threading.Lock()
        self.add_event_barrier = None
        self.event_queue = []  # Players queue
        self.player_manager = PlayerManager()

    def GetNewPlayerId(self, request, context):
        logger.info('New player id required')
        new_id = self.id_generator.get_id()
        logger.debug(f'Returned player id value: {new_id}')
        return PlayerId(id=new_id)

    def SetBarier(self, n: int):
        self.add_event_barrier = threading.Barrier(n, action=game_event_queue.get_event)

    def Subscribe(self, request: Player, context):
        logger.info(f'New player with name {request.name} and id {request.id} is subscribing: {request}')
        self.player_manager.add_player(request)
        notifier = self.player_manager.get_player_notifier(request.id)
        game_event_queue.add_event(request.id, event=AddPlayerEvent(request.name, request.id, notifier, self.SetBarier))

        while True:
            with notifier:
                notifier.wait()
            logger.debug('')
            #if len(self.event_queue) == 0:
                #return Response(data="OK", status=SUCCESS)
            response = game_event_queue.get_event(request.id).run()
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
