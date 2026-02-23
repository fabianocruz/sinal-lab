"""Tests for shared RSS/Atom feed parser.

Tests parse_feed_date, extract_tags, parse_rss_entry, and fetch_rss_feed
functions that replace duplicated code across 4 agent collectors.
"""

import time
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.agents.sources.rss import (
    RSSItem,
    extract_tags,
    fetch_rss_feed,
    parse_feed_date,
    parse_rss_entry,
)
from apps.agents.base.config import DataSourceConfig


def _make_entry(**kwargs: Any) -> SimpleNamespace:
    """Helper to create a feedparser-like entry object."""
    return SimpleNamespace(**kwargs)


def _make_time_struct(year: int = 2026, month: int = 2, day: int = 15) -> time.struct_time:
    """Helper to create a time.struct_time for feed date testing."""
    return time.strptime(f"{year}-{month:02d}-{day:02d}", "%Y-%m-%d")


class TestParseFeedDate:
    """Test parse_feed_date extraction from feedparser entries."""

    def test_published_parsed(self) -> None:
        ts = _make_time_struct(2026, 2, 15)
        entry = _make_entry(published_parsed=ts)
        result = parse_feed_date(entry)
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 15
        assert result.tzinfo == timezone.utc

    def test_updated_parsed_fallback(self) -> None:
        ts = _make_time_struct(2026, 1, 10)
        entry = _make_entry(updated_parsed=ts)
        result = parse_feed_date(entry)
        assert result is not None
        assert result.month == 1
        assert result.day == 10

    def test_created_parsed_fallback(self) -> None:
        ts = _make_time_struct(2025, 12, 25)
        entry = _make_entry(created_parsed=ts)
        result = parse_feed_date(entry)
        assert result is not None
        assert result.year == 2025

    def test_none_when_no_dates(self) -> None:
        entry = _make_entry()
        assert parse_feed_date(entry) is None

    def test_handles_value_error(self) -> None:
        entry = _make_entry(published_parsed=None, updated_parsed=None)
        assert parse_feed_date(entry) is None

    def test_priority_published_over_updated(self) -> None:
        """published_parsed is checked before updated_parsed."""
        pub = _make_time_struct(2026, 3, 1)
        upd = _make_time_struct(2026, 3, 15)
        entry = _make_entry(published_parsed=pub, updated_parsed=upd)
        result = parse_feed_date(entry)
        assert result is not None
        assert result.day == 1  # published_parsed wins


class TestExtractTags:
    """Test extract_tags from feedparser entries."""

    def test_dict_style_tags(self) -> None:
        entry = _make_entry(tags=[
            {"term": "AI", "scheme": None},
            {"term": "Machine Learning", "scheme": None},
        ])
        result = extract_tags(entry)
        assert result == ["ai", "machine learning"]

    def test_object_style_tags(self) -> None:
        entry = _make_entry(tags=[
            SimpleNamespace(term="Python"),
            SimpleNamespace(term="FastAPI"),
        ])
        result = extract_tags(entry)
        assert result == ["python", "fastapi"]

    def test_empty_tags(self) -> None:
        entry = _make_entry(tags=[])
        assert extract_tags(entry) == []

    def test_no_tags_attribute(self) -> None:
        entry = _make_entry()
        assert extract_tags(entry) == []

    def test_max_tags_limit(self) -> None:
        entry = _make_entry(tags=[
            {"term": f"tag-{i}"} for i in range(20)
        ])
        result = extract_tags(entry, max_tags=5)
        assert len(result) == 5

    def test_strips_and_lowercases(self) -> None:
        entry = _make_entry(tags=[
            {"term": "  UPPERCASE  "},
            {"term": " MiXeD CaSe "},
        ])
        result = extract_tags(entry)
        assert result == ["uppercase", "mixed case"]

    def test_skips_empty_terms(self) -> None:
        entry = _make_entry(tags=[
            {"term": "valid"},
            {"term": ""},
            {"term": "also-valid"},
        ])
        result = extract_tags(entry)
        assert result == ["valid", "also-valid"]


