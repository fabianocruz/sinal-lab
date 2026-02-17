"""RSS/Atom feed collector for SINTESE agent.

Fetches and parses feeds from configured sources, deduplicates by URL,
and returns structured feed items with provenance tracking.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from time import mktime

import feedparser
import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)

# Timeout for individual feed fetches (seconds)
FEED_FETCH_TIMEOUT = 15.0


@dataclass
class FeedItem:
    """A single item collected from an RSS/Atom feed."""

    title: str
    url: str
    source_name: str
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def parse_feed_date(entry: Any) -> Optional[datetime]:
    """Extract and parse the publication date from a feed entry.

    Handles multiple date formats commonly found in RSS/Atom feeds.
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


def extract_tags(entry: Any) -> list[str]:
    """Extract tags/categories from a feed entry."""
    tags = []
    if hasattr(entry, "tags"):
        for tag in entry.tags:
            term = tag.get("term", "") if isinstance(tag, dict) else getattr(tag, "term", "")
            if term:
                tags.append(term.strip().lower())
    return tags[:10]  # Cap at 10 tags


def parse_feed_entry(entry: Any, source_name: str) -> Optional[FeedItem]:
    """Parse a single feed entry into a FeedItem.

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

    return FeedItem(
        title=title.strip(),
        url=link.strip(),
        source_name=source_name,
        published_at=parse_feed_date(entry),
        summary=summary,
        author=author,
        tags=extract_tags(entry),
    )


def fetch_feed(
    source: DataSourceConfig,
    client: httpx.Client,
) -> list[FeedItem]:
    """Fetch and parse a single RSS/Atom feed.

    Returns a list of FeedItems. Returns empty list on any error
    (network, parse, timeout) rather than raising.
    """
    if not source.url:
        logger.warning("Source %s has no URL, skipping", source.name)
        return []

    try:
        response = client.get(source.url, timeout=FEED_FETCH_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch %s (%s): %s", source.name, source.url, e)
        return []

    feed = feedparser.parse(response.text)

    if feed.bozo and not feed.entries:
        logger.warning("Feed %s is malformed and has no entries", source.name)
        return []

    items: list[FeedItem] = []
    for entry in feed.entries:
        item = parse_feed_entry(entry, source.name)
        if item:
            items.append(item)

    logger.info("Fetched %d items from %s", len(items), source.name)
    return items


def collect_all_feeds(
    sources: list[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "sintese",
    run_id: str = "",
) -> list[FeedItem]:
    """Fetch all configured feeds and return deduplicated items.

    Deduplication is by URL (content_hash). Items from the same URL
    across different feeds are kept only once (first seen wins).

    Args:
        sources: List of feed source configurations.
        provenance: Tracker to record data provenance.
        agent_name: Name of the collecting agent.
        run_id: Current run identifier.

    Returns:
        Deduplicated list of FeedItems from all sources.
    """
    all_items: list[FeedItem] = []
    seen_urls: set[str] = set()

    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": "Sinal.lab/0.1 (newsletter aggregator)"},
    ) as client:
        for source in sources:
            if not source.enabled:
                continue

            items = fetch_feed(source, client)

            for item in items:
                if item.content_hash not in seen_urls:
                    seen_urls.add(item.content_hash)
                    all_items.append(item)

                    provenance.track(
                        source_url=item.url,
                        source_name=source.name,
                        extraction_method="rss",
                        confidence=0.6,
                        collector_agent=agent_name,
                        collector_run_id=run_id,
                    )

    logger.info(
        "Collected %d unique items from %d sources (%d duplicates removed)",
        len(all_items),
        len([s for s in sources if s.enabled]),
        len(seen_urls) - len(all_items) if len(seen_urls) > len(all_items) else 0,
    )

    return all_items
