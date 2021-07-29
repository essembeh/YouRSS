FROM debian:stable-slim

RUN apt update && apt install -q -y python3 python3-pip && apt clean
RUN pip3 install poetry gunicorn PyMySQL

ADD . /app
WORKDIR /app
RUN poetry build
RUN pip3 install dist/yourss-*.whl

EXPOSE 8000
ENTRYPOINT gunicorn --bind 0.0.0.0:8000 'yourss:create_app()'

