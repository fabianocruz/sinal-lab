"""Tests for async RSS feed fetching.

Async variants of the shared RSS source module for IO-bound concurrent
feed fetching via asyncio.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.async_rss import fetch_rss_feed_async, fetch_rss_feeds_concurrent
from apps.agents.sources.rss import RSSItem


def _make_source(
    name: str = "test_feed",
    url: str = "https://example.com/rss",
) -> DataSourceConfig:
    return DataSourceConfig(
        name=name,
        source_type="rss",
        url=url,
    )


_VALID_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Test Article</title>
      <link>https://example.com/article</link>
      <description>A test article</description>
    </item>
    <item>
      <title>Another Article</title>
      <link>https://example.com/another</link>
      <description>Another test</description>
    </item>
  </channel>
</rss>"""


@pytest.mark.asyncio
class TestFetchRSSFeedAsync:
    """Test async single feed fetching."""

    async def test_success(self) -> None:
        mock_response = MagicMock()
        mock_response.text = _VALID_RSS
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        source = _make_source()
        items = await fetch_rss_feed_async(source, mock_client)

        assert len(items) == 2
        assert items[0].title == "Test Article"
        assert isinstance(items[0], RSSItem)

    async def test_http_error_returns_empty(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))

        source = _make_source()
        items = await fetch_rss_feed_async(source, mock_client)

        assert items == []

    async def test_no_url_returns_empty(self) -> None:
        source = DataSourceConfig(name="no_url", source_type="rss", url=None)
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        items = await fetch_rss_feed_async(source, mock_client)

        assert items == []


@pytest.mark.asyncio
class TestFetchRSSFeedsConcurrent:
    """Test concurrent multi-feed fetching."""

    async def test_multiple_feeds(self) -> None:
        mock_response = MagicMock()
        mock_response.text = _VALID_RSS
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        sources = [
            _make_source("feed_1", "https://example.com/rss1"),
            _make_source("feed_2", "https://example.com/rss2"),
            _make_source("feed_3", "https://example.com/rss3"),
        ]

        items = await fetch_rss_feeds_concurrent(sources, mock_client)

        # 3 feeds x 2 items each = 6
        assert len(items) == 6

    async def test_one_failure_doesnt_block_others(self) -> None:
        good_response = MagicMock()
        good_response.text = _VALID_RSS
        good_response.raise_for_status = MagicMock()

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise httpx.HTTPError("Feed 2 failed")
            return good_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=side_effect)

        sources = [
            _make_source("feed_1", "https://example.com/rss1"),
            _make_source("feed_2", "https://example.com/rss2"),
            _make_source("feed_3", "https://example.com/rss3"),
        ]

        items = await fetch_rss_feeds_concurrent(sources, mock_client)

        # 2 successful feeds x 2 items = 4
        assert len(items) == 4

    async def test_empty_sources(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        items = await fetch_rss_feeds_concurrent([], mock_client)

        assert items == []

    async def test_respects_max_concurrency(self) -> None:
        """Verify that we don't exceed max_concurrency simultaneous requests."""
        concurrent_count = 0
        max_concurrent = 0

        good_response = MagicMock()
        good_response.text = _VALID_RSS
        good_response.raise_for_status = MagicMock()

        async def counting_get(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.01)  # Small delay to allow overlap
            concurrent_count -= 1
            return good_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=counting_get)

        sources = [_make_source("feed_{}".format(i), "https://example.com/rss{}".format(i)) for i in range(10)]

        items = await fetch_rss_feeds_concurrent(sources, mock_client, max_concurrency=3)

        assert max_concurrent <= 3
        assert len(items) == 20  # 10 feeds x 2 items
