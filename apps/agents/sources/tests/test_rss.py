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
