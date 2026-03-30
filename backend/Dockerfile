# Backend Dockerfile — FastAPI + DuckDB

FROM python:3.12-slim AS base

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY backend/pyproject.toml backend/pyproject.toml
RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python -r backend/pyproject.toml

# Copy application code
COPY backend/ backend/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV HOST=0.0.0.0
ENV PORT=8000
ENV LOG_LEVEL=info
ENV DUCKDB_PATH=/data/config.duckdb

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
