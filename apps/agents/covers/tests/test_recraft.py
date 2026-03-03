"""Tests for Recraft V3 API client."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.agents.covers.recraft import GeneratedImage, RecraftClient


@pytest.fixture
def mock_http_client():
    return MagicMock(spec=httpx.Client)


def _make_recraft_response(image_url="https://cdn.recraft.ai/img.png"):
    """Build a mock Recraft API JSON response."""
    return {"data": [{"url": image_url}]}


def test_generate_returns_images_on_success(mock_http_client):
    # Mock the Recraft API response
    api_response = MagicMock()
    api_response.json.return_value = _make_recraft_response()
    api_response.raise_for_status.return_value = None

    # Mock the image download response
    img_response = MagicMock()
    img_response.content = b"\x89PNG fake image bytes"
    img_response.raise_for_status.return_value = None

    mock_http_client.post.return_value = api_response
    mock_http_client.get.return_value = img_response

    client = RecraftClient(api_key="test-key", http_client=mock_http_client)
    results = client.generate("A dark illustration", variations=2)

    assert len(results) == 2
    assert all(isinstance(r, GeneratedImage) for r in results)
    assert results[0].variation == 1
    assert results[1].variation == 2
    assert results[0].image_bytes == b"\x89PNG fake image bytes"


def test_generate_returns_empty_when_unavailable():
    client = RecraftClient(api_key="")
    assert client.generate("A prompt") == []
    assert not client.is_available


def test_generate_handles_api_error(mock_http_client):
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=MagicMock(status_code=500, text="Error")
    )
    mock_http_client.post.return_value = response

    client = RecraftClient(api_key="test-key", http_client=mock_http_client)
    results = client.generate("A prompt", variations=1)
    assert results == []


def test_generate_handles_timeout(mock_http_client):
    mock_http_client.post.side_effect = httpx.TimeoutException("Timeout")

    client = RecraftClient(api_key="test-key", http_client=mock_http_client)
    results = client.generate("A prompt", variations=1)
    assert results == []


def test_generate_partial_success(mock_http_client):
    """One of two calls fails, should return 1 image."""
    api_response = MagicMock()
    api_response.json.return_value = _make_recraft_response()
    api_response.raise_for_status.return_value = None

    img_response = MagicMock()
    img_response.content = b"\x89PNG data"
    img_response.raise_for_status.return_value = None

    # First call succeeds, second fails
    mock_http_client.post.side_effect = [
        api_response,
        httpx.TimeoutException("Timeout"),
    ]
    mock_http_client.get.return_value = img_response

    client = RecraftClient(api_key="test-key", http_client=mock_http_client)
    results = client.generate("A prompt", variations=2)
    assert len(results) == 1
    assert results[0].variation == 1


def test_variations_parameter(mock_http_client):
    api_response = MagicMock()
    api_response.json.return_value = _make_recraft_response()
    api_response.raise_for_status.return_value = None

    img_response = MagicMock()
    img_response.content = b"\x89PNG data"
    img_response.raise_for_status.return_value = None

    mock_http_client.post.return_value = api_response
    mock_http_client.get.return_value = img_response

    client = RecraftClient(api_key="test-key", http_client=mock_http_client)
    results = client.generate("A prompt", variations=1)
    assert len(results) == 1
    assert mock_http_client.post.call_count == 1


def test_is_available_with_key():
    client = RecraftClient(api_key="test-key")
    assert client.is_available


def test_request_uses_recraft_dimensions_by_default(mock_http_client):
    """Default dimensions should be Recraft-valid sizes, not OG sizes."""
    from apps.agents.covers.config import RECRAFT_HEIGHT, RECRAFT_WIDTH

    api_response = MagicMock()
    api_response.json.return_value = _make_recraft_response()
    api_response.raise_for_status.return_value = None

    img_response = MagicMock()
    img_response.content = b"\x89PNG data"
    img_response.raise_for_status.return_value = None

    mock_http_client.post.return_value = api_response
    mock_http_client.get.return_value = img_response

    client = RecraftClient(api_key="test-key", http_client=mock_http_client)
    client.generate("A prompt", variations=1)

    call_args = mock_http_client.post.call_args
    assert call_args.kwargs["json"]["size"] == f"{RECRAFT_WIDTH}x{RECRAFT_HEIGHT}"
