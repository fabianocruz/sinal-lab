"""Multi-source collector for CODIGO agent.

Fetches developer ecosystem signals from GitHub trending, npm, PyPI,
Stack Overflow, and dev community RSS feeds.
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

FETCH_TIMEOUT = 15.0


@dataclass
class DevSignal:
    """A single developer ecosystem signal from any source."""

    title: str
    url: str
    source_name: str
    signal_type: str  # repo, package, tag, article
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    language: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def collect_github_repos(
    source: DataSourceConfig,
    client: httpx.Client,
) -> list[DevSignal]:
    """Fetch trending GitHub repos via the search API."""
    if not source.url:
        return []

    window = source.params.get("window", "daily")
    date_qualifier = "created:>2026-02-10" if window == "daily" else "created:>2026-02-03"

    params = {
        "q": f"stars:>20 {date_qualifier}",
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }

    headers = {"Accept": "application/vnd.github+json"}
    import os
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = client.get(source.url, params=params, headers=headers, timeout=FETCH_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("GitHub API error for %s: %s", source.name, e)
        return []

    data = response.json()
    signals: list[DevSignal] = []

    for repo in data.get("items", []):
        created_at = None
        if repo.get("created_at"):
            try:
                created_at = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
            except ValueError:
                pass

        signals.append(DevSignal(
            title=repo.get("full_name", "unknown"),
            url=repo.get("html_url", ""),
            source_name=source.name,
            signal_type="repo",
            published_at=created_at,
            summary=repo.get("description", ""),
            language=repo.get("language"),
            tags=[repo.get("language", "").lower()] if repo.get("language") else [],
            metrics={
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "open_issues": repo.get("open_issues_count", 0),
                "watchers": repo.get("watchers_count", 0),
            },
        ))

    logger.info("Collected %d repos from %s", len(signals), source.name)
    return signals


def collect_npm_packages(
    source: DataSourceConfig,
    client: httpx.Client,
) -> list[DevSignal]:
    """Fetch popular npm packages via the registry search API."""
    if not source.url:
        return []

    params = {
        "text": "keywords:framework,tool,cli,api",
        "size": 25,
        "quality": source.params.get("quality", 0.8),
        "popularity": source.params.get("popularity", 0.9),
    }

    try:
        response = client.get(source.url, params=params, timeout=FETCH_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("npm registry error for %s: %s", source.name, e)
        return []

    data = response.json()
    signals: list[DevSignal] = []

    for obj in data.get("objects", []):
        pkg = obj.get("package", {})
        name = pkg.get("name", "")
        if not name:
            continue

        published_at = None
        date_str = pkg.get("date")
        if date_str:
            try:
                published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        signals.append(DevSignal(
            title=name,
            url=pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{name}"),
            source_name=source.name,
            signal_type="package",
            published_at=published_at,
            summary=pkg.get("description", ""),
            language="javascript",
            tags=pkg.get("keywords", [])[:10],
            metrics={
                "score_detail": obj.get("score", {}).get("detail", {}),
            },
        ))

    logger.info("Collected %d npm packages from %s", len(signals), source.name)
    return signals


def collect_rss_source(
    source: DataSourceConfig,
    client: httpx.Client,
    signal_type: str = "article",
) -> list[DevSignal]:
    """Fetch and parse an RSS/Atom feed into DevSignals."""
    if not source.url:
        return []

    try:
        response = client.get(source.url, timeout=FETCH_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch %s: %s", source.name, e)
        return []

    feed = feedparser.parse(response.text)
    if feed.bozo and not feed.entries:
        return []

    signals: list[DevSignal] = []
    for entry in feed.entries:
        title = getattr(entry, "title", None)
        link = getattr(entry, "link", None)
        if not title or not link:
            continue

        published_at = None
        for date_field in ("published_parsed", "updated_parsed"):
            parsed = getattr(entry, date_field, None)
            if parsed:
                try:
                    published_at = datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                    break
                except (ValueError, OverflowError, OSError):
                    continue

        summary = getattr(entry, "summary", None)
        if summary and len(summary) > 1000:
            summary = summary[:1000] + "..."

        tags = []
        if hasattr(entry, "tags"):
            for tag in entry.tags:
                term = tag.get("term", "") if isinstance(tag, dict) else getattr(tag, "term", "")
                if term:
                    tags.append(term.strip().lower())

        signals.append(DevSignal(
            title=title.strip(),
            url=link.strip(),
            source_name=source.name,
            signal_type=signal_type,
            published_at=published_at,
            summary=summary,
            tags=tags[:10],
        ))

    logger.info("Collected %d signals from %s", len(signals), source.name)
    return signals


def collect_all_sources(
    sources: list[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "codigo",
    run_id: str = "",
) -> list[DevSignal]:
    """Fetch all configured sources and return deduplicated signals."""
    all_signals: list[DevSignal] = []
    seen_urls: set[str] = set()

    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": "Sinal.lab/0.1 (dev ecosystem monitor)"},
    ) as client:
        for source in sources:
            if not source.enabled:
                continue

            if "github_trending" in source.name:
                signals = collect_github_repos(source, client)
            elif "npm" in source.name:
                signals = collect_npm_packages(source, client)
            elif source.source_type == "rss":
                stype = "package" if "pypi" in source.name else "article"
                signals = collect_rss_source(source, client, signal_type=stype)
            else:
                signals = collect_rss_source(source, client, signal_type="article")

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
        "CODIGO collected %d unique signals from %d sources",
        len(all_signals),
        len([s for s in sources if s.enabled]),
    )
    return all_signals
