"""X/Twitter API collector for SINTESE agent.

Fetches recent tweets matching editorial territory keywords via the
X API v2 search/recent endpoint. Converts tweets into FeedItems for
unified scoring alongside RSS content.

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
