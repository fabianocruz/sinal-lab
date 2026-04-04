"""Polymarket prediction market data connector.

Fetches trending markets, odds, and resolution data from Polymarket's
public API. Prediction market data provides a unique "money-weighted"
signal about what the market believes will happen.

No authentication required for public market data.
For trading: requires API key + wallet (not needed for signal intelligence).

Docs: https://docs.polymarket.com
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.http import HttpClientConfig, create_http_client

logger = logging.getLogger(__name__)

POLYMARKET_API = "https://clob.polymarket.com"
POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com"


@dataclass
class PredictionMarket:
    """A Polymarket prediction market with current odds."""

    title: str
    url: str
    description: str = ""
    category: str = ""
    outcome_yes: float = 0.0  # 0-1 probability
    outcome_no: float = 0.0
    volume_usd: float = 0.0
    liquidity_usd: float = 0.0
    end_date: Optional[str] = None
    is_active: bool = True
    tags: List[str] = field(default_factory=list)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def fetch_trending_markets(
    source: DataSourceConfig,
    client: Optional[httpx.Client] = None,
    limit: int = 25,
    categories: Optional[List[str]] = None,
) -> List[PredictionMarket]:
    """Fetch trending/active markets from Polymarket.

    Uses the Gamma API (public, no auth) for market discovery.

    Args:
        source: DataSourceConfig for provenance.
        client: Optional httpx client.
        limit: Max markets to return.
        categories: Optional category filter (e.g., ["crypto", "politics", "tech"]).

    Returns:
        List of PredictionMarket. Empty on failure.
    """
    own_client = client is None
    if own_client:
        client = create_http_client(HttpClientConfig(timeout=15.0))

    try:
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false",
        }

        response = client.get(
            f"{POLYMARKET_GAMMA_API}/markets",
            params=params,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        markets = []
        for item in data if isinstance(data, list) else data.get("data", []):
            if not isinstance(item, dict):
                continue

            title = item.get("question") or item.get("title") or ""
            if not title:
                continue

            slug = item.get("slug") or item.get("condition_id") or ""
            url = f"https://polymarket.com/event/{slug}" if slug else ""

            category = item.get("category") or ""
            if categories and category.lower() not in [c.lower() for c in categories]:
                continue

            # Parse outcomes
            outcome_yes = 0.0
            outcome_no = 0.0
            outcomes = item.get("outcomePrices") or item.get("outcome_prices") or ""
            if isinstance(outcomes, str) and outcomes:
                try:
                    import json
                    prices = json.loads(outcomes)
                    if len(prices) >= 2:
                        outcome_yes = float(prices[0])
                        outcome_no = float(prices[1])
                except (json.JSONDecodeError, ValueError, IndexError):
                    pass
            elif isinstance(outcomes, list) and len(outcomes) >= 2:
                try:
                    outcome_yes = float(outcomes[0])
                    outcome_no = float(outcomes[1])
                except (ValueError, TypeError):
                    pass

            volume = 0.0
            for vol_key in ["volume", "volume24hr", "volumeNum"]:
                if vol_key in item and item[vol_key]:
                    try:
                        volume = float(item[vol_key])
                        break
                    except (ValueError, TypeError):
                        pass

            liquidity = 0.0
            for liq_key in ["liquidity", "liquidityNum"]:
                if liq_key in item and item[liq_key]:
                    try:
                        liquidity = float(item[liq_key])
                        break
                    except (ValueError, TypeError):
                        pass

            tags = []
            if item.get("tags"):
                tags = item["tags"] if isinstance(item["tags"], list) else []

            markets.append(PredictionMarket(
                title=title,
                url=url,
                description=item.get("description") or "",
                category=category,
                outcome_yes=outcome_yes,
                outcome_no=outcome_no,
                volume_usd=volume,
                liquidity_usd=liquidity,
                end_date=item.get("end_date_iso") or item.get("endDate"),
                is_active=item.get("active", True),
                tags=tags,
            ))

        logger.info("Polymarket: fetched %d trending markets", len(markets))
        return markets[:limit]

    except httpx.TimeoutException:
        logger.warning("Polymarket API timeout")
        return []
    except httpx.HTTPError as e:
        logger.warning("Polymarket API error: %s", e)
        return []
    except Exception as e:
        logger.warning("Polymarket unexpected error: %s", e)
        return []
    finally:
        if own_client:
            client.close()


def collect_polymarket_signals(
    provenance: ProvenanceTracker,
    limit: int = 20,
    categories: Optional[List[str]] = None,
) -> List[PredictionMarket]:
    """Collect prediction market data as signals.

    Args:
        provenance: Provenance tracker.
        limit: Max markets.
        categories: Category filter.

    Returns:
        List of PredictionMarket.
    """
    source = DataSourceConfig(
        name="polymarket",
        source_type="api",
        url=POLYMARKET_GAMMA_API,
    )

    markets = fetch_trending_markets(source, limit=limit, categories=categories)

    for m in markets:
        provenance.track(
            source_url=m.url,
            source_name="polymarket",
            extraction_method="api",
        )

    return markets
