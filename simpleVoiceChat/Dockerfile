FROM python:latest

COPY . .
RUN apt-get update && apt-get install -y libasound-dev python3-pyaudio portaudio19-dev
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

CMD ["python3", "recorder.py"]
