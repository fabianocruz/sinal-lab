"""Tests for shared HTTP client with retry/backoff.

Tests the HttpClientConfig, create_http_client, and create_async_http_client
factory functions used by all agent collectors.
"""

import httpx
import pytest

from apps.agents.sources.http import (
    HttpClientConfig,
    create_async_http_client,
    create_http_client,
)


class TestHttpClientConfig:
    """Test HttpClientConfig defaults and customization."""

    def test_defaults(self) -> None:
        config = HttpClientConfig()
        assert config.user_agent == "Sinal.lab/0.2"
        assert config.timeout == 15.0
        assert config.follow_redirects is True
        assert config.max_retries == 3
        assert config.retry_backoff_base == 1.0
        assert config.retry_on_status == (429, 500, 502, 503, 504)

    def test_custom_values(self) -> None:
        config = HttpClientConfig(
            user_agent="TestAgent/1.0",
            timeout=30.0,
            follow_redirects=False,
            max_retries=5,
            retry_backoff_base=2.0,
            retry_on_status=(429, 503),
        )
        assert config.user_agent == "TestAgent/1.0"
        assert config.timeout == 30.0
        assert config.follow_redirects is False
        assert config.max_retries == 5
        assert config.retry_backoff_base == 2.0
        assert config.retry_on_status == (429, 503)


class TestCreateHttpClient:
    """Test create_http_client factory function."""

    def test_returns_client(self) -> None:
        client = create_http_client()
        assert isinstance(client, httpx.Client)
        client.close()

    def test_default_config(self) -> None:
        client = create_http_client()
        assert client.headers.get("user-agent") == "Sinal.lab/0.2"
        assert client.timeout.connect == 15.0
        assert client.follow_redirects is True
        client.close()

    def test_custom_config_user_agent(self) -> None:
        config = HttpClientConfig(user_agent="Custom/2.0")
        client = create_http_client(config)
        assert client.headers.get("user-agent") == "Custom/2.0"
        client.close()

    def test_custom_config_timeout(self) -> None:
        config = HttpClientConfig(timeout=30.0)
        client = create_http_client(config)
        assert client.timeout.connect == 30.0
        client.close()

    def test_custom_config_no_redirects(self) -> None:
        config = HttpClientConfig(follow_redirects=False)
        client = create_http_client(config)
        assert client.follow_redirects is False
        client.close()

    def test_none_config_uses_defaults(self) -> None:
        client = create_http_client(None)
        assert isinstance(client, httpx.Client)
        assert client.headers.get("user-agent") == "Sinal.lab/0.2"
        client.close()


class TestCreateAsyncHttpClient:
    """Test create_async_http_client factory function."""

    def test_returns_async_client(self) -> None:
        client = create_async_http_client()
        assert isinstance(client, httpx.AsyncClient)

    def test_default_config(self) -> None:
        client = create_async_http_client()
        assert client.headers.get("user-agent") == "Sinal.lab/0.2"
        assert client.timeout.connect == 15.0
        assert client.follow_redirects is True

    def test_custom_config(self) -> None:
        config = HttpClientConfig(
            user_agent="AsyncAgent/1.0",
            timeout=25.0,
            follow_redirects=False,
        )
        client = create_async_http_client(config)
        assert client.headers.get("user-agent") == "AsyncAgent/1.0"
        assert client.timeout.connect == 25.0
        assert client.follow_redirects is False
