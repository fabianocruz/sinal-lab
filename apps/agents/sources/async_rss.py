"""Async RSS feed fetching for concurrent IO-bound operations.

Async variants of the shared RSS source module. Reuses the synchronous
parse_rss_entry() for CPU-bound parsing — only the HTTP fetch is async.

Usage:
    from apps.agents.sources.async_rss import fetch_rss_feeds_concurrent

    items = await fetch_rss_feeds_concurrent(sources, async_client, max_concurrency=10)
"""

import asyncio
import logging
from typing import List

import feedparser
import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.rss import RSSItem, parse_rss_entry

logger = logging.getLogger(__name__)


async def fetch_rss_feed_async(
    source: DataSourceConfig,
    client: httpx.AsyncClient,
) -> List[RSSItem]:
    """Fetch and parse a single RSS/Atom feed asynchronously.

    Async equivalent of fetch_rss_feed(). Returns empty list on any error.

    Args:
        source: Data source configuration with URL.
        client: Configured httpx.AsyncClient.

    Returns:
        List of parsed RSSItems, empty on error.
    """
    if not source.url:
        logger.warning("Source %s has no URL, skipping", source.name)
        return []

    try:
        response = await client.get(source.url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch %s (%s): %s", source.name, source.url, e)
        return []

    feed = feedparser.parse(response.text)

    if feed.bozo and not feed.entries:
        logger.warning("Feed %s is malformed and has no entries", source.name)
        return []

    items: List[RSSItem] = []
    for entry in feed.entries:
        item = parse_rss_entry(entry, source.name)
        if item:
            items.append(item)

    logger.info("Fetched %d items from %s (async)", len(items), source.name)
    return items


async def fetch_rss_feeds_concurrent(
    sources: List[DataSourceConfig],
    client: httpx.AsyncClient,
    max_concurrency: int = 10,
) -> List[RSSItem]:
    """Fetch multiple RSS feeds concurrently with bounded parallelism.

    Uses asyncio.Semaphore to limit concurrent requests, preventing
    overwhelming target servers or exhausting connection pool.

    Args:
        sources: List of data source configurations.
        client: Configured httpx.AsyncClient.
        max_concurrency: Maximum simultaneous requests (default 10).

    Returns:
        Flat list of all RSSItems from all feeds. Failed feeds are skipped.
    """
    if not sources:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _fetch_with_semaphore(source: DataSourceConfig) -> List[RSSItem]:
        async with semaphore:
            return await fetch_rss_feed_async(source, client)

    results = await asyncio.gather(
        *[_fetch_with_semaphore(s) for s in sources],
        return_exceptions=True,
    )

    all_items: List[RSSItem] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(
                "Feed %s raised unexpected exception: %s",
                sources[i].name,
                result,
            )
            continue
        all_items.extend(result)

    return all_items
