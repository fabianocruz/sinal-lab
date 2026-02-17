"""Multi-source collector for SINTESE agent.

Fetches and parses feeds from RSS/Atom sources and X/Twitter API,
deduplicates by URL, and returns structured feed items with provenance tracking.

Architecture:
    This is the main collector orchestrator. It routes each DataSourceConfig
    to the appropriate sub-collector based on source_type:

        collect_all_sources()       ← entry point (called by SinteseAgent.collect)
        ├── fetch_feed()            ← source_type="rss"  (RSS/Atom parser)
        └── twitter_collector.py    ← source_type="api" + "twitter" in name

    All sub-collectors produce FeedItem instances. Cross-source deduplication
    is by content_hash (MD5 of URL), so if a tweet links to the same article
    as an RSS entry, only one FeedItem is kept (first seen wins).

    twitter_collector is imported lazily inside collect_all_sources() to avoid
    circular imports (twitter_collector imports FeedItem from this module).
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
    """A single item collected from any source (RSS/Atom feed or X/Twitter API).

    This is the shared data model for the SINTESE multi-source collector pipeline.
    Both RSS feeds (via fetch_feed) and Twitter (via twitter_collector.parse_tweet)
    produce FeedItems that flow into the scorer for unified relevance ranking.

    The content_hash field enables cross-source deduplication: if a tweet links to
    the same article URL as an RSS entry, only one FeedItem is kept.
    """

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


def collect_all_sources(
    sources: list[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "sintese",
    run_id: str = "",
) -> list[FeedItem]:
    """Fetch all configured sources (RSS + Twitter) and return deduplicated items.

    Routes each source to the appropriate collector based on source_type:
    - "api" sources with "twitter" in the name → collect_twitter_sources()
    - all other sources → fetch_feed() (RSS/Atom)

    Deduplication is by content_hash (MD5 of URL). Items from the same URL
    across different sources/types are kept only once (first seen wins).

    Args:
        sources: List of source configurations (RSS + API).
        provenance: Tracker to record data provenance.
        agent_name: Name of the collecting agent.
        run_id: Current run identifier.

    Returns:
        Deduplicated list of FeedItems from all sources.
    """
    # Separate sources by type
    rss_sources = [s for s in sources if s.source_type == "rss" and s.enabled]
    twitter_sources = [
        s for s in sources
        if s.source_type == "api" and "twitter" in s.name and s.enabled
    ]

    all_items: list[FeedItem] = []
    seen_hashes: set[str] = set()

    def _add_items(items: list[FeedItem], source_name: str, method: str) -> None:
        """Add items to the collection, deduplicating by content_hash."""
        for item in items:
            if item.content_hash not in seen_hashes:
                seen_hashes.add(item.content_hash)
                all_items.append(item)

                provenance.track(
                    source_url=item.url,
                    source_name=item.source_name,
                    extraction_method=method,
                    confidence=0.6 if method == "rss" else 0.4,
                    collector_agent=agent_name,
                    collector_run_id=run_id,
                )

    # Collect RSS sources
    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": "Sinal.lab/0.1 (newsletter aggregator)"},
    ) as client:
        for source in rss_sources:
            items = fetch_feed(source, client)
            _add_items(items, source.name, "rss")

    # Collect Twitter sources (handled by twitter_collector module).
    # Lazy import: twitter_collector imports FeedItem from this module,
    # so a top-level import would create a circular dependency.
    if twitter_sources:
        from apps.agents.sintese.twitter_collector import collect_twitter_sources

        twitter_items = collect_twitter_sources(
            sources=twitter_sources,
            provenance=ProvenanceTracker(),  # Separate tracker (twitter_collector tracks internally)
            agent_name=agent_name,
            run_id=run_id,
        )
        _add_items(twitter_items, "twitter", "api")

    total_sources = len(rss_sources) + len(twitter_sources)
    logger.info(
        "Collected %d unique items from %d sources (%d RSS, %d Twitter)",
        len(all_items), total_sources, len(rss_sources), len(twitter_sources),
    )

    return all_items


# Backward-compatible alias
collect_all_feeds = collect_all_sources
