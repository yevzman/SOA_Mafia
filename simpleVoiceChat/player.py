import pyaudio
import wave
from rstream import Consumer, amqp_decoder, AMQPMessage, MessageContext
import asyncio
import codecs


async def on_message(msg: bytes, message_context: MessageContext):
    global stream, wf
    stream.write(msg)
    wf.writeframes(msg)


async def consume():
    consumer = Consumer(
        host='127.0.0.1',
        port=5552,
        username='guest',
        password='guest',
    )
    await consumer.start()
    await consumer.subscribe('mystream', on_message)
    await consumer.run()


p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paInt16,
                channels=2,
                rate=33000,
                output=True)


wf = wave.open('output.wav', 'wb')
wf.setnchannels(2)
wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
wf.setframerate(33000)

asyncio.run(consume())

wf.close()


