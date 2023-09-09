import pyaudio
import wave
from rstream import Producer, AMQPMessage
import asyncio


async def publish():
    global frames, stream
    async with Producer(
      host='localhost',
      port=5552,
      username='voicechat',
      password='ZZZxxx123'
    ) as producer:
        await producer.create_stream('mystream_new', exists_ok=True)
        for i in range(0, int(fs / chunk * seconds)):
            data = stream.read(chunk)
            frames.append(data)
            await producer.send('mystream', AMQPMessage(
                body=data
            ))


chunk = 1024  # Record in chunks of 1024 samples
sample_format = pyaudio.paInt16  # 16 bits per sample
channels = 2
fs = 33000  # Record at 44100 samples per second
seconds = 10
filename = "input.wav"

p = pyaudio.PyAudio()

print('Recording')

stream = p.open(format=sample_format,
                channels=channels,
                rate=fs,
                frames_per_buffer=chunk,
                input=True)

frames = []  # Initialize array to store frames
asyncio.run(publish())

# Stop and close the stream
stream.stop_stream()
stream.close()
# Terminate the PortAudio interface
p.terminate()
print(frames[0])
print('Finished recording')

# Save the recorded data as a WAV file
wf = wave.open(filename, 'wb')
wf.setnchannels(channels)
wf.setsampwidth(p.get_sample_size(sample_format))
wf.setframerate(fs)
wf.writeframes(b''.join(frames))
wf.close()
