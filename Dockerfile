# syntax=docker/dockerfile:1

FROM python:3.11-slim-buster

WORKDIR /python-docker

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY src src
COPY templates templates
COPY static static

CMD [ "python3", "-m" , "gunicorn", "src.server:app", "-b=0.0.0.0:5000", "-w=4"]
