FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY packages/database/requirements.txt /app/requirements-db.txt
RUN pip install --no-cache-dir -r /app/requirements-db.txt
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic-settings \
    python-dotenv \
    feedparser \
    httpx \
    passlib[bcrypt]

# Application code
COPY packages/ /app/packages/
COPY apps/api/ /app/apps/api/
COPY apps/agents/ /app/apps/agents/

# Ensure Python can find our packages
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

# Railway sets PORT dynamically; use shell form so $PORT is expanded at runtime
CMD uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
