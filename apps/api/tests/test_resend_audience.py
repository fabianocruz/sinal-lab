"""Tests for Resend Audience service — subscriber management."""

from unittest.mock import patch

import httpx
import pytest

from apps.api.services.resend_audience import (
    add_contact_to_audience,
    bulk_sync_contacts,
    remove_contact_from_audience,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear lru_cache between tests so env overrides take effect."""
    from apps.api.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _mock_settings(resend_api_key="re_test_key", resend_audience_id="aud_123"):
    """Return a mock settings object with Resend config."""
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.resend_api_key = resend_api_key
    settings.resend_audience_id = resend_audience_id
    return settings


# ---------------------------------------------------------------------------
# add_contact_to_audience
# ---------------------------------------------------------------------------


class TestAddContact:
    """Tests for add_contact_to_audience()."""

    @patch("apps.api.services.resend_audience.get_settings")
    @patch("apps.api.services.resend_audience.httpx.post")
    def test_adds_contact_successfully(self, mock_post, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_post.return_value.raise_for_status = lambda: None

        result = add_contact_to_audience("test@example.com", first_name="Test")

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["email"] == "test@example.com"
        assert call_kwargs[1]["json"]["first_name"] == "Test"

    @patch("apps.api.services.resend_audience.get_settings")
    @patch("apps.api.services.resend_audience.httpx.post")
    def test_adds_contact_without_name(self, mock_post, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_post.return_value.raise_for_status = lambda: None

        result = add_contact_to_audience("test@example.com")

        assert result is True
        payload = mock_post.call_args[1]["json"]
        assert "first_name" not in payload

    @patch("apps.api.services.resend_audience.get_settings")
    def test_returns_false_when_api_key_missing(self, mock_settings):
        mock_settings.return_value = _mock_settings(resend_api_key="")

        result = add_contact_to_audience("test@example.com")

        assert result is False

    @patch("apps.api.services.resend_audience.get_settings")
    def test_returns_false_when_audience_id_missing(self, mock_settings):
        mock_settings.return_value = _mock_settings(resend_audience_id="")

        result = add_contact_to_audience("test@example.com")

        assert result is False

    @patch("apps.api.services.resend_audience.get_settings")
    @patch("apps.api.services.resend_audience.httpx.post")
    def test_returns_false_on_http_error(self, mock_post, mock_settings):
        mock_settings.return_value = _mock_settings()
        response = httpx.Response(status_code=422, request=httpx.Request("POST", "https://api.resend.com"))
        mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "422", request=response.request, response=response
        )
        mock_post.return_value.status_code = 422
        mock_post.return_value.text = "Invalid email"

        result = add_contact_to_audience("bad-email")

        assert result is False

    @patch("apps.api.services.resend_audience.get_settings")
    @patch("apps.api.services.resend_audience.httpx.post")
    def test_returns_false_on_network_error(self, mock_post, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        result = add_contact_to_audience("test@example.com")

        assert result is False

    @patch("apps.api.services.resend_audience.get_settings")
    @patch("apps.api.services.resend_audience.httpx.post")
    def test_uses_correct_url(self, mock_post, mock_settings):
        mock_settings.return_value = _mock_settings(resend_audience_id="aud_abc")
        mock_post.return_value.raise_for_status = lambda: None

        add_contact_to_audience("test@example.com")

        url = mock_post.call_args[0][0]
        assert "audiences/aud_abc/contacts" in url


# ---------------------------------------------------------------------------
# remove_contact_from_audience
# ---------------------------------------------------------------------------


class TestRemoveContact:
    """Tests for remove_contact_from_audience()."""

    @patch("apps.api.services.resend_audience.get_settings")
    @patch("apps.api.services.resend_audience.httpx.delete")
    def test_removes_contact_successfully(self, mock_delete, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_delete.return_value.raise_for_status = lambda: None

        result = remove_contact_from_audience("test@example.com")

        assert result is True
        url = mock_delete.call_args[0][0]
        assert url.endswith("/test@example.com")

    @patch("apps.api.services.resend_audience.get_settings")
    def test_returns_false_when_not_configured(self, mock_settings):
        mock_settings.return_value = _mock_settings(resend_api_key="")

        result = remove_contact_from_audience("test@example.com")

        assert result is False

    @patch("apps.api.services.resend_audience.get_settings")
    @patch("apps.api.services.resend_audience.httpx.delete")
    def test_returns_false_on_http_error(self, mock_delete, mock_settings):
        mock_settings.return_value = _mock_settings()
        response = httpx.Response(status_code=404, request=httpx.Request("DELETE", "https://api.resend.com"))
        mock_delete.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=response.request, response=response
        )
        mock_delete.return_value.status_code = 404
        mock_delete.return_value.text = "Not found"

        result = remove_contact_from_audience("nonexistent@example.com")

        assert result is False


# ---------------------------------------------------------------------------
# bulk_sync_contacts
# ---------------------------------------------------------------------------


class TestBulkSync:
    """Tests for bulk_sync_contacts()."""

    @patch("apps.api.services.resend_audience.add_contact_to_audience")
    @patch("apps.api.services.resend_audience.get_settings")
    def test_syncs_all_contacts(self, mock_settings, mock_add):
        mock_settings.return_value = _mock_settings()
        mock_add.return_value = True

        contacts = [
            {"email": "a@example.com", "first_name": "A"},
            {"email": "b@example.com", "first_name": "B"},
            {"email": "c@example.com"},
        ]
        result = bulk_sync_contacts(contacts)

        assert result["synced"] == 3
        assert result["failed"] == 0
        assert result["skipped"] is False

    @patch("apps.api.services.resend_audience.add_contact_to_audience")
    @patch("apps.api.services.resend_audience.get_settings")
    def test_tracks_failures(self, mock_settings, mock_add):
        mock_settings.return_value = _mock_settings()
        mock_add.side_effect = [True, False, True]

        contacts = [
            {"email": "a@example.com"},
            {"email": "bad@example.com"},
            {"email": "c@example.com"},
        ]
        result = bulk_sync_contacts(contacts)

        assert result["synced"] == 2
        assert result["failed"] == 1

    @patch("apps.api.services.resend_audience.get_settings")
    def test_returns_skipped_when_not_configured(self, mock_settings):
        mock_settings.return_value = _mock_settings(resend_api_key="")

        result = bulk_sync_contacts([{"email": "a@example.com"}])

        assert result["skipped"] is True
        assert result["synced"] == 0

    @patch("apps.api.services.resend_audience.add_contact_to_audience")
    @patch("apps.api.services.resend_audience.get_settings")
    def test_empty_list(self, mock_settings, mock_add):
        mock_settings.return_value = _mock_settings()

        result = bulk_sync_contacts([])

        assert result["synced"] == 0
        assert result["failed"] == 0
        mock_add.assert_not_called()
