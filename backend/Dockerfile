# syntax=docker/dockerfile:1.7
# Multi-stage build: dependencies are resolved from the lockfile in a builder stage; the runtime
# image contains only the virtualenv and source, runs as a non-root user, and has no build tools.
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime
RUN useradd --create-home --uid 10001 careslot
WORKDIR /app
COPY --from=builder --chown=careslot:careslot /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER careslot
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "careslot.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