class TestParseRSSEntry:
    """Test parse_rss_entry conversion to RSSItem."""

    def test_full_entry(self) -> None:
        ts = _make_time_struct(2026, 2, 10)
        entry = _make_entry(
            title="Test Article Title",
            link="https://example.com/article",
            summary="This is a test summary.",
            author="John Doe",
            published_parsed=ts,
            tags=[{"term": "tech"}],
        )
        item = parse_rss_entry(entry, "Test Source")
        assert item is not None
        assert item.title == "Test Article Title"
        assert item.url == "https://example.com/article"
        assert item.source_name == "Test Source"
        assert item.summary == "This is a test summary."
        assert item.author == "John Doe"
        assert item.tags == ["tech"]
        assert item.published_at is not None
        assert item.content_hash  # Non-empty

    def test_missing_title_returns_none(self) -> None:
        entry = _make_entry(link="https://example.com/article")
        assert parse_rss_entry(entry, "Test") is None

    def test_missing_link_returns_none(self) -> None:
        entry = _make_entry(title="Test Title")
        assert parse_rss_entry(entry, "Test") is None

    def test_long_summary_truncated(self) -> None:
        entry = _make_entry(
            title="Test",
            link="https://example.com",
            summary="x" * 1500,
        )
        item = parse_rss_entry(entry, "Test")
        assert item is not None
        assert len(item.summary) == 1003  # 1000 + "..."

    def test_author_extracted(self) -> None:
        entry = _make_entry(
            title="Test",
            link="https://example.com",
            author="Jane Smith",
        )
        item = parse_rss_entry(entry, "Test")
        assert item is not None
        assert item.author == "Jane Smith"

    def test_strips_title_and_url(self) -> None:
        entry = _make_entry(
            title="  Padded Title  ",
            link="  https://example.com  ",
        )
        item = parse_rss_entry(entry, "Test")
        assert item is not None
        assert item.title == "Padded Title"
        assert item.url == "https://example.com"

    def test_content_hash_from_url(self) -> None:
        entry = _make_entry(
            title="Test",
            link="https://example.com/unique",
        )
        item = parse_rss_entry(entry, "Test")
        assert item is not None
        assert len(item.content_hash) == 32  # MD5 hex digest


class TestFetchRSSFeed:
    """Test fetch_rss_feed HTTP fetching + parsing."""

    def _make_source(self, url: str = "https://example.com/feed.xml") -> DataSourceConfig:
        return DataSourceConfig(
            name="test_feed",
            source_type="rss",
            url=url,
        )

    @patch("apps.agents.sources.rss.feedparser")
    def test_success(self, mock_feedparser: MagicMock) -> None:
        """Successful fetch and parse returns items."""
        mock_response = MagicMock()
        mock_response.text = "<rss>...</rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        ts = _make_time_struct(2026, 2, 10)
        mock_feedparser.parse.return_value = MagicMock(
            bozo=False,
            entries=[
                SimpleNamespace(
                    title="Article 1",
                    link="https://example.com/1",
                    summary="Summary 1",
                    author="Author 1",
                    published_parsed=ts,
                    tags=[],
                ),
                SimpleNamespace(
                    title="Article 2",
                    link="https://example.com/2",
                    summary="Summary 2",
                    published_parsed=None,
                    tags=[],
                ),
            ],
        )

        source = self._make_source()
        items = fetch_rss_feed(source, mock_client)
        assert len(items) == 2
        assert items[0].title == "Article 1"
        assert items[1].title == "Article 2"

    def test_http_error_returns_empty(self) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.HTTPError("Connection refused")

        source = self._make_source()
        items = fetch_rss_feed(source, mock_client)
        assert items == []

    @patch("apps.agents.sources.rss.feedparser")
    def test_malformed_feed_no_entries_returns_empty(
        self, mock_feedparser: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.text = "not xml"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        mock_feedparser.parse.return_value = MagicMock(
            bozo=True, entries=[]
        )

        source = self._make_source()
        items = fetch_rss_feed(source, mock_client)
        assert items == []

    @patch("apps.agents.sources.rss.feedparser")
    def test_malformed_feed_with_entries_returns_items(
        self, mock_feedparser: MagicMock
    ) -> None:
        """Bozo feed with valid entries still returns parsed items."""
        mock_response = MagicMock()
        mock_response.text = "<rss partial>..."
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        mock_feedparser.parse.return_value = MagicMock(
            bozo=True,
            entries=[
                SimpleNamespace(
                    title="Partial Article",
                    link="https://example.com/partial",
                ),
            ],
        )

        source = self._make_source()
        items = fetch_rss_feed(source, mock_client)
        assert len(items) == 1

    def test_no_url_returns_empty(self) -> None:
        source = DataSourceConfig(name="no_url", source_type="rss", url=None)
        mock_client = MagicMock(spec=httpx.Client)
        items = fetch_rss_feed(source, mock_client)
        assert items == []

    @patch("apps.agents.sources.rss.feedparser")
    def test_max_items_caps_entries(self, mock_feedparser: MagicMock) -> None:
        """max_items in DataSourceConfig caps the number of returned items."""
        mock_response = MagicMock()
        mock_response.text = "<rss>...</rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        # Feed has 50 entries
        mock_feedparser.parse.return_value = MagicMock(
            bozo=False,
            entries=[
                SimpleNamespace(
                    title=f"Article {i}",
                    link=f"https://example.com/{i}",
                )
                for i in range(50)
            ],
        )

        source = DataSourceConfig(
            name="big_feed", source_type="rss",
            url="https://example.com/feed", max_items=10,
        )
        items = fetch_rss_feed(source, mock_client)
        assert len(items) == 10
        assert items[0].title == "Article 0"
        assert items[-1].title == "Article 9"

    @patch("apps.agents.sources.rss.feedparser")
    def test_max_items_none_returns_all(self, mock_feedparser: MagicMock) -> None:
        """max_items=None (default) returns all entries."""
        mock_response = MagicMock()
        mock_response.text = "<rss>...</rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        mock_feedparser.parse.return_value = MagicMock(
            bozo=False,
            entries=[
                SimpleNamespace(
                    title=f"Article {i}",
                    link=f"https://example.com/{i}",
                )
                for i in range(25)
            ],
        )

        source = DataSourceConfig(
            name="full_feed", source_type="rss",
            url="https://example.com/feed",
        )
        items = fetch_rss_feed(source, mock_client)
        assert len(items) == 25


