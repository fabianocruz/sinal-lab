"""Tests for Vercel Blob uploader."""

from unittest.mock import MagicMock

import httpx
import pytest

from apps.agents.covers.uploader import BlobUploader, UploadedCover


@pytest.fixture
def mock_http_client():
    return MagicMock(spec=httpx.Client)


def _make_blob_response(url="https://store.public.blob.vercel-storage.com/covers/radar/ed30-v1.png"):
    response = MagicMock()
    response.json.return_value = {"url": url, "pathname": "covers/radar/ed30-v1.png"}
    response.raise_for_status.return_value = None
    return response


def test_upload_returns_url_on_success(mock_http_client):
    mock_http_client.put.return_value = _make_blob_response()

    uploader = BlobUploader(token="test-token", http_client=mock_http_client)
    result = uploader.upload(b"\x89PNG image data", "covers/radar/ed30-v1.png")

    assert isinstance(result, UploadedCover)
    assert "blob.vercel-storage.com" in result.url
    assert result.pathname == "covers/radar/ed30-v1.png"


def test_upload_returns_none_when_unavailable():
    uploader = BlobUploader(token="")
    assert uploader.upload(b"data", "file.png") is None
    assert not uploader.is_available


def test_upload_returns_none_on_empty_bytes(mock_http_client):
    uploader = BlobUploader(token="test-token", http_client=mock_http_client)
    assert uploader.upload(b"", "file.png") is None


def test_upload_handles_auth_error(mock_http_client):
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401, text="Unauthorized")
    )
    mock_http_client.put.return_value = response

    uploader = BlobUploader(token="bad-token", http_client=mock_http_client)
    assert uploader.upload(b"data", "file.png") is None


def test_upload_handles_timeout(mock_http_client):
    mock_http_client.put.side_effect = httpx.TimeoutException("Timeout")

    uploader = BlobUploader(token="test-token", http_client=mock_http_client)
    assert uploader.upload(b"data", "file.png") is None


def test_request_headers(mock_http_client):
    mock_http_client.put.return_value = _make_blob_response()

    uploader = BlobUploader(token="test-token", http_client=mock_http_client)
    uploader.upload(b"\x89PNG data", "covers/radar/ed30-v1.png")

    call_args = mock_http_client.put.call_args
    headers = call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Content-Type"] == "image/png"
    assert headers["x-api-version"] == "7"


def test_is_available_with_token():
    uploader = BlobUploader(token="test-token")
    assert uploader.is_available
