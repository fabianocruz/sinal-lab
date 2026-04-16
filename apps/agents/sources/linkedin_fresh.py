"""Fresh LinkedIn Profile Data API source (RapidAPI).

Fetches LinkedIn posts from company pages and individual profiles.
Uses the FreshData provider on RapidAPI.

Available endpoints:
    - /get-profile-posts (by linkedin_url)
    - /get-company-posts (by linkedin_url)

Requires RAPIDAPI_KEY environment variable.

Usage:
    from apps.agents.sources.linkedin_fresh import (
        fetch_profile_posts, fetch_company_posts
    )
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

RAPIDAPI_HOST = "fresh-linkedin-profile-data.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"
# FreshData API is slow (~5s per request), need generous timeout
DEFAULT_TIMEOUT = 45


@dataclass
class LinkedInFreshPost:
    """A LinkedIn post from the FreshData API."""

    text: str
    url: str
    author_name: str
    author_headline: str = ""
    author_url: str = ""
    num_likes: int = 0
    num_comments: int = 0
    num_reactions: int = 0
    num_reposts: int = 0
    posted_at: Optional[str] = None
    image_url: Optional[str] = None
    source_name: str = ""
    mentioned_companies: List[str] = field(default_factory=list)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def _get_headers() -> Optional[Dict[str, str]]:
    """Build RapidAPI headers. Returns None if key not set."""
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return None
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "Content-Type": "application/json",
    }


def _parse_post(item: dict, source_name: str) -> Optional[LinkedInFreshPost]:
    """Parse a single post from the API response."""
    text = item.get("text", "")
    url = item.get("post_url", "")
    if not text or not url:
        return None

    poster = item.get("poster") or {}
    author_name = ""
    if isinstance(poster, dict):
        first = poster.get("first", "")
        last = poster.get("last", "")
        author_name = f"{first} {last}".strip()

    # Extract mentioned companies from attributes
    companies = []
    for attr in item.get("attributes") or []:
        if isinstance(attr, dict) and attr.get("type") == "company":
            name = attr.get("name")
            if name:
                companies.append(name)

    # Extract first image
    image_url = None
    images = item.get("images") or []
    if images and isinstance(images[0], dict):
        image_url = images[0].get("url")

    return LinkedInFreshPost(
        text=text,
        url=url,
        author_name=author_name,
        author_headline=poster.get("headline", "") if isinstance(poster, dict) else "",
        author_url=item.get("poster_linkedin_url", ""),
        num_likes=item.get("num_likes", 0) or 0,
        num_comments=item.get("num_comments", 0) or 0,
        num_reactions=item.get("num_reactions", 0) or 0,
        num_reposts=item.get("num_reposts", 0) or 0,
        posted_at=item.get("posted"),
        image_url=image_url,
        source_name=source_name,
        mentioned_companies=companies,
    )


def fetch_profile_posts(
    linkedin_url: str,
    client: httpx.Client,
    source_name: str = "linkedin_profile",
    limit: int = 10,
) -> List[LinkedInFreshPost]:
    """Fetch recent posts from a LinkedIn profile.

    Args:
        linkedin_url: Full LinkedIn profile URL (e.g. https://linkedin.com/in/davidvelez/)
        client: httpx.Client instance.
        source_name: Name for provenance tracking.
        limit: Max posts to fetch.

    Returns:
        List of LinkedInFreshPost. Empty on error or missing key.
    """
    headers = _get_headers()
    if not headers:
        logger.warning("RAPIDAPI_KEY not set, skipping LinkedIn profile posts")
        return []

    try:
        r = client.get(
            f"{BASE_URL}/get-profile-posts",
            headers=headers,
            params={"linkedin_url": linkedin_url, "limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("LinkedIn profile posts error for %s: %s", linkedin_url, exc)
        return []

    data = r.json()
    if not data.get("success", True) and data.get("message"):
        logger.warning("LinkedIn API error: %s", data["message"])
        return []

    items = data.get("data") or []
    posts = []
    for item in items:
        post = _parse_post(item, source_name)
        if post:
            posts.append(post)

    logger.info("LinkedIn profile %s: %d posts", linkedin_url.split("/")[-2], len(posts))
    return posts


def fetch_company_posts(
    linkedin_url: str,
    client: httpx.Client,
    source_name: str = "linkedin_company",
    limit: int = 10,
) -> List[LinkedInFreshPost]:
    """Fetch recent posts from a LinkedIn company page.

    Args:
        linkedin_url: Full LinkedIn company URL (e.g. https://linkedin.com/company/nubank/)
        client: httpx.Client instance.
        source_name: Name for provenance tracking.
        limit: Max posts to fetch.

    Returns:
        List of LinkedInFreshPost. Empty on error or missing key.
    """
    headers = _get_headers()
    if not headers:
        logger.warning("RAPIDAPI_KEY not set, skipping LinkedIn company posts")
        return []

    try:
        r = client.get(
            f"{BASE_URL}/get-company-posts",
            headers=headers,
            params={"linkedin_url": linkedin_url, "limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("LinkedIn company posts error for %s: %s", linkedin_url, exc)
        return []

    data = r.json()
    if not data.get("success", True) and data.get("message"):
        logger.warning("LinkedIn API error: %s", data["message"])
        return []

    items = data.get("data") or []
    posts = []
    for item in items:
        post = _parse_post(item, source_name)
        if post:
            posts.append(post)

    company_name = linkedin_url.rstrip("/").split("/")[-1]
    logger.info("LinkedIn company %s: %d posts", company_name, len(posts))
    return posts
