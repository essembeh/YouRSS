
#######################################
## Buider
#######################################
FROM python:3 as builder

RUN pip3 install poetry
ADD . /app
WORKDIR /app
RUN poetry build

#######################################
## Runner
#######################################
FROM python:3

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip3 install uvicorn
COPY --from=builder /app/dist/yourss-*.whl /tmp
RUN pip install /tmp/yourss-*.whl

EXPOSE 8000
ENTRYPOINT uvicorn --host 0.0.0.0 --port 8000 yourss.webapp:app

