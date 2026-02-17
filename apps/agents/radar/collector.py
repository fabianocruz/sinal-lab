"""Multi-source collector for RADAR agent.

Fetches items from HN, GitHub trending, arXiv, and other sources.
Each source has its own parser that normalizes into a common TrendSignal dataclass.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.dedup import deduplicate_by_hash
from apps.agents.sources.github import GitHubRepoItem, fetch_github_repos
from apps.agents.sources.http import create_http_client
from apps.agents.sources.rss import (
    RSSItem,
    fetch_rss_feed,
    parse_feed_date,  # noqa: F401 — re-export
)

logger = logging.getLogger(__name__)


@dataclass
class TrendSignal:
    """A single signal/item from any source tracked by RADAR."""

    title: str
    url: str
    source_name: str
    source_type: str  # hn, github, arxiv, trends, community
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def _rss_to_signal(item: RSSItem, source_type: str) -> TrendSignal:
    """Convert a shared RSSItem to a RADAR TrendSignal."""
    return TrendSignal(
        title=item.title,
        url=item.url,
        source_name=item.source_name,
        source_type=source_type,
        published_at=item.published_at,
        summary=item.summary,
        author=item.author,
        tags=item.tags,
        content_hash=item.content_hash,
    )


def _github_to_signal(repo: GitHubRepoItem) -> TrendSignal:
    """Convert a shared GitHubRepoItem to a RADAR TrendSignal."""
    description = repo.description or ""
    return TrendSignal(
        title="{} \u2014 {}".format(repo.full_name, description[:200]),
        url=repo.url,
        source_name=repo.source_name,
        source_type="github",
        published_at=repo.created_at,
        summary=description,
        author=repo.full_name.split("/")[0] if "/" in repo.full_name else "",
        tags=[repo.language.lower()] if repo.language else [],
        metrics={
            "stars": repo.stars,
            "forks": repo.forks,
            "open_issues": repo.open_issues,
            "language": repo.language or "",
        },
        content_hash=repo.content_hash,
    )


def collect_rss_source(
    source: DataSourceConfig,
    client: httpx.Client,
    source_type: str = "community",
) -> List[TrendSignal]:
    """Fetch and parse a single RSS/Atom feed into TrendSignals."""
    rss_items = fetch_rss_feed(source, client)
    return [_rss_to_signal(item, source_type) for item in rss_items]


def collect_github_trending(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[TrendSignal]:
    """Fetch GitHub trending repos via the search API.

    Uses the shared GitHub collector with RADAR-specific min_stars=50
    and converts results to TrendSignal with title format:
    "{full_name} — {description[:200]}"
    """
    window = source.params.get("window", "daily")
    repos = fetch_github_repos(source, client, min_stars=50, window=window)
    return [_github_to_signal(repo) for repo in repos]


def collect_all_sources(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "radar",
    run_id: str = "",
) -> List[TrendSignal]:
    """Fetch all configured sources and return deduplicated signals.

    Routes each source to the appropriate collector based on source type
    and name.
    """
    all_signals: List[TrendSignal] = []

    with create_http_client() as client:
        for source in sources:
            if not source.enabled:
                continue

            if "github_trending" in source.name:
                signals = collect_github_trending(source, client)
            elif "arxiv" in source.name:
                signals = collect_rss_source(source, client, source_type="arxiv")
            elif "hn" in source.name:
                signals = collect_rss_source(source, client, source_type="hn")
            elif "google_trends" in source.name:
                signals = collect_rss_source(source, client, source_type="trends")
            else:
                signals = collect_rss_source(source, client, source_type="community")

            for signal in signals:
                provenance.track(
                    source_url=signal.url,
                    source_name=source.name,
                    extraction_method="api" if source.source_type == "api" else "rss",
                    confidence=0.6,
                    collector_agent=agent_name,
                    collector_run_id=run_id,
                )

            all_signals.extend(signals)

    unique_signals = deduplicate_by_hash(all_signals, hash_fn=lambda s: s.content_hash)

    logger.info(
        "RADAR collected %d unique signals from %d sources",
        len(unique_signals),
        len([s for s in sources if s.enabled]),
    )
    return unique_signals
