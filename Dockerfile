FROM python:3.7-buster

RUN apt install -y openjdk8 build-base libffi-dev openssl-dev

RUN pip install poetry

COPY . .

RUN poetry install

ENTRYPOINT [ "poetry", "run", "server", "--cloud", "gcloud" ]

EXPOSE 25565
