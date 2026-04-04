"""Monid data discovery and execution connector.

Monid is a marketplace of data endpoints (Apify, web scrapers, etc.)
that enables agents to discover, inspect, and run data collection
endpoints across the web. Useful for social media data that requires
scraping (LinkedIn posts, Twitter at scale, Reddit threads).

IMPORTANT: Monid charges per result. Use with cost awareness.
Twitter: ~$0.0006/tweet, LinkedIn: ~$0.018/post, Reddit: varies.

Requires MONID_API_KEY env var.
Docs: https://monid.ai/SKILL.md
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.http import HttpClientConfig, create_http_client

logger = logging.getLogger(__name__)

MONID_API_BASE = "https://api.monid.ai/v1"


def _get_api_key() -> str:
    return os.environ.get("MONID_API_KEY", "")


def is_available() -> bool:
    return bool(_get_api_key())


def discover(query: str, limit: int = 5) -> List[Dict]:
    """Discover available data endpoints for a query.

    Args:
        query: Natural language search (e.g., "twitter sentiment fintech")
        limit: Max results

    Returns:
        List of endpoint dicts with provider, endpoint, description, price.
    """
    if not is_available():
        return []

    try:
        client = create_http_client(HttpClientConfig(timeout=15.0))
        response = client.post(
            f"{MONID_API_BASE}/discover",
            headers={
                "Authorization": f"Bearer {_get_api_key()}",
                "Content-Type": "application/json",
            },
            json={"query": query},
        )
        response.raise_for_status()
        data = response.json()
        client.close()
        return data.get("results", [])[:limit]
    except Exception as e:
        logger.warning("Monid discover failed: %s", e)
        return []


def run_endpoint(
    provider: str,
    endpoint: str,
    input_data: Dict[str, Any],
    wait: bool = True,
    timeout: int = 120,
) -> Optional[Dict]:
    """Execute a Monid data endpoint.

    Args:
        provider: Provider slug (e.g., "apify")
        endpoint: Endpoint path (e.g., "/apidojo/tweet-scraper")
        input_data: Input parameters for the endpoint
        wait: If True, poll until complete
        timeout: Max wait time in seconds

    Returns:
        Result dict or None on failure.
    """
    if not is_available():
        logger.warning("MONID_API_KEY not set")
        return None

    try:
        client = create_http_client(HttpClientConfig(timeout=30.0))

        # Start the run
        response = client.post(
            f"{MONID_API_BASE}/run",
            headers={
                "Authorization": f"Bearer {_get_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "provider": provider,
                "endpoint": endpoint,
                "input": input_data,
            },
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data.get("runId") or run_data.get("run_id")

        if not run_id:
            logger.warning("Monid run returned no run_id: %s", run_data)
            client.close()
            return run_data  # Maybe the result is inline

        if not wait:
            client.close()
            return {"run_id": run_id, "status": "running"}

        # Poll for completion
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(3)
            poll = client.get(
                f"{MONID_API_BASE}/runs/{run_id}",
                headers={"Authorization": f"Bearer {_get_api_key()}"},
            )
            poll.raise_for_status()
            result = poll.json()

            status = result.get("status", "")
            if status in ("SUCCEEDED", "completed", "done"):
                client.close()
                return result
            elif status in ("FAILED", "error"):
                logger.warning("Monid run %s failed: %s", run_id, result.get("error"))
                client.close()
                return None

        logger.warning("Monid run %s timed out after %ds", run_id, timeout)
        client.close()
        return None

    except Exception as e:
        logger.warning("Monid run failed: %s", e)
        return None


def fetch_tweets(
    query: str,
    max_results: int = 50,
    provenance: Optional[ProvenanceTracker] = None,
) -> List[Dict]:
    """Fetch tweets via Monid's Apify tweet scraper.

    Cost: ~$0.0006 per tweet (~$0.03 for 50 tweets).

    Args:
        query: Twitter search query
        max_results: Max tweets to return
        provenance: Optional provenance tracker

    Returns:
        List of tweet dicts.
    """
    result = run_endpoint(
        provider="apify",
        endpoint="/apidojo/tweet-scraper",
        input_data={
            "searchTerms": [query],
            "maxTweets": max_results,
            "searchMode": "live",
        },
    )

    if not result:
        return []

    items = result.get("output", result.get("items", result.get("data", [])))
    if isinstance(items, list):
        if provenance:
            for item in items:
                url = item.get("url") or item.get("tweetUrl") or ""
                if url:
                    provenance.track(
                        source_url=url,
                        source_name="monid_twitter",
                        extraction_method="api",
                    )
        logger.info("Monid: fetched %d tweets for '%s'", len(items), query)
        return items

    return []


def fetch_linkedin_posts(
    query: str,
    max_results: int = 25,
    provenance: Optional[ProvenanceTracker] = None,
) -> List[Dict]:
    """Fetch LinkedIn posts via Monid's Apify LinkedIn scraper.

    Cost: ~$0.018 per post (~$0.45 for 25 posts).

    Args:
        query: LinkedIn search query
        max_results: Max posts to return
        provenance: Optional provenance tracker

    Returns:
        List of post dicts.
    """
    result = run_endpoint(
        provider="apify",
        endpoint="/harvestapi/linkedin-post-search",
        input_data={
            "query": query,
            "maxResults": max_results,
        },
    )

    if not result:
        return []

    items = result.get("output", result.get("items", result.get("data", [])))
    if isinstance(items, list):
        if provenance:
            for item in items:
                url = item.get("url") or item.get("postUrl") or ""
                if url:
                    provenance.track(
                        source_url=url,
                        source_name="monid_linkedin",
                        extraction_method="api",
                    )
        logger.info("Monid: fetched %d LinkedIn posts for '%s'", len(items), query)
        return items

    return []
