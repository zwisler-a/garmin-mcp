FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.30 /uv /usr/local/bin/uv

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    GARMIN_TOKEN_STORE=/data/garminconnect

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY server.py ./
RUN uv sync --frozen --no-dev

VOLUME ["/data"]

EXPOSE 8000

ENTRYPOINT ["uv", "run", "python", "server.py"]
