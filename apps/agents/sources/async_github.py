"""Async GitHub repository fetching for concurrent IO-bound operations.

Async variant of the shared GitHub source module. Reuses the synchronous
JSON-to-GitHubRepoItem parsing — only the HTTP fetch is async.

Usage:
    from apps.agents.sources.async_github import fetch_github_repos_concurrent

    items = await fetch_github_repos_concurrent(sources, async_client, max_concurrency=5)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.github import GitHubRepoItem

logger = logging.getLogger(__name__)


async def fetch_github_repos_async(
    source: DataSourceConfig,
    client: httpx.AsyncClient,
    min_stars: int = 50,
    window: str = "daily",
) -> List[GitHubRepoItem]:
    """Fetch trending repos via GitHub Search API asynchronously.

    Async equivalent of fetch_github_repos(). Returns empty list on any error.

    Args:
        source: Data source configuration with GitHub API URL.
        client: Configured httpx.AsyncClient.
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

    date_qualifier = "created:>{}".format(cutoff.strftime("%Y-%m-%d"))

    params: Dict[str, Any] = {
        "q": "stars:>{} {}".format(min_stars, date_qualifier),
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }

    headers: Dict[str, str] = {"Accept": "application/vnd.github+json"}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = "Bearer {}".format(github_token)

    try:
        response = await client.get(
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

    logger.info("Collected %d repos from %s (async)", len(items), source.name)
    return items


async def fetch_github_repos_concurrent(
    sources: List[DataSourceConfig],
    client: httpx.AsyncClient,
    min_stars: int = 50,
    window: str = "daily",
    max_concurrency: int = 5,
) -> List[GitHubRepoItem]:
    """Fetch repos from multiple GitHub API sources concurrently.

    Uses asyncio.Semaphore to limit concurrent requests, preventing
    GitHub API rate limit exhaustion.

    Args:
        sources: List of data source configurations.
        client: Configured httpx.AsyncClient.
        min_stars: Minimum star count filter.
        window: Time window — "daily" or "weekly".
        max_concurrency: Maximum simultaneous requests (default 5).

    Returns:
        Flat list of all GitHubRepoItems. Failed sources are skipped.
    """
    if not sources:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _fetch_with_semaphore(source: DataSourceConfig) -> List[GitHubRepoItem]:
        async with semaphore:
            return await fetch_github_repos_async(
                source, client, min_stars=min_stars, window=window,
            )

    results = await asyncio.gather(
        *[_fetch_with_semaphore(s) for s in sources],
        return_exceptions=True,
    )

    all_items: List[GitHubRepoItem] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(
                "Source %s raised unexpected exception: %s",
                sources[i].name,
                result,
            )
            continue
        all_items.extend(result)

    return all_items
