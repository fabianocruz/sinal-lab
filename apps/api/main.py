"""Sinal.lab API — FastAPI application entry point.

Usage:
    uvicorn apps.api.main:app --reload --port 8000
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from apps.api.config import get_settings
from apps.api.ratelimit import limiter
from apps.api.routers import admin_api_keys, admin_content, agents, auth, companies, content, covers, developers, editorial, export, feedback, health, signals, waitlist

settings = get_settings()

app = FastAPI(
    title="Sinal.lab API",
    description="AI-native intelligence platform for the LATAM tech ecosystem.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting (default limit on every route; stricter per-route
# limits live on the signup endpoints; /health is exempt)
app.state.limiter = limiter


def _rate_limit_exceeded(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}",
            "code": "RATE_LIMITED",
        },
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(agents.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(content.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(waitlist.router, prefix="/api")
app.include_router(developers.router, prefix="/api")
app.include_router(editorial.router, prefix="/api")
app.include_router(admin_content.router, prefix="/api")
app.include_router(covers.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(admin_api_keys.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")


@app.get("/")
def root():
    """API root — basic info."""
    return {
        "name": "Sinal.lab API",
        "version": "0.1.0",
        "tagline": "Inteligencia aberta para quem constroi.",
        "docs": "/docs",
    }
