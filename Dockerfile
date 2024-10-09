
#######################################
## Buider
#######################################
FROM python:3.12 as builder

RUN pip3 install poetry
ADD . /app
WORKDIR /app
RUN poetry build
RUN poetry export -f requirements.txt --output /app/requirements.txt

#######################################
## Runner
#######################################
FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=builder /app/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY --from=builder /app/dist/yourss-*.whl /tmp
RUN pip install /tmp/yourss-*.whl

RUN pip3 install uvicorn
EXPOSE 8000
ENTRYPOINT uvicorn --host 0.0.0.0 --port 8000 yourss.main:app

