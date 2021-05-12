FROM debian:stable-slim

RUN apt update && apt install -q -y python3 python3-pip && apt clean
RUN pip3 install poetry gunicorn

ADD . /app
WORKDIR /app
RUN poetry build
RUN pip3 install dist/youtube_rss_viewer-*.whl

EXPOSE 8000
ENTRYPOINT gunicorn --bind 0.0.0.0:8000 'youtube_rss_viewer:create_app()'

