FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY packages/database/requirements.txt /app/requirements-db.txt
RUN pip install --no-cache-dir -r /app/requirements-db.txt
COPY apps/agents/requirements.txt /app/requirements-agents.txt
RUN pip install --no-cache-dir -r /app/requirements-agents.txt
# cache-bust: 2026-04-06
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    slowapi \
    "pydantic[email]" \
    pydantic-settings \
    python-dotenv \
    feedparser \
    httpx \
    bcrypt

# Application code
COPY packages/ /app/packages/
COPY apps/api/ /app/apps/api/
COPY apps/agents/ /app/apps/agents/
COPY scripts/ /app/scripts/

# Ensure Python can find our packages
ENV PYTHONPATH=/app

# Railway injects PORT at runtime; default to 8000 for local dev.
# `exec` makes uvicorn the PID 1 so SIGTERM from Railway hits the app
# directly (graceful shutdown). JSON-form is required for proper signal
# handling but doesn't expand env vars, so we wrap in sh -c.
# --workers 2: survive one worker dying and use both vCPUs.
# --proxy-headers + --forwarded-allow-ips: trust Railway's proxy so
# request.client carries the real caller IP (rate limiting keys on it).
CMD ["sh", "-c", "exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --proxy-headers --forwarded-allow-ips '*'"]
