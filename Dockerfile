FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies — all versions pinned in requirements files
COPY packages/database/requirements.txt /app/requirements-db.txt
RUN pip install --no-cache-dir -r /app/requirements-db.txt
COPY apps/agents/requirements.txt /app/requirements-agents.txt
RUN pip install --no-cache-dir -r /app/requirements-agents.txt
COPY apps/api/requirements.txt /app/requirements-api.txt
RUN pip install --no-cache-dir -r /app/requirements-api.txt

# Application code
COPY packages/ /app/packages/
COPY apps/api/ /app/apps/api/
COPY apps/agents/ /app/apps/agents/
COPY scripts/ /app/scripts/

# Ensure Python can find our packages
ENV PYTHONPATH=/app

# Railway injects PORT at runtime; default to 8000 for local dev
CMD uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
