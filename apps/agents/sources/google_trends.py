"""Shared Google Trends source for agent collectors.

Uses the pytrends library (unofficial Google Trends API) to fetch
trending searches, related queries, and regional interest data.

No API key required but subject to Google rate limiting.
Falls back gracefully if pytrends is not installed or Google blocks requests.

Usage:
    from apps.agents.sources.google_trends import fetch_trending_searches

    items = fetch_trending_searches(source_config, region="brazil")
"""

import hashlib
import logging
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

# Lazy-loaded pytrends import — module degrades gracefully if not installed
_pytrends_available = True
try:
    from pytrends.request import TrendReq
except ImportError:
    _pytrends_available = False
    logger.warning("pytrends not installed, Google Trends source unavailable")


@dataclass
class GoogleTrendItem:
    """A single trending topic or related query from Google Trends.

    Hash is computed from keyword+region+trend_type (not URL) because
    Google Trends does not have stable per-result URLs.
    """

    keyword: str
    source_name: str
    trend_type: str  # "trending_search", "related_query", "rising_topic"
    region: str  # "BR", "MX", "AR", "brazil", etc.
    traffic_value: Optional[str] = None  # e.g., "200K+", "500%"
    related_queries: List[str] = field(default_factory=list)
    url: str = ""
    collected_at: Optional[datetime] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            key = f"{self.keyword}-{self.region}-{self.trend_type}"
            self.content_hash = hashlib.md5(key.encode()).hexdigest()
        if not self.url:
            encoded = urllib.parse.quote_plus(self.keyword)
            self.url = (
                f"https://trends.google.com/trends/explore"
                f"?q={encoded}&geo={self.region}"
            )
        if not self.collected_at:
            self.collected_at = datetime.now(timezone.utc)


def fetch_trending_searches(
    source: DataSourceConfig,
    region: str = "brazil",
) -> List[GoogleTrendItem]:
    """Fetch today's trending searches for a region.

    Uses pytrends.trending_searches(). No API key required.

    Args:
        source: DataSourceConfig for provenance/naming.
        region: Region name for pytrends (e.g., "brazil", "mexico").
            Note: pytrends uses lowercase country names, not ISO codes.

    Returns:
        List of GoogleTrendItem. Empty list on error.
    """
    if not _pytrends_available:
        logger.warning("pytrends not available, skipping %s", source.name)
        return []

    try:
        pytrends = TrendReq(hl="pt-BR", tz=180)
        df = pytrends.trending_searches(pn=region)

        items: List[GoogleTrendItem] = []
        for _, row in df.iterrows():
            keyword = str(row[0]).strip()
            if keyword:
                items.append(GoogleTrendItem(
                    keyword=keyword,
                    source_name=source.name,
                    trend_type="trending_search",
                    region=region,
                ))

        logger.info(
            "Fetched %d trending searches from %s (%s)",
            len(items), source.name, region,
        )
        return items
    except Exception as e:
        logger.warning("Google Trends error for %s: %s", source.name, e)
        return []


def fetch_related_queries(
    source: DataSourceConfig,
    keywords: List[str],
    region: str = "BR",
    timeframe: str = "today 3-m",
) -> List[GoogleTrendItem]:
    """Fetch related and rising queries for given keywords.

    Uses pytrends.related_queries() to discover emerging topics
    around known editorial keywords.

    Args:
        source: DataSourceConfig for provenance/naming.
        keywords: List of seed keywords (max 5 per pytrends API).
        region: ISO country code (e.g., "BR", "MX").
        timeframe: Pytrends timeframe (e.g., "today 3-m", "today 1-m").

    Returns:
        List of GoogleTrendItem with trend_type="related_query" or
        "rising_topic". Empty list on error.
    """
    if not _pytrends_available:
        logger.warning("pytrends not available, skipping %s", source.name)
        return []

    if not keywords:
        return []

    # pytrends only supports up to 5 keywords at a time
    keywords = keywords[:5]

    try:
        pytrends = TrendReq(hl="pt-BR", tz=180)
        pytrends.build_payload(keywords, timeframe=timeframe, geo=region)
        related = pytrends.related_queries()

        items: List[GoogleTrendItem] = []
        for kw, data in related.items():
            if data is None:
                continue

            # Rising queries (most interesting for trend detection)
            rising = data.get("rising")
            if rising is not None and not rising.empty:
                for _, row in rising.iterrows():
                    query = str(row.get("query", "")).strip()
                    value = str(row.get("value", ""))
                    if query:
                        items.append(GoogleTrendItem(
                            keyword=query,
                            source_name=source.name,
                            trend_type="related_query",
                            region=region,
                            traffic_value=value,
                            related_queries=[kw],
                        ))

            # Top queries (stable popular queries)
            top = data.get("top")
            if top is not None and not top.empty:
                for _, row in top.head(5).iterrows():  # Limit to top 5
                    query = str(row.get("query", "")).strip()
                    if query and not any(i.keyword == query for i in items):
                        items.append(GoogleTrendItem(
                            keyword=query,
                            source_name=source.name,
                            trend_type="rising_topic",
                            region=region,
                            related_queries=[kw],
                        ))

        logger.info(
            "Fetched %d related queries from %s",
            len(items), source.name,
        )
        return items
    except Exception as e:
        logger.warning(
            "Google Trends related queries error for %s: %s",
            source.name, e,
        )
        return []
