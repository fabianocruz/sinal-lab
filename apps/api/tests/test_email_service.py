"""Tests for the email service — brand template and welcome email delivery."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.api.services.email import _wrap_in_brand_template, send_welcome_email


# ---------------------------------------------------------------------------
# _wrap_in_brand_template
# ---------------------------------------------------------------------------


class TestBrandTemplate:
    """Tests for the brand HTML email template."""

    def test_brand_template_contains_sinal_colors(self):
        """Template output includes all Sinal brand colors."""
        html = _wrap_in_brand_template("<p>Test</p>", "Test Title")

        assert "#0A0A0B" in html  # sinal-black
        assert "#1A1A1F" in html  # graphite
        assert "#E8FF59" in html  # signal accent
        assert "#FAFAF8" in html  # bone heading color

    def test_brand_template_uses_ibm_plex_sans(self):
        """Template specifies IBM Plex Sans as the primary font."""
        html = _wrap_in_brand_template("<p>Test</p>", "Test Title")

        assert "IBM Plex Sans" in html

    def test_brand_template_includes_body_content(self):
        """Template wraps the provided HTML body content."""
        body = "<p>Custom content here</p>"
        html = _wrap_in_brand_template(body, "My Title")

        assert "Custom content here" in html

    def test_brand_template_includes_title(self):
        """Template sets the HTML title tag."""
        html = _wrap_in_brand_template("<p>Body</p>", "Email Subject")

        assert "<title>Email Subject</title>" in html

    def test_brand_template_includes_footer(self):
        """Template includes the Sinal.lab branded footer."""
        html = _wrap_in_brand_template("<p>Body</p>", "Title")

        assert "Sinal.lab" in html
        assert "sinal.ai" in html

    def test_brand_template_is_valid_html(self):
        """Template output starts with DOCTYPE and contains html/head/body tags."""
        html = _wrap_in_brand_template("<p>Body</p>", "Title")

        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_brand_template_sets_portuguese_lang(self):
        """Template sets lang='pt-BR' for proper language identification."""
        html = _wrap_in_brand_template("<p>Body</p>", "Title")

        assert 'lang="pt-BR"' in html


# ---------------------------------------------------------------------------
# send_welcome_email
# ---------------------------------------------------------------------------


class TestSendWelcomeEmail:
    """Tests for the welcome email send function."""

    def test_send_welcome_email_no_api_key(self, monkeypatch):
        """Returns False without error when RESEND_API_KEY is not set."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "")

        result = send_welcome_email("user@example.com", "Test User")

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_welcome_email_success(self, mock_post, monkeypatch):
        """Returns True when Resend API responds with 200."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")
        monkeypatch.setenv("RESEND_FROM_EMAIL", "test@sinal.ai")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_welcome_email("user@example.com", "Maria")

        assert result is True
        mock_post.assert_called_once()

        # Verify the API was called with correct parameters
        call_kwargs = mock_post.call_args
        assert call_kwargs.args[0] == "https://api.resend.com/emails"
        assert "Bearer re_test_key_123" in call_kwargs.kwargs["headers"]["Authorization"]
        assert call_kwargs.kwargs["json"]["to"] == ["user@example.com"]
        assert "Bem-vindo" in call_kwargs.kwargs["json"]["subject"]

        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_welcome_email_api_error(self, mock_post, monkeypatch):
        """Returns False when the Resend API raises an error."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_post.side_effect = httpx.ConnectError("Connection refused")

        result = send_welcome_email("user@example.com", "Test")

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_welcome_email_http_status_error(self, mock_post, monkeypatch):
        """Returns False when Resend API returns a non-2xx status code."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Invalid email"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "422 Unprocessable Entity",
            request=MagicMock(),
            response=mock_response,
        )
        mock_post.return_value = mock_response

        result = send_welcome_email("bad-email", "Test")

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_welcome_email_html_contains_portuguese_accents(
        self, mock_post, monkeypatch
    ):
        """The email HTML body contains proper Portuguese accented characters."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        send_welcome_email("user@example.com", "Joao")

        call_kwargs = mock_post.call_args
        html_body = call_kwargs.kwargs["json"]["html"]

        # Verify Portuguese accented characters are present
        assert "\u00e9" in html_body  # e with acute (tecnicos -> tecnicos)
        assert "\u00e3" in html_body  # a with tilde (informacoes -> informacoes)
        assert "\u00e7" in html_body  # c with cedilla (movimentacoes)
        assert "\u00f3" in html_body  # o with acute (construi)
        assert "\u00ea" in html_body  # e with circumflex (tendencias)
        assert "\u00ed" in html_body  # i with acute (analises)

        # Verify subject also has accents
        subject = call_kwargs.kwargs["json"]["subject"]
        assert "intelig\u00eancia" in subject

        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_welcome_email_without_name(self, mock_post, monkeypatch):
        """Welcome email works when name is None (uses generic greeting)."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_welcome_email("user@example.com")

        assert result is True

        call_kwargs = mock_post.call_args
        html_body = call_kwargs.kwargs["json"]["html"]
        assert "Ol\u00e1!" in html_body

        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_welcome_email_with_name(self, mock_post, monkeypatch):
        """Welcome email includes personalized greeting when name is provided."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        send_welcome_email("user@example.com", "Carlos")

        call_kwargs = mock_post.call_args
        html_body = call_kwargs.kwargs["json"]["html"]
        assert "Ol\u00e1, Carlos!" in html_body

        get_settings.cache_clear()
