"""Shared Google News RSS source for all agent collectors.

Builds query-based Google News RSS URLs and delegates to the shared
fetch_rss_feed() parser. No API key required.

Usage:
    from apps.agents.sources.google_news import fetch_google_news

    items = fetch_google_news(source_config, client)
"""

import logging
import urllib.parse
from copy import copy
from typing import Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.rss import RSSItem, fetch_rss_feed

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"

# Country code to ceid mapping for Google News RSS feeds.
# Format: {country_code}: {country_code}:{language_variant}
_CEID_MAP: Dict[str, str] = {
    "BR": "BR:pt-419",
    "MX": "MX:es-419",
    "AR": "AR:es-419",
    "CO": "CO:es-419",
    "CL": "CL:es-419",
    "US": "US:en",
}


def build_google_news_url(
    query: str,
    language: str = "pt-BR",
    country: str = "BR",
    time_range: Optional[str] = "7d",
) -> str:
    """Build a Google News RSS search URL.

    Args:
        query: Search query (e.g., "startup latam fintech").
        language: Language code (e.g., "pt-BR", "es", "en").
        country: Country code (e.g., "BR", "MX", "AR").
        time_range: Time filter appended to query ("1d", "7d", "30d").
            None for no time filter.

    Returns:
        Complete Google News RSS URL.
    """
    search_query = query
    if time_range:
        search_query = f"{query} when:{time_range}"

    ceid = _CEID_MAP.get(country, f"{country}:{language[:2]}")

    params = urllib.parse.urlencode({
        "q": search_query,
        "hl": language,
        "gl": country,
        "ceid": ceid,
    })

    return f"{GOOGLE_NEWS_RSS_BASE}?{params}"


def build_google_news_sources(
    queries: List[Dict],
    prefix: str = "gnews",
) -> List[DataSourceConfig]:
    """Build DataSourceConfig entries from query definitions.

    Convenience function for agent config files. Each query dict is
    converted to a DataSourceConfig with params for fetch-time URL
    construction.

    Args:
        queries: List of dicts with keys: "name", "query", and optionally
            "language", "country", "time_range".
        prefix: Name prefix for sources (default "gnews").

    Returns:
        List of DataSourceConfig entries.
    """
    sources: List[DataSourceConfig] = []
    for q in queries:
        name = f"{prefix}_{q['name']}"
        sources.append(DataSourceConfig(
            name=name,
            source_type="rss",
            url=None,  # Built at fetch time from params
            params={
                "query": q["query"],
                "language": q.get("language", "pt-BR"),
                "country": q.get("country", "BR"),
                "time_range": q.get("time_range", "7d"),
            },
        ))
    return sources


def fetch_google_news(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[RSSItem]:
    """Fetch Google News RSS feed for a configured source.

    Builds URL from source.params, then delegates to fetch_rss_feed()
    for actual HTTP fetching and RSS parsing.

    Expected params keys: "query", "language", "country", "time_range".

    Args:
        source: DataSourceConfig with params containing query info.
        client: Configured httpx.Client.

    Returns:
        List of RSSItems from Google News. Empty on error.
    """
    query = source.params.get("query", "")
    if not query:
        logger.warning(
            "Google News source %s has no query param, skipping", source.name
        )
        return []

    url = build_google_news_url(
        query=query,
        language=source.params.get("language", "pt-BR"),
        country=source.params.get("country", "BR"),
        time_range=source.params.get("time_range", "7d"),
    )

    # Create a copy of the source with the built URL so we
    # do not mutate the caller's DataSourceConfig.
    fetching_source = copy(source)
    fetching_source.url = url

    return fetch_rss_feed(fetching_source, client)
