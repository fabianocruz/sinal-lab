"""Shared LinkedIn RapidAPI source for agent collectors.

Fetches LinkedIn posts and company data via the LinkedIn Data API
on RapidAPI. Requires a RAPIDAPI_KEY environment variable.

Falls back gracefully (returns []) when the key is missing, the API
returns an error, or the response is malformed.

Usage:
    from apps.agents.sources.linkedin import fetch_linkedin_posts

    posts = fetch_linkedin_posts(source_config, client, "fintech latam")
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

RAPIDAPI_HOST = "linkedin-data-api.p.rapidapi.com"


@dataclass
class LinkedInPost:
    """A single LinkedIn post from the RapidAPI search endpoint.

    Cross-source dedup: hashes external_url (shared article link) when
    present so the same article discovered via Google News, HN, *and*
    LinkedIn is recognised as one item.  Falls back to the LinkedIn
    post URL when no external link exists.
    """

    title: str
    text: str
    url: str
    source_name: str
    author_name: Optional[str] = None
    author_headline: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    published_at: Optional[datetime] = None
    external_url: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            hash_key = self.external_url if self.external_url else self.url
            self.content_hash = hashlib.md5(hash_key.encode()).hexdigest()


@dataclass
class LinkedInCompany:
    """A LinkedIn company profile from the RapidAPI search endpoint."""

    name: str
    url: str
    source_name: str
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    company_size: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def _build_headers(api_key: str) -> Dict[str, str]:
    """Build RapidAPI request headers."""
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }


def _parse_author_name(author: Dict) -> Optional[str]:
    """Extract full name from an author dict with firstName/lastName."""
    first = author.get("firstName", "")
    last = author.get("lastName", "")
    full = f"{first} {last}".strip()
    return full if full else None


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string into a timezone-aware datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def fetch_linkedin_posts(
    source: DataSourceConfig,
    client: httpx.Client,
    query: str,
    limit: int = 20,
) -> List[LinkedInPost]:
    """Fetch LinkedIn posts matching a search query via RapidAPI.

    Args:
        source: DataSourceConfig with endpoint URL and provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        query: Search keywords (e.g., "fintech latam").
        limit: Maximum number of results to request from the API.

    Returns:
        List of LinkedInPost. Empty list when the API key is missing,
        on HTTP/timeout errors, or when the response is malformed.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        logger.warning(
            "RAPIDAPI_KEY not set, skipping LinkedIn posts for %s",
            source.name,
        )
        return []

    try:
        response = client.get(
            source.url,
            headers=_build_headers(api_key),
            params={"keywords": query, "limit": limit},
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(
            "LinkedIn posts API error for %s: %s", source.name, exc
        )
        return []

    try:
        data = response.json()
    except Exception as exc:
        logger.warning(
            "LinkedIn posts JSON decode error for %s: %s", source.name, exc
        )
        return []

    raw_items = data.get("data", [])

    posts: List[LinkedInPost] = []
    for item in raw_items:
        try:
            post_url = item["url"]
        except KeyError:
            logger.debug("Skipping LinkedIn post with missing url field")
            continue

        text = item.get("text", "")
        title = text[:100]

        author = item.get("author") or {}
        author_name = _parse_author_name(author)
        author_headline = author.get("headline") or None

        article = item.get("article") or {}
        external_url = article.get("url") or None

        # Media extraction: article thumbnail, item images, video
        li_image = (
            article.get("thumbnail")
            or article.get("image")
        )
        if not li_image:
            images_list = item.get("images") or item.get("image") or []
            if isinstance(images_list, list) and images_list:
                first_img = images_list[0]
                li_image = first_img.get("url") if isinstance(first_img, dict) else first_img
            elif isinstance(images_list, str) and images_list:
                li_image = images_list

        li_video = None
        video_data = item.get("video")
        if isinstance(video_data, dict):
            li_video = video_data.get("url")
        elif isinstance(video_data, str) and video_data:
            li_video = video_data

        published_at = _parse_datetime(item.get("postedAt"))

        posts.append(
            LinkedInPost(
                title=title,
                text=text,
                url=post_url,
                source_name=source.name,
                author_name=author_name,
                author_headline=author_headline,
                like_count=item.get("totalReactionCount", 0),
                comment_count=item.get("commentsCount", 0),
                published_at=published_at,
                external_url=external_url,
                image_url=li_image or None,
                video_url=li_video or None,
            )
        )

    logger.info(
        "Fetched %d LinkedIn posts from %s", len(posts), source.name
    )
    return posts


def fetch_linkedin_companies(
    source: DataSourceConfig,
    client: httpx.Client,
    query: str,
    limit: int = 20,
) -> List[LinkedInCompany]:
    """Fetch LinkedIn company profiles matching a search query via RapidAPI.

    Args:
        source: DataSourceConfig with endpoint URL and provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        query: Search keywords (e.g., "fintech brazil").
        limit: Maximum number of results to request from the API.

    Returns:
        List of LinkedInCompany. Empty list when the API key is missing,
        on HTTP/timeout errors, or when the response is malformed.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        logger.warning(
            "RAPIDAPI_KEY not set, skipping LinkedIn companies for %s",
            source.name,
        )
        return []

    try:
        response = client.get(
            source.url,
            headers=_build_headers(api_key),
            params={"keywords": query, "limit": limit},
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(
            "LinkedIn companies API error for %s: %s", source.name, exc
        )
        return []

    try:
        data = response.json()
    except Exception as exc:
        logger.warning(
            "LinkedIn companies JSON decode error for %s: %s",
            source.name,
            exc,
        )
        return []

    raw_items = data.get("data", [])

    companies: List[LinkedInCompany] = []
    for item in raw_items:
        try:
            company_url = item["url"]
        except KeyError:
            logger.debug("Skipping LinkedIn company with missing url field")
            continue

        hq = item.get("headquarter") or {}
        city = hq.get("city", "")
        country = hq.get("country", "")
        headquarters: Optional[str] = None
        if city and country:
            headquarters = f"{city}, {country}"
        elif city:
            headquarters = city
        elif country:
            headquarters = country

        companies.append(
            LinkedInCompany(
                name=item.get("name", ""),
                url=company_url,
                source_name=source.name,
                industry=item.get("industry") or None,
                headquarters=headquarters,
                company_size=item.get("staffCount") or None,
                description=item.get("description") or None,
                website=item.get("website") or None,
            )
        )

    logger.info(
        "Fetched %d LinkedIn companies from %s",
        len(companies),
        source.name,
    )
    return companies
