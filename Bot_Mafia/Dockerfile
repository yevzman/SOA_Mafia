FROM python:latest

COPY . .
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

CMD [ "python3", "server.py" ]