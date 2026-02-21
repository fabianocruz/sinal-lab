"""Shared HTTP client factory for all agent collectors.

Provides a configured httpx.Client with retry support, consistent
User-Agent, timeouts, and redirect handling.

Usage:
    from apps.agents.sources.http import create_http_client

    with create_http_client() as client:
        response = client.get("https://example.com/feed.xml")
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple

import httpx


@dataclass
class HttpClientConfig:
    """Configuration for the shared HTTP client."""

    user_agent: str = "Sinal.lab/0.2"
    timeout: float = 15.0
    follow_redirects: bool = True
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    retry_on_status: Tuple[int, ...] = (429, 500, 502, 503, 504)


def create_http_client(config: Optional[HttpClientConfig] = None) -> httpx.Client:
    """Create a shared httpx.Client with retry via transport.

    Args:
        config: Optional configuration. Uses defaults if None.

    Returns:
        Configured httpx.Client ready for use as a context manager.
    """
    if config is None:
        config = HttpClientConfig()

    transport = httpx.HTTPTransport(retries=config.max_retries)

    return httpx.Client(
        transport=transport,
        headers={"User-Agent": config.user_agent},
        timeout=config.timeout,
        follow_redirects=config.follow_redirects,
    )


def create_async_http_client(
    config: Optional[HttpClientConfig] = None,
) -> httpx.AsyncClient:
    """Create an async httpx.AsyncClient with retry via transport.

    Args:
        config: Optional configuration. Uses defaults if None.

    Returns:
        Configured httpx.AsyncClient ready for use as an async context manager.
    """
    if config is None:
        config = HttpClientConfig()

    transport = httpx.AsyncHTTPTransport(retries=config.max_retries)

    return httpx.AsyncClient(
        transport=transport,
        headers={"User-Agent": config.user_agent},
        timeout=config.timeout,
        follow_redirects=config.follow_redirects,
    )
