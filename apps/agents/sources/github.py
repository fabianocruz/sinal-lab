"""Shared GitHub repository collector for agent collectors.

Fetches trending repos via the GitHub Search API, replacing duplicated
code in radar/collector.py and codigo/collector.py.

Usage:
    from apps.agents.sources.github import fetch_github_repos

    items = fetch_github_repos(source_config, client, min_stars=50)
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepoItem:
    """A GitHub repository from the search API.

    Unified data model replacing TrendSignal (radar) and DevSignal (codigo)
    for GitHub-sourced items.
    """

    full_name: str
    url: str
    description: str
    source_name: str
    created_at: Optional[datetime] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def fetch_github_repos(
    source: DataSourceConfig,
    client: httpx.Client,
    min_stars: int = 50,
    window: str = "daily",
) -> List[GitHubRepoItem]:
    """Fetch trending repos via GitHub Search API.

    Args:
        source: Data source configuration with GitHub API URL.
        client: Configured httpx.Client.
        min_stars: Minimum star count filter (radar=50, codigo=20).
        window: Time window — "daily" (7 days) or "weekly" (14 days).

    Returns:
        List of GitHubRepoItem. Empty list on error.
    """
    if not source.url:
        return []

    now = datetime.now(timezone.utc)
    if window == "weekly":
        cutoff = now - timedelta(days=14)
    else:
        cutoff = now - timedelta(days=7)

    date_qualifier = f"created:>{cutoff.strftime('%Y-%m-%d')}"

    params: Dict[str, Any] = {
        "q": f"stars:>{min_stars} {date_qualifier}",
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }

    headers: Dict[str, str] = {"Accept": "application/vnd.github+json"}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        response = client.get(
            source.url,
            params=params,
            headers=headers,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("GitHub API error for %s: %s", source.name, e)
        return []

    data = response.json()
    items_data = data.get("items", [])

    items: List[GitHubRepoItem] = []
    for repo in items_data:
        created_at = None
        if repo.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    repo["created_at"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        items.append(GitHubRepoItem(
            full_name=repo.get("full_name", "unknown"),
            url=repo.get("html_url", ""),
            description=repo.get("description") or "",
            source_name=source.name,
            created_at=created_at,
            language=repo.get("language"),
            stars=repo.get("stargazers_count", 0),
            forks=repo.get("forks_count", 0),
            open_issues=repo.get("open_issues_count", 0),
        ))

    logger.info("Collected %d repos from %s", len(items), source.name)
    return items
