import sys
import grpc
import package.proto.mafiaRPC_pb2_grpc as mafiaGRPC
from package.proto.mafiaRPC_pb2 import Player, PlayerId, Response, Status, SUCCESS, FAIL
from concurrent import futures
from package.idgenerator import IdGenerator
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
        self.add_event_barrier = threading.Barrier(parties=thread_amount, action=self.remove_event_from_queue)
        self.event_queue = []  # Players queue

    def remove_event_from_queue(self):

        self.event_queue.pop()

    def GetNewPlayerId(self, request, context):
        logger.info('New player id required!')
        new_id = self.id_generator.get_id()
        logger.debug(f'Returned player id value: {new_id}')
        return PlayerId(id=new_id)

    def Subscribe(self, request: Player, context):
        logger.info(f'New subscriber: {request}')

        if self.id_generator.count_active_players() > 1:
            with self.cond_var:
                self.event_queue.append(f'New player {request.name} has joined the server')
                self.cond_var.notify_all()

        while True:
            with self.cond_var:
                self.cond_var.wait()
            if self.event_queue[0].count(request.name):
                return self.Unsubscribe(request, context)
            response = Response(data=self.event_queue[0], status=SUCCESS)
            self.add_event_barrier.wait()
            self.add_event_barrier.reset()
            yield response

    def Unsubscribe(self, request: Player, context) -> Response:
        logger.info(f'Player with id {request.id} unsubscribed from server!')
        self.id_generator.add_id(request.id)
        if self.id_generator.count_active_players() > 1:
            with self.cond_var:
                self.event_queue.append(f'Player {request.name} left server!')
                self.cond_var.notify_all()
        return Response(data="OK", status=SUCCESS)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=thread_amount))
    mafiaGRPC.add_MafiaClientServicer_to_server(MafiaClientServicer(), server)
    server.add_insecure_port('[::]:5345')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
