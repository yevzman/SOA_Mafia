from __future__ import print_function


import socket
import sys
import time
import random

import grpc
import threading
import package.proto.mafiaRPC_pb2_grpc as mafiaGRPC
from package.proto.mafiaRPC_pb2 import *
from optparse import OptionParser
from enum import Enum

import pyaudio
import wave
from rstream import Producer, Consumer, amqp_decoder, AMQPMessage, MessageContext, OffsetType, ConsumerOffsetSpecification
import asyncio
import traceback
import queue

host = ''
fs = 33000
chunk = 1024
name = 'no_name'
stop_communication = 0
stop_messages = 0
messages = queue.Queue()
q_offset = 0

async def publish(user, password, seconds, channel):
    global host, fs, chunk, name, stop_communication, messages
    # print('start publisher with channel name:', channel)
    async with Producer(
      host=host,
      port=5552,
      username='guest',
      password='guest',
    ) as producer:
        await producer.create_stream(channel, exists_ok=True)
        # print('len of queue:', len(messages))
        while not messages.empty() and not stop_communication:
            await producer.send(channel, AMQPMessage(
                body= name + ': ' + messages.get()
            ))
            time.sleep(0)
            


async def on_message(msg: bytes, message_context: MessageContext):
    global name, q_offset
    q_offset += 1
    # print('got message')
    if str(msg)[:len(name) + 2] == name + ': ':
        return
    print()
    print(msg)
    time.sleep(0)



async def consume(user, password, seconds, channel):
    global host, fs, chunk, q_offset
    consumer = Consumer(
        host=host,
        port=5552,
        username='guest',
        password='guest',
    )
    await consumer.start()
    await consumer.subscribe(channel, on_message, 
                             decoder=amqp_decoder,
                             offset_specification=ConsumerOffsetSpecification(OffsetType.OFFSET, q_offset))
    c_task = consumer.run()
    await asyncio.wait_for(c_task, timeout=0.5)
    consumer.close()


# async def start_communication(params: CommunicationParams):
#     get_msg_task = asyncio.create_task(
#         publish(params.user, params.password, params.timeout, params.channel))
#     send_msg_task = asyncio.create_task(
#         consume(params.user, params.password, params.timeout, params.channel))
#     t1 = asyncio.wait_for(get_msg_task, timeout=params.timeout)
#     t2 = asyncio.wait_for(send_msg_task, timeout=params.timeout)
#     await t1
#     await t2


def start_get_messages(params: CommunicationParams):
    try:
        asyncio.run(
            consume(params.user, params.password, params.timeout, params.channel))
    except:
        return

def start_send_messages(params: CommunicationParams):
    try:
        asyncio.run(
            publish(params.user, params.password, params.timeout, params.channel))
    except:
        return

def make_messages():
    global stop_messages, name, messages
    while not stop_messages:
        msg = input(name + ': ')
        if msg.strip().rstrip() != '':
            messages.put(msg)
        time.sleep(0.02)
        time.sleep(0)

def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()


default_bot_name = sys.platform
connection_status = 1


class GameStatus(Enum):
    STARTED = 1
    DAY_VOTE = 2
    NIGHT = 3
    NO_STATUS = 4


game_status = GameStatus.NO_STATUS


def start_notifier(stub, player, as_bot):
    global game_status, stop_communication, stop_messages
    session_id = -1
    try:
        for event in stub.Subscribe(player):
            event: Response = event
            # print(event)
            if game_status != GameStatus.STARTED:
                print()
            print(event.data, flush=True)
            if event.status == START_GAME:
                game_status = GameStatus.STARTED
                session_id = int(event.data.split('\n')[1].split(': ')[1])
            elif event.status == DAY_VOTE or event.status == NIGHT_VOTE:
                while True:
                    player_id = -1
                    if not as_bot:
                        while True:
                            try:
                                player_id = int(input('Write player id you want to vote: '))
                            except:
                                print()
                                continue
                            break
                    else:
                        rand_player = random.choice(str(event.data).split('chose {')[1].split('} using')[0].split(', '))
                        player_id, player_name = tuple(rand_player.split(':'))
                        player_id = int(player_id)
                        print(f'Vote for player {player_id}, {player_name}')
                    response = stub.SendVote(VoteRequest(player_id=player_id, session_id=session_id))
                    if response.status == SUCCESS:
                        break
                    print('Bad value. Try again!', flush=True)
            elif event.status == START_COMMUNICATION:
                print('Communiacation started:')
                params: CommunicationParams = event.communication
                stop_messages = 0
                make_msg_thread = threading.Thread(target=make_messages, args=())
                make_msg_thread.start()
                for i in range(params.timeout):
                    # print('new cycle of import')
                    stop_communication = 0
                    send_thread = threading.Thread(target=start_send_messages, args=(params,))
                    send_thread.start()
                    time.sleep(0.5)
                    stop_communication = 1
                    send_thread.join()
                    stop_communication = 0

                    get_thread = threading.Thread(target=start_get_messages, args=(params,))
                    get_thread.start()
                    get_thread.join()
                stop_messages = 1
                make_msg_thread.join()
            elif event.status == END_GAME:
                game_status = GameStatus.NO_STATUS
                return
            if connection_status == 0:
                return
    except Exception as error:
        print(traceback.format_exc())
        print('Exception occured')
        print(error)


def start_session(stub, player_name, as_bot):
    global game_status, name
    response: PlayerId = stub.GetNewPlayerId(Request(message=''))
    if player_name == default_bot_name:
        player_name = f'Bot_{response.id}'
        name = player_name
        print(f'Your name is {player_name}')
    # print(f'New player with name {player_name} and id {response.id}')
    host_address = socket.gethostbyname(socket.gethostname())
    player = Player(id=response.id, name=player_name, address=host_address)
    notifier_thread = None
    while True:
        ans = 'no'
        if not as_bot:
            ans = input('If you want join the game, write \'yes\', or \'no\' to quit the game: ')
        if ans == 'yes' or as_bot:
            print('Please wait. When 4 players join the server, game will start!')
            notifier_thread = threading.Thread(target=start_notifier, args=(stub, player, as_bot,))
            notifier_thread.start()
            while game_status == GameStatus.NO_STATUS:
                if not as_bot:
                    quit_ans = input('If you want leave game, write \'quit\': ')
                    if quit_ans == 'quit':
                        stub.Unsubscribe(player)
            notifier_thread.join()
            stub.Unsubscribe(player)
        elif ans == 'no':
            response: Response = stub.Unsubscribe(player)
            print('Response status: ', response.status)
            return

def fflusher():
    sys.stdout.flush()
    time.sleep(1)


def run(address: str, port: str, player_name: str, as_bot: bool):
    global host
    host = address
    with grpc.insecure_channel(f'{address}:{port}') as channel:
        stub = mafiaGRPC.MafiaClientStub(channel)
        start_session(stub, player_name, as_bot)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-a", "--address", dest="address", default='localhost',
                      help='connect to server using custom address')
    parser.add_option("-p", "--port", dest="port", default='5345',
                      help='connect to server using custom port')
    parser.add_option("-b", "--as-bot", action='store_true', dest="as_bot", default=False,
                      help='if this option included, then client will run as Bot (automotive management)')
    (options, args) = parser.parse_args()
    if not options.as_bot:
        name = input('Please input your name: ')
    else:
        name = default_bot_name
    fflusher_thread = threading.Thread(target=fflusher, args=())
    fflusher_thread.start()
    run(options.address, options.port, name, options.as_bot)