class TestRSSItem:
    """Test RSSItem dataclass behavior."""

    def test_auto_content_hash(self) -> None:
        item = RSSItem(
            title="Test",
            url="https://example.com/article",
            source_name="Test",
        )
        assert item.content_hash
        assert len(item.content_hash) == 32

    def test_preserves_manual_hash(self) -> None:
        item = RSSItem(
            title="Test",
            url="https://example.com",
            source_name="Test",
            content_hash="custom_hash_value",
        )
        assert item.content_hash == "custom_hash_value"

    def test_same_url_same_hash(self) -> None:
        item1 = RSSItem(title="A", url="https://example.com", source_name="S1")
        item2 = RSSItem(title="B", url="https://example.com", source_name="S2")
        assert item1.content_hash == item2.content_hash

    def test_different_url_different_hash(self) -> None:
        item1 = RSSItem(title="A", url="https://example.com/1", source_name="S")
        item2 = RSSItem(title="A", url="https://example.com/2", source_name="S")
        assert item1.content_hash != item2.content_hash

    def test_rssitem_image_url_defaults_to_none(self) -> None:
        """RSSItem.image_url is None when not explicitly set."""
        item = RSSItem(
            title="No Image Article",
            url="https://example.com/no-image",
            source_name="Test",
        )
        assert item.image_url is None


