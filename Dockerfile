#########################################
## Stage: base
##
FROM python:3-slim as base

# Create dedicated user
RUN groupadd -r app && useradd -r -d /app -g app -N app
RUN mkdir -p /app && chown app:app /app
WORKDIR /app

# Python default config
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


#########################################
## Stage: builder
##
FROM base as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_LINK_MODE="copy"
ENV UV_COMPILE_BYTECODE="1"
ENV UV_PYTHON_DOWNLOADS="never"

# Use dedicated user
USER app

# Only create the venv for dependencies
COPY --chown=app:app . .
RUN uv sync --locked --no-dev --no-install-project

# Build the app and install it
RUN uv build --wheel
RUN uv pip install --offline dist/*.whl


#########################################
## Stage: webapp
##
FROM base as webapp

# Install tini
RUN apt-get update && apt-get install -y tini && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["tini", "--"]

# Use dedicated user
USER app

# Get venv from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Custom Python
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Webserver
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "yourss.main:app"]

