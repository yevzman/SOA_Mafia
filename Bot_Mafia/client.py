from __future__ import print_function


import socket
import sys
import time

import grpc
import threading
import package.proto.mafiaRPC_pb2_grpc as mafiaGRPC
from package.proto.mafiaRPC_pb2 import *
from optparse import OptionParser
from enum import Enum


default_player_name = sys.platform
connection_status = 1


class GameStatus(Enum):
    STARTED = 1
    DAY_VOTE = 2
    NIGHT = 3
    NO_STATUS = 4


game_status = GameStatus.NO_STATUS


def start_notifier(stub, player):
    global game_status
    session_id = -1
    try:
        for event in stub.Subscribe(player):
            if game_status != GameStatus.STARTED:
                print()
            print(event.data, flush=True)
            if event.status == START_GAME:
                game_status = GameStatus.STARTED
                session_id = int(event.data.split('\n')[1].split(': ')[1])
            elif event.status == DAY_VOTE or event.status == NIGHT_VOTE:
                while True:
                    player_id = int(input('Write player id you want to vote: '))
                    response = stub.SendVote(VoteRequest(player_id=player_id, session_id=session_id))
                    if response.status == SUCCESS:
                        break
                    print('Bad value. Try again!', flush=True)
            elif event.status == END_GAME:
                game_status = GameStatus.NO_STATUS
                return
            if connection_status == 0:
                return
    except Exception:
        pass


def start_session(stub, player_name):
    global game_status
    response: PlayerId = stub.GetNewPlayerId(Request(message=''))
    if player_name == default_player_name:
        player_name = f'Guest_{response.id}'
    # print(f'New player with name {player_name} and id {response.id}')
    host_address = socket.gethostbyname(socket.gethostname())
    player = Player(id=response.id, name=player_name, address=host_address)
    notifier_thread = None
    while True:
        ans = input('If you want join the game, write \'yes\', or \'no\' to quit the game: ')
        if ans == 'yes':
            print('Please wait. When 4 players join the server, game will start!')
            notifier_thread = threading.Thread(target=start_notifier, args=(stub, player,))
            notifier_thread.start()
            while game_status == GameStatus.NO_STATUS:
                quit_ans = input('If you want leave game, write \'quit\': ')
                if quit_ans == 'quit':
                    stub.Unsubscribe(player)
            notifier_thread.join()
            stub.Unsubscribe(player)
        elif ans == 'no':
            response: Response = stub.Unsubscribe(player)
            print('Response status: ', response.status)
            return


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
    (options, args) = parser.parse_args()
    name = input('Please input your name: ')
    run(options.address, options.port, name)

