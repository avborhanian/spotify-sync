FROM python:3

WORKDIR /usr/src/app

COPY Pipfil* ./
RUN pip install pipenv && pipenv install
