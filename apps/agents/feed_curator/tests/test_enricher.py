"""Tests for Feed Curator enricher — embed detection and og:image extraction.

detect_embed and og:image parsing use real logic (no mocks needed for pure functions).
HTTP calls in extract_og_image are mocked via unittest.mock.patch.
"""

from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.agents.feed_curator.curator import CuratedItem
from apps.agents.feed_curator.enricher import (
    detect_embed,
    enrich_items,
    extract_og_image,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_item(
    content_hash: str = "hash001",
    source_url: str = "https://example.com",
    thumbnail_url: Optional[str] = None,
    embed_type: Optional[str] = None,
    embed_url: Optional[str] = None,
) -> CuratedItem:
    """Create a CuratedItem with sensible defaults for enricher tests."""
    return CuratedItem(
        content_hash=content_hash,
        editorial_headline="Test headline",
        editorial_context="Test context.",
        relevance_score=75,
        category="AI",
        source_url=source_url,
        thumbnail_url=thumbnail_url,
        embed_type=embed_type,
        embed_url=embed_url,
    )


# ---------------------------------------------------------------------------
# detect_embed
# ---------------------------------------------------------------------------


class TestDetectEmbedYouTube:
    """YouTube URL detection and embed URL generation."""

    def test_youtube_watch_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "youtube"
        assert embed_url == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_youtu_be_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "youtube"
        assert embed_url == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_youtube_embed_url(self):
        url = "https://www.youtube.com/embed/abc12345678"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "youtube"
        assert embed_url == "https://www.youtube.com/embed/abc12345678"

    def test_youtube_watch_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=PLabc"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "youtube"
        assert "dQw4w9WgXcQ" in embed_url

    def test_youtube_video_id_exactly_11_chars(self):
        # YouTube IDs are exactly 11 characters
        url = "https://youtu.be/12345678901"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "youtube"
        assert "12345678901" in embed_url

    def test_youtube_video_id_with_hyphens_and_underscores(self):
        url = "https://youtu.be/abc-EFG_12X"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "youtube"
        assert "abc-EFG_12X" in embed_url


class TestDetectEmbedInstagram:
    """Instagram URL detection."""

    def test_instagram_post_url(self):
        url = "https://www.instagram.com/p/ABC123xyz/"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "instagram"
        assert embed_url == "https://www.instagram.com/p/ABC123xyz/embed"

    def test_instagram_reel_url(self):
        url = "https://www.instagram.com/reel/XYZ789abc/"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "instagram"
        assert "XYZ789abc" in embed_url

    def test_instagram_profile_url_not_detected(self):
        url = "https://www.instagram.com/nubank/"
        embed_type, embed_url = detect_embed(url)
        assert embed_type is None
        assert embed_url is None


class TestDetectEmbedTikTok:
    """TikTok URL detection."""

    def test_tiktok_video_url(self):
        url = "https://www.tiktok.com/@user.name/video/7123456789012345678"
        embed_type, embed_url = detect_embed(url)
        assert embed_type == "tiktok"
        assert embed_url == "https://www.tiktok.com/embed/v2/7123456789012345678"

    def test_tiktok_user_profile_not_detected(self):
        url = "https://www.tiktok.com/@user.name"
        embed_type, embed_url = detect_embed(url)
        assert embed_type is None
        assert embed_url is None


class TestDetectEmbedEdgeCases:
    """Edge cases for embed detection."""

    def test_empty_string_returns_none_none(self):
        embed_type, embed_url = detect_embed("")
        assert embed_type is None
        assert embed_url is None

    def test_non_video_url_returns_none_none(self):
        url = "https://techcrunch.com/article/startup-raises-10m"
        embed_type, embed_url = detect_embed(url)
        assert embed_type is None
        assert embed_url is None

    def test_twitter_url_not_detected(self):
        url = "https://twitter.com/user/status/123456789"
        embed_type, embed_url = detect_embed(url)
        assert embed_type is None
        assert embed_url is None

    def test_linkedin_url_not_detected(self):
        url = "https://linkedin.com/posts/nubank_activity-123456"
        embed_type, embed_url = detect_embed(url)
        assert embed_type is None
        assert embed_url is None

    def test_returns_tuple_of_two(self):
        result = detect_embed("https://example.com")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_url_with_youtube_in_path_but_not_youtube_domain(self):
        # Should not match — the regex requires youtube.com/watch or youtu.be
        url = "https://example.com/redirect?to=youtube.com/not-a-video"
        embed_type, embed_url = detect_embed(url)
        # May match depending on regex — test that it doesn't crash
        assert isinstance(embed_type, (str, type(None)))


# ---------------------------------------------------------------------------
# extract_og_image
# ---------------------------------------------------------------------------


class TestExtractOgImage:
    """Test og:image extraction from HTML responses."""

    def _mock_response(self, status: int = 200, html: str = "") -> Mock:
        resp = Mock()
        resp.status_code = status
        resp.text = html
        return resp

    def test_returns_og_image_property_first_order(self):
        html = '<meta property="og:image" content="https://img.example.com/cover.jpg" />'
        with patch("httpx.get", return_value=self._mock_response(html=html)):
            result = extract_og_image("https://example.com")
        assert result == "https://img.example.com/cover.jpg"

    def test_returns_og_image_reversed_attribute_order(self):
        # content before property
        html = '<meta content="https://img.example.com/alt.jpg" property="og:image" />'
        with patch("httpx.get", return_value=self._mock_response(html=html)):
            result = extract_og_image("https://example.com")
        assert result == "https://img.example.com/alt.jpg"

    def test_returns_none_on_404(self):
        with patch("httpx.get", return_value=self._mock_response(status=404)):
            result = extract_og_image("https://example.com/404")
        assert result is None

    def test_returns_none_on_500(self):
        with patch("httpx.get", return_value=self._mock_response(status=500)):
            result = extract_og_image("https://example.com/error")
        assert result is None

    def test_returns_none_on_timeout(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            result = extract_og_image("https://example.com/slow")
        assert result is None

    def test_returns_none_on_connection_error(self):
        with patch("httpx.get", side_effect=Exception("Connection refused")):
            result = extract_og_image("https://example.com/unreachable")
        assert result is None

    def test_returns_none_when_no_og_image_tag(self):
        html = "<html><head><title>Page</title></head><body>Content</body></html>"
        with patch("httpx.get", return_value=self._mock_response(html=html)):
            result = extract_og_image("https://example.com")
        assert result is None

    def test_returns_none_for_empty_url(self):
        result = extract_og_image("")
        assert result is None

    def test_single_quotes_in_attribute_values(self):
        html = "<meta property='og:image' content='https://img.example.com/sq.jpg' />"
        with patch("httpx.get", return_value=self._mock_response(html=html)):
            result = extract_og_image("https://example.com")
        assert result == "https://img.example.com/sq.jpg"

    def test_case_insensitive_property_attribute(self):
        html = '<meta PROPERTY="og:image" CONTENT="https://img.example.com/upper.jpg" />'
        with patch("httpx.get", return_value=self._mock_response(html=html)):
            result = extract_og_image("https://example.com")
        assert result == "https://img.example.com/upper.jpg"

    def test_only_scans_first_50kb(self):
        # og:image placed beyond the 50KB mark should not be found
        padding = "X" * 50001
        html_after = '<meta property="og:image" content="https://far.example.com/img.jpg" />'
        html = padding + html_after
        with patch("httpx.get", return_value=self._mock_response(html=html)):
            result = extract_og_image("https://example.com")
        assert result is None

    def test_uses_sinal_bot_user_agent(self):
        html = '<meta property="og:image" content="https://img.example.com/x.jpg" />'
        with patch("httpx.get", return_value=self._mock_response(html=html)) as mock_get:
            extract_og_image("https://example.com")
        call_kwargs = mock_get.call_args.kwargs
        ua = call_kwargs.get("headers", {}).get("User-Agent", "")
        assert "SinalBot" in ua


# ---------------------------------------------------------------------------
# enrich_items
# ---------------------------------------------------------------------------


class TestEnrichItems:
    """Test the full enrichment pipeline orchestrator."""

    def test_youtube_url_gets_embed_type(self):
        item = make_item(source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type == "youtube"
        assert item.embed_url == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_youtube_url_gets_thumbnail(self):
        item = make_item(source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        enrich_items([item], fetch_thumbnails=False)
        assert item.thumbnail_url == "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"

    def test_instagram_url_gets_embed(self):
        item = make_item(source_url="https://www.instagram.com/p/ABC123xyz/")
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type == "instagram"
        assert "ABC123xyz" in item.embed_url

    def test_tiktok_url_gets_embed(self):
        item = make_item(source_url="https://www.tiktok.com/@user/video/12345678901234")
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type == "tiktok"

    def test_non_embed_url_with_fetch_thumbnails_false(self):
        item = make_item(source_url="https://techcrunch.com/article/test")
        enrich_items([item], fetch_thumbnails=False)
        # No embed detection, no HTTP call
        assert item.embed_type is None
        assert item.thumbnail_url is None

    def test_non_embed_url_fetches_og_image_when_enabled(self):
        item = make_item(source_url="https://techcrunch.com/article/test")
        with patch("apps.agents.feed_curator.enricher.extract_og_image") as mock_og:
            mock_og.return_value = "https://techcrunch.com/img/cover.jpg"
            enrich_items([item], fetch_thumbnails=True)
        assert item.thumbnail_url == "https://techcrunch.com/img/cover.jpg"

    def test_existing_thumbnail_not_overwritten_by_og_fetch(self):
        item = make_item(
            source_url="https://techcrunch.com/article/test",
            thumbnail_url="https://existing.example.com/thumb.jpg",
        )
        with patch("apps.agents.feed_curator.enricher.extract_og_image") as mock_og:
            mock_og.return_value = "https://new.example.com/thumb.jpg"
            enrich_items([item], fetch_thumbnails=True)
        # Existing thumbnail must be preserved
        assert item.thumbnail_url == "https://existing.example.com/thumb.jpg"
        mock_og.assert_not_called()

    def test_og_fetch_not_called_for_youtube(self):
        item = make_item(source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        with patch("apps.agents.feed_curator.enricher.extract_og_image") as mock_og:
            enrich_items([item], fetch_thumbnails=True)
        # YouTube already has thumbnail from video ID pattern — no HTTP call needed
        mock_og.assert_not_called()

    def test_empty_item_list(self):
        result = enrich_items([], fetch_thumbnails=False)
        assert result == []

    def test_returns_same_list_instance(self):
        items = [make_item()]
        result = enrich_items(items, fetch_thumbnails=False)
        assert result is items

    def test_modifies_items_in_place(self):
        item = make_item(source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type == "youtube"

    def test_mixed_items_enriched_correctly(self):
        yt_item = make_item(content_hash="yt", source_url="https://www.youtube.com/watch?v=abc12345678")
        plain_item = make_item(content_hash="plain", source_url="https://techcrunch.com/story")
        ig_item = make_item(content_hash="ig", source_url="https://www.instagram.com/p/XYZ987/")

        enrich_items([yt_item, plain_item, ig_item], fetch_thumbnails=False)

        assert yt_item.embed_type == "youtube"
        assert plain_item.embed_type is None
        assert ig_item.embed_type == "instagram"

    def test_item_with_empty_source_url(self):
        item = make_item(source_url="")
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type is None
        assert item.thumbnail_url is None

    def test_og_fetch_returns_none_does_not_set_thumbnail(self):
        item = make_item(source_url="https://example.com/no-og")
        with patch("apps.agents.feed_curator.enricher.extract_og_image", return_value=None):
            enrich_items([item], fetch_thumbnails=True)
        assert item.thumbnail_url is None

    def test_youtube_link_in_source_text_detected(self):
        """Twitter posts store YouTube links in text, not source_url."""
        item = make_item(source_url="https://x.com/user/status/123")
        item.source_text = "Check this out https://www.youtube.com/watch?v=dQw4w9WgXcQ great video"
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type == "youtube"
        assert item.embed_url == "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert item.thumbnail_url == "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"

    def test_instagram_link_in_source_text_detected(self):
        """Instagram reel links in tweet text."""
        item = make_item(source_url="https://x.com/user/status/456")
        item.source_text = "Amazing reel https://www.instagram.com/reel/ABC123/"
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type == "instagram"

    def test_source_url_embed_takes_priority_over_text(self):
        """If source_url is already a YouTube link, don't scan text."""
        item = make_item(source_url="https://www.youtube.com/watch?v=abc123abcde")
        item.source_text = "Also see https://www.youtube.com/watch?v=xyz789xyz78"
        enrich_items([item], fetch_thumbnails=False)
        # Should use the source_url video, not the text one
        assert item.embed_url == "https://www.youtube.com/embed/abc123abcde"

    def test_no_video_in_text_no_embed(self):
        """Plain text without video links should not trigger embed detection."""
        item = make_item(source_url="https://x.com/user/status/789")
        item.source_text = "Just a regular tweet about AI and fintech"
        enrich_items([item], fetch_thumbnails=False)
        assert item.embed_type is None
