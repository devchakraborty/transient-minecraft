FROM python:3.7-alpine

RUN apt install -y openjdk8

RUN pip install poetry

COPY . .

RUN poetry install

ENTRYPOINT [ "poetry", "run", "server", "--cloud", "gcloud" ]

EXPOSE 25565
