"""Multi-source collector for RADAR agent.

Fetches items from HN, GitHub trending, arXiv, and other sources.
Each source has its own parser that normalizes into a common TrendSignal dataclass.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import mktime
from typing import Any, Optional

import feedparser
import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)

FEED_FETCH_TIMEOUT = 15.0


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
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def parse_feed_date(entry: Any) -> Optional[datetime]:
    """Extract publication date from a feed entry."""
    for date_field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, date_field, None)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
    return None


def collect_rss_source(
    source: DataSourceConfig,
    client: httpx.Client,
    source_type: str = "community",
) -> list[TrendSignal]:
    """Fetch and parse a single RSS/Atom feed into TrendSignals."""
    if not source.url:
        return []

    try:
        response = client.get(source.url, timeout=FEED_FETCH_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch %s: %s", source.name, e)
        return []

    feed = feedparser.parse(response.text)
    if feed.bozo and not feed.entries:
        logger.warning("Feed %s is malformed with no entries", source.name)
        return []

    signals: list[TrendSignal] = []
    for entry in feed.entries:
        title = getattr(entry, "title", None)
        link = getattr(entry, "link", None)
        if not title or not link:
            continue

        tags = []
        if hasattr(entry, "tags"):
            for tag in entry.tags:
                term = tag.get("term", "") if isinstance(tag, dict) else getattr(tag, "term", "")
                if term:
                    tags.append(term.strip().lower())

        summary = getattr(entry, "summary", None)
        if summary and len(summary) > 1000:
            summary = summary[:1000] + "..."

        metrics = {}
        # HN entries often have points in the title or description
        if "hn" in source.name.lower():
            comments_link = getattr(entry, "comments", None)
            if comments_link:
                metrics["hn_comments_url"] = comments_link

        signals.append(TrendSignal(
            title=title.strip(),
            url=link.strip(),
            source_name=source.name,
            source_type=source_type,
            published_at=parse_feed_date(entry),
            summary=summary,
            author=getattr(entry, "author", None),
            tags=tags[:10],
            metrics=metrics,
        ))

    logger.info("Collected %d signals from %s", len(signals), source.name)
    return signals


def collect_github_trending(
    source: DataSourceConfig,
    client: httpx.Client,
) -> list[TrendSignal]:
    """Fetch GitHub trending repos via the search API.

    Uses the GitHub search API to find recently created repos with high star counts.
    Falls back gracefully if rate-limited.
    """
    if not source.url:
        return []

    window = source.params.get("window", "daily")
    if window == "daily":
        date_qualifier = "created:>2026-02-10"
    else:
        date_qualifier = "created:>2026-02-03"

    params = {
        "q": f"stars:>50 {date_qualifier}",
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }

    headers = {"Accept": "application/vnd.github+json"}
    github_token = None
    try:
        import os
        github_token = os.getenv("GITHUB_TOKEN")
    except Exception:
        pass

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        response = client.get(
            source.url,
            params=params,
            headers=headers,
            timeout=FEED_FETCH_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("GitHub API error for %s: %s", source.name, e)
        return []

    data = response.json()
    items = data.get("items", [])

    signals: list[TrendSignal] = []
    for repo in items:
        created_at = None
        if repo.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    repo["created_at"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        description = repo.get("description") or ""
        signals.append(TrendSignal(
            title=f"{repo.get('full_name', 'unknown')} — {description[:200]}",
            url=repo.get("html_url", ""),
            source_name=source.name,
            source_type="github",
            published_at=created_at,
            summary=description,
            author=repo.get("owner", {}).get("login", ""),
            tags=[repo.get("language", "").lower()] if repo.get("language") else [],
            metrics={
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "open_issues": repo.get("open_issues_count", 0),
                "language": repo.get("language", ""),
            },
        ))

    logger.info("Collected %d repos from %s", len(signals), source.name)
    return signals


def collect_all_sources(
    sources: list[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "radar",
    run_id: str = "",
) -> list[TrendSignal]:
    """Fetch all configured sources and return deduplicated signals.

    Routes each source to the appropriate collector based on source type
    and name.
    """
    all_signals: list[TrendSignal] = []
    seen_urls: set[str] = set()

    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": "Sinal.lab/0.1 (trend radar)"},
    ) as client:
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
                if signal.content_hash not in seen_urls:
                    seen_urls.add(signal.content_hash)
                    all_signals.append(signal)

                    provenance.track(
                        source_url=signal.url,
                        source_name=source.name,
                        extraction_method="api" if source.source_type == "api" else "rss",
                        confidence=0.6,
                        collector_agent=agent_name,
                        collector_run_id=run_id,
                    )

    logger.info(
        "RADAR collected %d unique signals from %d sources",
        len(all_signals),
        len([s for s in sources if s.enabled]),
    )
    return all_signals
