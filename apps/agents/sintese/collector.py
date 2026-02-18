"""Multi-source collector for SINTESE agent.

Fetches and parses feeds from RSS/Atom sources and X/Twitter API,
deduplicates by URL, and returns structured feed items with provenance tracking.

Architecture:
    This is the main collector orchestrator. It routes each DataSourceConfig
    to the appropriate sub-collector based on source_type:

        collect_all_sources()       <- entry point (called by SinteseAgent.collect)
        |- fetch_rss_feed()         <- source_type="rss"  (shared RSS parser)
        +- twitter_collector.py     <- source_type="api" + "twitter" in name

    All sub-collectors produce FeedItem instances. Cross-source deduplication
    is by content_hash (MD5 of URL), so if a tweet links to the same article
    as an RSS entry, only one FeedItem is kept (first seen wins).

    twitter_collector is imported lazily inside collect_all_sources() to avoid
    circular imports (twitter_collector imports FeedItem from this module).
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
import httpx

from apps.agents.sources.http import create_http_client
from apps.agents.sources.rss import RSSItem, fetch_rss_feed as _fetch_rss_feed
from apps.agents.sources.rss import (  # noqa: F401 — re-exports
    extract_tags,
    parse_feed_date,
    parse_rss_entry as _parse_rss_entry,
)

logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    """A single item collected from any source (RSS/Atom feed or X/Twitter API).

    This is the shared data model for the SINTESE multi-source collector pipeline.
    Both RSS feeds (via fetch_rss_feed) and Twitter (via twitter_collector.parse_tweet)
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
    tags: List[str] = field(default_factory=list)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def _rss_to_feed(rss_item: RSSItem) -> FeedItem:
    """Convert shared RSSItem to SINTESE-specific FeedItem."""
    return FeedItem(
        title=rss_item.title,
        url=rss_item.url,
        source_name=rss_item.source_name,
        published_at=rss_item.published_at,
        summary=rss_item.summary,
        author=rss_item.author,
        tags=rss_item.tags,
        content_hash=rss_item.content_hash,
    )


# Backward-compatible wrappers (used by existing tests and downstream code)
def parse_feed_entry(entry: object, source_name: str) -> Optional[FeedItem]:
    """Parse a feed entry into a FeedItem. Wraps shared parse_rss_entry."""
    rss_item = _parse_rss_entry(entry, source_name)
    if rss_item is None:
        return None
    return _rss_to_feed(rss_item)


def fetch_feed(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[FeedItem]:
    """Fetch and parse a single RSS feed. Wraps shared fetch_rss_feed."""
    rss_items = _fetch_rss_feed(source, client)
    return [_rss_to_feed(ri) for ri in rss_items]


def collect_all_sources(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "sintese",
    run_id: str = "",
) -> List[FeedItem]:
    """Fetch all configured sources (RSS + Twitter) and return deduplicated items.

    Routes each source to the appropriate collector based on source_type:
    - "api" sources with "twitter" in the name -> collect_twitter_sources()
    - all other sources -> fetch_rss_feed() (shared RSS parser)

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
    gnews_sources = [
        s for s in sources
        if s.source_type == "rss" and "gnews" in s.name and s.enabled
    ]
    rss_sources = [
        s for s in sources
        if s.source_type == "rss" and "gnews" not in s.name and s.enabled
    ]
    twitter_sources = [
        s for s in sources
        if s.source_type == "api" and "twitter" in s.name and s.enabled
    ]

    all_items: List[FeedItem] = []
    seen_hashes: set = set()

    def _add_items(items: List[FeedItem], method: str) -> None:
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

    # Collect RSS sources using shared source layer
    with create_http_client() as client:
        for source in rss_sources:
            items = fetch_feed(source, client)
            _add_items(items, "rss")

        # Collect Google News sources (URL built from params at fetch time)
        if gnews_sources:
            from apps.agents.sources.google_news import fetch_google_news

            for source in gnews_sources:
                rss_items = fetch_google_news(source, client)
                gnews_items = [_rss_to_feed(ri) for ri in rss_items]
                _add_items(gnews_items, "rss")

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
        _add_items(twitter_items, "api")

    total_sources = len(rss_sources) + len(gnews_sources) + len(twitter_sources)
    logger.info(
        "Collected %d unique items from %d sources (%d RSS, %d Google News, %d Twitter)",
        len(all_items), total_sources, len(rss_sources), len(gnews_sources), len(twitter_sources),
    )

    return all_items


# Backward-compatible alias
collect_all_feeds = collect_all_sources
