"""Tests for the unified Sinal brand email template."""

import pytest

from apps.api.services.email_template import BRAND_COLORS, build_brand_html


class TestBrandColors:
    """Brand color constants are complete and correct."""

    def test_all_required_colors_present(self):
        required = {
            "background", "container", "accent", "heading",
            "body_text", "muted", "border",
        }
        assert required.issubset(BRAND_COLORS.keys())

    def test_accent_is_signal_yellow(self):
        assert BRAND_COLORS["accent"] == "#E8FF59"

    def test_background_is_sinal_black(self):
        assert BRAND_COLORS["background"] == "#0A0A0B"


class TestBuildBrandHtml:
    """Tests for build_brand_html() — base template (transactional)."""

    def test_contains_sinal_colors(self):
        html = build_brand_html("<p>Test</p>", "Title")
        assert "#0A0A0B" in html
        assert "#1A1A1F" in html
        assert "#E8FF59" in html
        assert "#FAFAF8" in html

    def test_uses_ibm_plex_sans(self):
        html = build_brand_html("<p>Test</p>", "Title")
        assert "IBM Plex Sans" in html

    def test_includes_body_content(self):
        html = build_brand_html("<p>Custom content</p>", "Title")
        assert "Custom content" in html

    def test_sets_title(self):
        html = build_brand_html("<p>Body</p>", "My Subject")
        assert "<title>My Subject</title>" in html

    def test_includes_footer(self):
        html = build_brand_html("<p>Body</p>", "Title")
        assert "Sinal.lab" in html
        assert "sinal.ai" in html

    def test_valid_html_structure(self):
        html = build_brand_html("<p>Body</p>", "Title")
        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_sets_portuguese_lang(self):
        html = build_brand_html("<p>Body</p>", "Title")
        assert 'lang="pt-BR"' in html

    def test_footer_has_portuguese_accents(self):
        html = build_brand_html("<p>Body</p>", "Title")
        assert "Intelig\u00eancia" in html
        assert "constr\u00f3i" in html

    def test_includes_cta_button_style(self):
        html = build_brand_html("<p>Body</p>", "Title")
        assert ".cta-button" in html


class TestNewsletterStyles:
    """Tests for newsletter_styles=True flag."""

    def test_no_newsletter_styles_by_default(self):
        html = build_brand_html("<p>Body</p>", "Title")
        assert "DM Serif Display" not in html
        assert "blockquote" not in html

    def test_newsletter_styles_adds_dm_serif_display(self):
        html = build_brand_html("<p>Body</p>", "Title", newsletter_styles=True)
        assert "DM Serif Display" in html

    def test_newsletter_styles_adds_h2(self):
        html = build_brand_html("<p>Body</p>", "Title", newsletter_styles=True)
        assert "#F0EDE8" in html
        assert "18px" in html

    def test_newsletter_styles_adds_blockquote(self):
        html = build_brand_html("<p>Body</p>", "Title", newsletter_styles=True)
        assert "blockquote" in html
        assert "#2A2A32" in html

    def test_newsletter_styles_adds_hr(self):
        html = build_brand_html("<p>Body</p>", "Title", newsletter_styles=True)
        assert "border-top:" in html

    def test_newsletter_h1_has_accent_border(self):
        html = build_brand_html("<p>Body</p>", "Title", newsletter_styles=True)
        assert "border-bottom: 2px solid #E8FF59" in html


class TestUnsubscribeUrl:
    """Tests for the unsubscribe link."""

    def test_no_unsubscribe_by_default(self):
        html = build_brand_html("<p>Body</p>", "Title")
        assert "Cancelar" not in html

    def test_unsubscribe_link_present(self):
        html = build_brand_html(
            "<p>Body</p>", "Title",
            unsubscribe_url="https://example.com/unsub",
        )
        assert "Cancelar inscri\u00e7\u00e3o" in html
        assert "https://example.com/unsub" in html

    def test_unsubscribe_with_resend_placeholder(self):
        html = build_brand_html(
            "<p>Body</p>", "Title",
            unsubscribe_url="{{{RESEND_UNSUBSCRIBE_URL}}}",
        )
        assert "{{{RESEND_UNSUBSCRIBE_URL}}}" in html

    def test_unsubscribe_combined_with_newsletter_styles(self):
        html = build_brand_html(
            "<p>Body</p>", "Title",
            newsletter_styles=True,
            unsubscribe_url="https://example.com/unsub",
        )
        assert "DM Serif Display" in html
        assert "Cancelar inscri\u00e7\u00e3o" in html
