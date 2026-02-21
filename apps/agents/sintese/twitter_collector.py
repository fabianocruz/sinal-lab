"""X/Twitter API collector for SINTESE agent.

Fetches recent tweets matching editorial territory keywords via the
X API v2 search/recent endpoint. Converts tweets into FeedItems for
unified scoring alongside RSS content.

Architecture:
    This module is one leg of SINTESE's multi-source collector pipeline:

        collector.py (orchestrator)
        ├── fetch_feed()              ← RSS/Atom sources
        └── twitter_collector.py      ← X/Twitter API (this module)
                ├── build_twitter_queries()    → 1 query per editorial territory
                ├── fetch_twitter_results()    → X API v2 search/recent
                ├── parse_tweet()              → tweet JSON → FeedItem
                └── collect_twitter_sources()  → orchestrate all territories

    Both RSS and Twitter produce FeedItem instances (defined in collector.py),
    which flow into scorer.py for unified relevance ranking. Cross-source
    deduplication happens via content_hash (MD5 of article URL).

Requires X_BEARER_TOKEN environment variable. Degrades gracefully
(returns empty list) when the token is not set.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sintese.collector import FeedItem
from packages.editorial.guidelines import EDITORIAL_TERRITORIES

logger = logging.getLogger(__name__)

# X API v2 search/recent endpoint
TWITTER_API_URL = "https://api.twitter.com/2/tweets/search/recent"

# Timeout for individual API calls (seconds)
TWITTER_FETCH_TIMEOUT = 10.0

# X API Basic tier: 512 char query limit
MAX_QUERY_LENGTH = 512

# Suffix appended to every query
_QUERY_SUFFIX = " has:links -is:retweet (lang:en OR lang:pt)"


def build_twitter_queries() -> dict[str, str]:
    """Build one X API search query per editorial territory.

    Uses keywords from EDITORIAL_TERRITORIES. Each query is OR-joined
    keywords wrapped in parentheses, followed by filters for links,
    no retweets, and English/Portuguese language.

    Multi-word keywords are quoted. Queries are truncated to stay
    within the 512-character X API limit.

    Returns:
        Dict mapping territory key to query string.
    """
    queries: dict[str, str] = {}

    for territory_key, territory in EDITORIAL_TERRITORIES.items():
        keywords = territory.get("keywords", [])
        if not keywords:
            queries[territory_key] = f"({territory_key}){_QUERY_SUFFIX}"
            continue

        # Format keywords: quote multi-word, leave single-word as-is
        formatted: list[str] = []
        for kw in keywords:
            if " " in kw:
                formatted.append(f'"{kw}"')
            else:
                formatted.append(kw)

        # Build query, truncating keywords to fit within limit
        # Reserve space for: "(" + ")" + suffix
        max_keywords_len = MAX_QUERY_LENGTH - len(_QUERY_SUFFIX) - 2  # 2 for parens

        keyword_parts: list[str] = []
        current_len = 0
        for kw in formatted:
            # " OR " separator = 4 chars (except for first keyword)
            separator_len = 4 if keyword_parts else 0
            needed = separator_len + len(kw)
            if current_len + needed > max_keywords_len:
                break
            keyword_parts.append(kw)
            current_len += needed

        query = f"({' OR '.join(keyword_parts)}){_QUERY_SUFFIX}"
        queries[territory_key] = query

    return queries


def parse_tweet(
    tweet: dict,
    source_name: str,
    users: dict[str, dict],
) -> Optional[FeedItem]:
    """Parse an X API v2 tweet JSON object into a FeedItem.

    Uses the expanded URL from entities.urls as FeedItem.url when available,
    falling back to the tweet permalink on x.com. The content_hash is
    computed from the resolved URL to enable cross-source dedup with RSS
    items that link to the same article.

    Args:
        tweet: Raw tweet dict from X API v2 response data[].
        source_name: Source name for this item (e.g. "twitter_fintech").
        users: Dict mapping author_id to user dict (from includes.users).

    Returns:
        FeedItem or None if tweet lacks required fields.
    """
    tweet_id = tweet.get("id")
    text = tweet.get("text", "")

    if not tweet_id or not text:
        return None

    # Extract the first expanded URL from entities (the linked article)
    expanded_url = None
    entities = tweet.get("entities", {})
    urls = entities.get("urls", [])
    for url_entity in urls:
        candidate = url_entity.get("expanded_url", "")
        # Skip t.co links and Twitter/X internal links
        if candidate and "t.co" not in candidate:
            expanded_url = candidate
            break

    # Fallback: tweet permalink
    if not expanded_url:
        expanded_url = f"https://x.com/i/status/{tweet_id}"

    # Author from includes.users
    author_id = tweet.get("author_id", "")
    user = users.get(author_id, {})
    username = user.get("username", "")
    author = f"@{username}" if username else None

    # Parse created_at
    published_at = None
    created_at = tweet.get("created_at")
    if created_at:
        try:
            published_at = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    # Truncate long text for summary
    summary = text
    if len(summary) > 1000:
        summary = summary[:1000] + "..."

    # Use first ~100 chars of text as title
    title = text[:100].strip()
    if len(text) > 100:
        title += "..."

    return FeedItem(
        title=title,
        url=expanded_url,
        source_name=source_name,
        published_at=published_at,
        summary=summary,
        author=author,
        tags=[],
        content_hash=hashlib.md5(expanded_url.encode()).hexdigest(),
    )


def fetch_twitter_results(
    query: str,
    bearer_token: str,
    client: httpx.Client,
    source_name: str = "twitter",
    max_results: int = 50,
) -> list[FeedItem]:
    """Fetch tweets matching query from X API v2 search/recent.

    Returns parsed FeedItems. Returns empty list on any API error
    (auth, rate limit, network, malformed response).

    Args:
        query: X API search query string.
        bearer_token: X API Bearer token.
        client: httpx Client instance.
        source_name: Source name for resulting FeedItems.
        max_results: Max tweets per request (10-100, default 50).

    Returns:
        List of FeedItems parsed from matching tweets.
    """
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,entities",
        "expansions": "author_id",
        "user.fields": "username",
    }
    headers = {
        "Authorization": f"Bearer {bearer_token}",
    }

    try:
        response = client.get(
            TWITTER_API_URL,
            params=params,
            headers=headers,
            timeout=TWITTER_FETCH_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Twitter API error for %s: %s", source_name, e)
        return []

    data = response.json()
    tweets = data.get("data", [])
    if not tweets:
        return []

    # Build users lookup from includes
    users: dict[str, dict] = {}
    includes = data.get("includes", {})
    for user in includes.get("users", []):
        users[user.get("id", "")] = user

    items: list[FeedItem] = []
    for tweet in tweets:
        item = parse_tweet(tweet, source_name, users)
        if item:
            items.append(item)

    logger.info("Fetched %d items from Twitter (%s)", len(items), source_name)
    return items


def collect_twitter_sources(
    sources: list[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "sintese",
    run_id: str = "",
) -> list[FeedItem]:
    """Collect items from X/Twitter API for all configured Twitter sources.

    Skips silently if X_BEARER_TOKEN env var is not set. Builds a query
    per source (territory) using build_twitter_queries(), fetches results,
    deduplicates by content_hash, and tracks provenance.

    Args:
        sources: List of Twitter DataSourceConfig entries.
        provenance: Tracker for data provenance records.
        agent_name: Name of the collecting agent.
        run_id: Current run identifier.

    Returns:
        Deduplicated list of FeedItems from Twitter.
    """
    bearer_token = os.environ.get("X_BEARER_TOKEN", "")
    if not bearer_token:
        logger.warning("X_BEARER_TOKEN not set, skipping Twitter collection")
        return []

    queries = build_twitter_queries()
    all_items: list[FeedItem] = []
    seen_hashes: set[str] = set()

    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": "Sinal.lab/0.1 (newsletter aggregator)"},
    ) as client:
        for source in sources:
            if not source.enabled:
                continue

            territory = source.params.get("territory", "")
            query = queries.get(territory)
            if not query:
                logger.warning(
                    "No query for territory %s (source %s), skipping",
                    territory, source.name,
                )
                continue

            items = fetch_twitter_results(
                query=query,
                bearer_token=bearer_token,
                client=client,
                source_name=source.name,
            )

            for item in items:
                if item.content_hash not in seen_hashes:
                    seen_hashes.add(item.content_hash)
                    all_items.append(item)

                    provenance.track(
                        source_url=item.url,
                        source_name=source.name,
                        extraction_method="api",
                        confidence=0.4,
                        collector_agent=agent_name,
                        collector_run_id=run_id,
                    )

    logger.info(
        "Twitter collected %d unique items from %d sources",
        len(all_items),
        len([s for s in sources if s.enabled]),
    )
    return all_items
