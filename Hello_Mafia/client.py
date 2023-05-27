from __future__ import print_function

import socket
import sys
import grpc
import package.proto.mafiaRPC_pb2_grpc as mafiaGRPC
from package.proto.mafiaRPC_pb2 import Player, Request, PlayerId, Response, Status, SUCCESS, FAIL
from optparse import OptionParser

default_player_name = sys.platform


def start_session(stub, player_name):
    response: PlayerId = stub.GetNewPlayerId(Request(message=''))
    if player_name == default_player_name:
        player_name = f'Guest_{response.id}'
    print(f'New player with name {player_name} and id {response.id}')
    host_address = socket.gethostbyname(socket.gethostname())
    player = Player(id=response.id, name=player_name, address=host_address)
    for event in stub.Subscribe(player):
        print(event.data)
    print('END!')
    print(response)
    response: Response = stub.Unsubscribe(player)
    print('Response status: ', response.status)


def run(address: str, port: str, player_name: str):
    with grpc.insecure_channel(f'{address}:{port}') as channel:
        stub = mafiaGRPC.MafiaClientStub(channel)
        start_session(stub, player_name)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-a", "--address", dest="address", default='localhost',
                      help='connect to server using custom address')
    parser.add_option("-p", "--port", dest="port", default='5345',
                      help='connect to server using custom port')
    parser.add_option("-n", "--name", dest="name", default=default_player_name,
                      help='set player name')

    (options, args) = parser.parse_args()
    print(options)
    run(options.address, options.port, options.name)
