# Multi-stage build: uv builds the venv in a build stage, the final image only gets the .venv.

# Pinned versions, updated in the dependency bump commit along with uv.lock.
ARG UV_VERSION=0.11.21
ARG PYTHON_VERSION=3.13

#########################################
## Stage: uv (official image, pinned version)
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

#########################################
## Stage: base
FROM python:${PYTHON_VERSION}-slim AS base

# A fixed high UID, the one of the Helm chart: no clash with an account of the host
RUN groupadd -r -g 10001 app && useradd -r -u 10001 -d /app -g app -N app \
 && mkdir -p /app && chown app:app /app
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


#########################################
## Stage: builder
FROM base AS builder

COPY --from=uv /uv /usr/local/bin/uv

USER 10001:10001
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# 1) Dependencies only: this layer is cached as long as pyproject.toml / uv.lock do not change.
COPY --chown=app:app pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

# 2) Then the project, not editable: the venv must be self-contained to be copied.
COPY --chown=app:app src ./src
RUN uv sync --locked --no-dev --no-editable


#########################################
## Stage: production
FROM base AS production

RUN apt-get update && apt-get install -y tini && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["tini", "--"]

USER 10001:10001
COPY --from=builder --chown=app:app /app/.venv /app/.venv
# PATH is enough: the package is installed in the venv, no PYTHONPATH needed.
ENV PATH="/app/.venv/bin:$PATH"


#########################################
## Stage: webapp
FROM production AS webapp

EXPOSE 8000
# For Docker and compose (Kubernetes has the probes of the chart): the process answers, nothing else is checked
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/version', timeout=2)"]
# No `uv run` here: PATH points to the venv, uv run would sync again at startup.
# The scheme the proxy saw (X-Forwarded-Proto) makes the login cookie Secure: only the proxy reaches the pod
CMD ["python", "-m", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "--forwarded-allow-ips", "*", "yourss.main:app"]