class TestExtractImageUrl:
    """Test extract_image_url extraction from feedparser entries."""

    def test_extract_image_url_from_media_content(self) -> None:
        """media_content list with medium=image returns first matching URL."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_content=[
                {"url": "https://cdn.example.com/image.jpg", "medium": "image"},
            ]
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/image.jpg"

    def test_extract_image_url_from_media_content_type(self) -> None:
        """media_content with image/* MIME type also works."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_content=[
                {"url": "https://cdn.example.com/photo.png", "type": "image/png"},
            ]
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/photo.png"

    def test_extract_image_url_from_media_thumbnail(self) -> None:
        """media_thumbnail list returns first URL when media_content absent."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_thumbnail=[
                {"url": "https://cdn.example.com/thumb.jpg"},
            ]
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/thumb.jpg"

    def test_extract_image_url_from_enclosure(self) -> None:
        """Enclosure with image/* MIME type returns its URL."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            enclosures=[
                {"href": "https://cdn.example.com/enclosure.jpg", "type": "image/jpeg"},
            ]
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/enclosure.jpg"

    def test_extract_image_url_from_enclosure_url_key(self) -> None:
        """Enclosure using 'url' key (not 'href') is also handled."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            enclosures=[
                {"url": "https://cdn.example.com/via-url.jpg", "type": "image/jpeg"},
            ]
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/via-url.jpg"

    def test_extract_image_url_skips_audio_enclosure(self) -> None:
        """Enclosure with audio/* MIME type is skipped."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            enclosures=[
                {"href": "https://example.com/podcast.mp3", "type": "audio/mpeg"},
            ]
        )
        result = extract_image_url(entry)
        assert result is None

    def test_extract_image_url_from_html_img_in_summary_detail(self) -> None:
        """Falls back to first <img> tag in summary_detail HTML."""
        from apps.agents.sources.rss import extract_image_url

        html = '<p>Article text.</p><img src="https://cdn.example.com/inline.jpg" alt="photo">'
        entry = _make_entry(
            summary_detail={"type": "text/html", "value": html}
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/inline.jpg"

    def test_extract_image_url_skips_non_html_summary_detail(self) -> None:
        """summary_detail with text/plain type does not trigger img parse."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            summary_detail={"type": "text/plain", "value": "No HTML here."}
        )
        result = extract_image_url(entry)
        assert result is None

    def test_extract_image_url_returns_none_when_no_media(self) -> None:
        """Entry with no media attributes returns None."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            title="Plain article",
            link="https://example.com/plain",
            summary="Just text, no image.",
        )
        result = extract_image_url(entry)
        assert result is None

    def test_extract_image_url_priority_media_content_over_enclosure(self) -> None:
        """media_content takes priority over enclosures when both are present."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_content=[
                {"url": "https://cdn.example.com/media-content.jpg", "medium": "image"},
            ],
            enclosures=[
                {"href": "https://cdn.example.com/enclosure.jpg", "type": "image/jpeg"},
            ]
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/media-content.jpg"

    def test_extract_image_url_priority_media_content_over_thumbnail(self) -> None:
        """media_content takes priority over media_thumbnail."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_content=[
                {"url": "https://cdn.example.com/content.jpg", "medium": "image"},
            ],
            media_thumbnail=[
                {"url": "https://cdn.example.com/thumbnail.jpg"},
            ],
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/content.jpg"

    def test_extract_image_url_priority_thumbnail_over_enclosure(self) -> None:
        """media_thumbnail takes priority over enclosures (but loses to media_content)."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_thumbnail=[
                {"url": "https://cdn.example.com/thumb.jpg"},
            ],
            enclosures=[
                {"href": "https://cdn.example.com/enclosure.jpg", "type": "image/jpeg"},
            ]
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/thumb.jpg"

    def test_extract_image_url_empty_media_content_list(self) -> None:
        """Empty media_content list falls through to next source."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_content=[],
            media_thumbnail=[{"url": "https://cdn.example.com/fallback-thumb.jpg"}],
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/fallback-thumb.jpg"

    def test_extract_image_url_media_content_without_image_medium(self) -> None:
        """media_content entries without 'medium=image' and no image MIME are skipped."""
        from apps.agents.sources.rss import extract_image_url

        entry = _make_entry(
            media_content=[
                {"url": "https://cdn.example.com/video.mp4", "medium": "video"},
            ],
            media_thumbnail=[{"url": "https://cdn.example.com/poster.jpg"}],
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/poster.jpg"

    def test_extract_image_url_img_with_single_quotes(self) -> None:
        """HTML img tag using single-quoted src is also matched."""
        from apps.agents.sources.rss import extract_image_url

        html = "<img src='https://cdn.example.com/single-quote.jpg'>"
        entry = _make_entry(
            summary_detail={"type": "text/html", "value": html}
        )
        result = extract_image_url(entry)
        assert result == "https://cdn.example.com/single-quote.jpg"


class TestParseRSSEntryImageUrl:
    """Test that parse_rss_entry correctly populates image_url on RSSItem."""

    def test_parse_rss_entry_includes_image_url_from_media_content(self) -> None:
        """Full entry with media_content produces RSSItem with image_url set."""
        ts = _make_time_struct(2026, 2, 10)
        entry = _make_entry(
            title="Article with Media",
            link="https://example.com/article",
            summary="Summary text.",
            published_parsed=ts,
            tags=[],
            media_content=[
                {"url": "https://cdn.example.com/article-image.jpg", "medium": "image"},
            ],
        )
        item = parse_rss_entry(entry, "Media Source")

        assert item is not None
        assert item.image_url == "https://cdn.example.com/article-image.jpg"

    def test_parse_rss_entry_image_url_is_none_when_no_media(self) -> None:
        """Entry with no media produces RSSItem.image_url = None."""
        entry = _make_entry(
            title="Plain Article",
            link="https://example.com/plain",
            summary="No images here.",
        )
        item = parse_rss_entry(entry, "Plain Source")

        assert item is not None
        assert item.image_url is None
