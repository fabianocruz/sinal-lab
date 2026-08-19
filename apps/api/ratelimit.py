"""Rate limiting for public API endpoints (slowapi).

The limiter is keyed by client IP. Behind Railway's proxy the real IP
arrives via X-Forwarded-For; uvicorn rewrites it into request.client
when started with --proxy-headers (see the Dockerfile CMD), so
get_remote_address sees the caller, not the proxy.

Disabled when API_ENV=test: the suite fires hundreds of requests from
a single TestClient address and would trip any sane limit.
test_rate_limit.py re-enables it explicitly to exercise the 429 path.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from apps.api.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    enabled=settings.api_env != "test",
)
