"""Shared RSS/Atom feed parser for all agent collectors.

Extracts and unifies the common RSS parsing logic that was duplicated
across sintese, radar, codigo, and funding collectors.

Usage:
    from apps.agents.sources.rss import fetch_rss_feed, RSSItem

    items: list[RSSItem] = fetch_rss_feed(source_config, client)
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import mktime
from typing import Any, List, Optional

import feedparser
import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)


@dataclass
class RSSItem:
    """A single item parsed from an RSS/Atom feed.

    Unified data model replacing inline parsing in all collectors.
    Agent-specific collectors convert RSSItem to their domain type
    (FeedItem, TrendSignal, DevSignal, etc.) as needed.
    """

    title: str
    url: str
    source_name: str
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def parse_feed_date(entry: Any) -> Optional[datetime]:
    """Extract and parse the publication date from a feedparser entry.

    Checks published_parsed, updated_parsed, and created_parsed in order.
    Returns None if no valid date is found.
    """
    for date_field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, date_field, None)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
    return None


def extract_tags(entry: Any, max_tags: int = 10) -> List[str]:
    """Extract normalized tags/categories from a feedparser entry.

    Handles both dict-style and object-style tag entries from feedparser.
    Returns lowercased, stripped tags up to max_tags.
    """
    tags: List[str] = []
    if not hasattr(entry, "tags"):
        return tags

    for tag in entry.tags:
        term = (
            tag.get("term", "")
            if isinstance(tag, dict)
            else getattr(tag, "term", "")
        )
        if term:
            tags.append(term.strip().lower())

    return tags[:max_tags]


def parse_rss_entry(entry: Any, source_name: str) -> Optional[RSSItem]:
    """Parse a single feedparser entry into an RSSItem.

    Returns None if the entry lacks required fields (title + link).
    """
    title = getattr(entry, "title", None)
    link = getattr(entry, "link", None)

    if not title or not link:
        return None

    summary = getattr(entry, "summary", None)
    if summary and len(summary) > 1000:
        summary = summary[:1000] + "..."

    author = getattr(entry, "author", None)

    return RSSItem(
        title=title.strip(),
        url=link.strip(),
        source_name=source_name,
        published_at=parse_feed_date(entry),
        summary=summary,
        author=author,
        tags=extract_tags(entry),
    )


def fetch_rss_feed(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[RSSItem]:
    """Fetch and parse a single RSS/Atom feed.

    Returns a list of RSSItems. Returns empty list on any error
    (network, parse, timeout) rather than raising.

    Args:
        source: Data source configuration with URL.
        client: Configured httpx.Client (use create_http_client()).

    Returns:
        List of parsed RSSItems, empty on error.
    """
    if not source.url:
        logger.warning("Source %s has no URL, skipping", source.name)
        return []

    try:
        response = client.get(source.url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch %s (%s): %s", source.name, source.url, e)
        return []

    feed = feedparser.parse(response.text)

    if feed.bozo and not feed.entries:
        logger.warning("Feed %s is malformed and has no entries", source.name)
        return []

    entries = feed.entries
    if source.max_items is not None:
        entries = entries[:source.max_items]

    items: List[RSSItem] = []
    for entry in entries:
        item = parse_rss_entry(entry, source.name)
        if item:
            items.append(item)

    logger.info("Fetched %d items from %s", len(items), source.name)
    return items
