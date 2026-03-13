# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS base

ENV PYTHONUNBUFFERED=1

ARG UID=10001

RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/usr/sbin/nologin" \
    --uid "${UID}" \
    appuser


# Install build dependencies and runtime libs for LiveKit agents native FFI
# gcc, g++, python3-dev: for Python packages with C extensions
# libglib2.0-0: required by livekit-agents FFI (libgobject-2.0.so.0)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libglib2.0-0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency layer
COPY pyproject.toml uv.lock ./
RUN mkdir -p src
RUN uv sync --locked

# App source
COPY . .

RUN chown -R appuser:appuser /app

USER appuser

CMD ["sh", "-lc", "uv run src/agent.py download-files && uv run src/agent.py start"]
