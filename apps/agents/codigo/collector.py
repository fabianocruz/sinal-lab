"""Multi-source collector for CODIGO agent.

Fetches developer ecosystem signals from GitHub trending, npm, PyPI,
Stack Overflow, and dev community RSS feeds.
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
from apps.agents.sources.rss import RSSItem, fetch_rss_feed

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
    tags: List[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    content_hash: str = ""
    image_url: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def _rss_to_signal(item: RSSItem, signal_type: str) -> DevSignal:
    """Convert a shared RSSItem to a CODIGO DevSignal."""
    return DevSignal(
        title=item.title,
        url=item.url,
        source_name=item.source_name,
        signal_type=signal_type,
        published_at=item.published_at,
        summary=item.summary,
        tags=item.tags,
        content_hash=item.content_hash,
        image_url=item.image_url,
    )


def _github_to_signal(repo: GitHubRepoItem) -> DevSignal:
    """Convert a shared GitHubRepoItem to a CODIGO DevSignal."""
    return DevSignal(
        title=repo.full_name,
        url=repo.url,
        source_name=repo.source_name,
        signal_type="repo",
        published_at=repo.created_at,
        summary=repo.description or "",
        language=repo.language,
        tags=[repo.language.lower()] if repo.language else [],
        metrics={
            "stars": repo.stars,
            "forks": repo.forks,
            "open_issues": repo.open_issues,
            "watchers": 0,
        },
        content_hash=repo.content_hash,
    )


def collect_github_repos(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[DevSignal]:
    """Fetch trending GitHub repos via the search API."""
    window = source.params.get("window", "daily")
    repos = fetch_github_repos(source, client, min_stars=20, window=window)
    return [_github_to_signal(repo) for repo in repos]


def collect_npm_packages(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[DevSignal]:
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
    signals: List[DevSignal] = []

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
            url=pkg.get("links", {}).get("npm", "https://www.npmjs.com/package/{}".format(name)),
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
) -> List[DevSignal]:
    """Fetch and parse an RSS/Atom feed into DevSignals."""
    rss_items = fetch_rss_feed(source, client)
    return [_rss_to_signal(item, signal_type) for item in rss_items]


def collect_all_sources(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "codigo",
    run_id: str = "",
) -> List[DevSignal]:
    """Fetch all configured sources and return deduplicated signals."""
    all_signals: List[DevSignal] = []

    with create_http_client() as client:
        for source in sources:
            if not source.enabled:
                continue

            if "github_trending" in source.name:
                signals = collect_github_repos(source, client)
            elif "npm" in source.name:
                signals = collect_npm_packages(source, client)
            elif "reddit" in source.name:
                from apps.agents.sources.reddit import fetch_subreddit_posts
                subreddit = source.params.get("subreddit", "")
                sort = source.params.get("sort", "hot")
                limit = source.params.get("limit", 25)
                posts = fetch_subreddit_posts(source, client, subreddit=subreddit, sort=sort, limit=limit)
                signals = [
                    DevSignal(
                        title=p.title,
                        url=p.url,
                        source_name=source.name,
                        signal_type="article",
                        published_at=p.created_utc,
                        summary=p.selftext[:500] if p.selftext else None,
                        tags=[f"r/{p.subreddit}"],
                        metrics={"score": p.score, "comments": p.num_comments},
                        content_hash=p.content_hash,
                    )
                    for p in posts
                ]
            elif "producthunt" in source.name:
                from apps.agents.sources.producthunt import fetch_producthunt_posts
                limit = source.params.get("limit", 20)
                posts = fetch_producthunt_posts(source, client, limit=limit)
                signals = [
                    DevSignal(
                        title=f"{p.name} — {p.tagline}",
                        url=p.website or p.url,
                        source_name=source.name,
                        signal_type="package",
                        published_at=p.created_at,
                        summary=p.description or p.tagline,
                        tags=[t.lower() for t in p.topics[:5]],
                        metrics={"votes": p.votes_count, "comments": p.comments_count},
                        content_hash=p.content_hash,
                    )
                    for p in posts
                ]
            elif source.source_type == "rss":
                stype = "package" if "pypi" in source.name else "article"
                signals = collect_rss_source(source, client, signal_type=stype)
            else:
                signals = collect_rss_source(source, client, signal_type="article")

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
        "CODIGO collected %d unique signals from %d sources",
        len(unique_signals),
        len([s for s in sources if s.enabled]),
    )
    return unique_signals
