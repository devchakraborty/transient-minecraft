FROM python:3.7-alpine

RUN apk add openjdk8

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN python setup.py install

ENTRYPOINT [ "python", "-m", "minecraft.server" ]
