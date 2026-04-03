"""Shared Twitter/X API v2 source for agent collectors.

Fetches tweets from the Twitter API v2 using Bearer Token authentication.
Requires X_BEARER_TOKEN environment variable.

Usage:
    from apps.agents.sources.twitter import fetch_twitter_search

    posts = fetch_twitter_search(source_config, client, "latam startups")
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

TWITTER_API_BASE = "https://api.twitter.com/2"
TWITTER_SEARCH_ENDPOINT = f"{TWITTER_API_BASE}/tweets/search/recent"

# Shared tweet.fields, expansions, user.fields, and media.fields used by
# both search and timeline endpoints.
_TWEET_FIELDS = "created_at,public_metrics,entities"
_EXPANSIONS = "author_id,attachments.media_keys"
_USER_FIELDS = "name,username,public_metrics"
_MEDIA_FIELDS = "url,preview_image_url"


@dataclass
class TwitterPost:
    """A single tweet from the Twitter API v2.

    Content hash is computed from the tweet URL (permalink) for
    cross-source deduplication.
    """

    text: str
    url: str
    source_name: str
    author_handle: Optional[str] = None
    author_display_name: Optional[str] = None
    author_followers: int = 0
    like_count: int = 0
    reply_count: int = 0
    retweet_count: int = 0
    quote_count: int = 0
    impression_count: int = 0
    created_at: Optional[datetime] = None
    external_url: Optional[str] = None
    image_url: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def _get_bearer_token() -> Optional[str]:
    """Read the X_BEARER_TOKEN from environment variables.

    Returns:
        Bearer token string, or None if not configured.
    """
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        logger.warning(
            "Twitter credentials not configured (X_BEARER_TOKEN missing)"
        )
    return token


def _build_auth_headers(bearer_token: str) -> Dict[str, str]:
    """Build Authorization headers for Twitter API v2.

    Args:
        bearer_token: The Bearer token for authentication.

    Returns:
        Headers dict with Authorization and User-Agent.
    """
    return {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "Sinal.lab/0.2 (LATAM tech intelligence)",
    }


def _build_request_params(
    query: Optional[str] = None,
    max_results: int = 100,
) -> Dict[str, Any]:
    """Build common query parameters for Twitter API v2 endpoints.

    Args:
        query: Search query string (omitted for timeline endpoints).
        max_results: Maximum results to return.

    Returns:
        Dict of query parameters.
    """
    params: Dict[str, Any] = {
        "max_results": max_results,
        "tweet.fields": _TWEET_FIELDS,
        "expansions": _EXPANSIONS,
        "user.fields": _USER_FIELDS,
        "media.fields": _MEDIA_FIELDS,
    }
    if query is not None:
        params["query"] = query
    return params


def _parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp from the Twitter API.

    Twitter API v2 returns timestamps like "2026-02-15T14:30:00.000Z".

    Returns None if the timestamp is malformed.
    """
    try:
        return datetime.fromisoformat(
            timestamp_str.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        return None


def _build_user_lookup(includes: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build a lookup dict from includes.users keyed by user ID.

    Args:
        includes: The "includes" object from the Twitter API v2 response.

    Returns:
        Dict mapping user ID string to user data dict.
    """
    users = includes.get("users", [])
    return {user["id"]: user for user in users if "id" in user}


def _build_media_lookup(includes: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build a lookup dict from includes.media keyed by media_key.

    Args:
        includes: The "includes" object from the Twitter API v2 response.

    Returns:
        Dict mapping media_key string to media data dict.
    """
    media_list = includes.get("media", [])
    return {
        m["media_key"]: m for m in media_list if "media_key" in m
    }


def _extract_external_url(tweet_data: Dict[str, Any]) -> Optional[str]:
    """Extract the first external URL from a tweet's entities.urls.

    Filters out Twitter's own URLs (t.co links that resolve to
    twitter.com/x.com) and returns the first expanded_url that
    points to an external site.

    Args:
        tweet_data: A single tweet object from the API response.

    Returns:
        The first external expanded_url, or None.
    """
    entities = tweet_data.get("entities", {})
    urls = entities.get("urls", [])

    for url_entity in urls:
        expanded = url_entity.get("expanded_url", "")
        # Skip Twitter/X internal links
        if expanded and not any(
            host in expanded
            for host in ("twitter.com", "x.com", "t.co")
        ):
            return expanded

    return None


def _extract_image_url(
    tweet_data: Dict[str, Any],
    media_lookup: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    """Extract the first image URL from a tweet's media attachments.

    Uses the media_keys from attachments and resolves them against the
    includes.media lookup. Prefers ``url`` over ``preview_image_url``.

    Args:
        tweet_data: A single tweet object from the API response.
        media_lookup: Dict mapping media_key to media data.

    Returns:
        Image URL string, or None if no image attachment found.
    """
    attachments = tweet_data.get("attachments", {})
    media_keys = attachments.get("media_keys", [])

    for key in media_keys:
        media = media_lookup.get(key, {})
        image = media.get("url") or media.get("preview_image_url")
        if image:
            return image

    return None


def _parse_tweets(
    data: Dict[str, Any],
    source_name: str,
) -> List[TwitterPost]:
    """Parse a Twitter API v2 response into a list of TwitterPost objects.

    Merges tweet data with includes.users and includes.media.

    Args:
        data: Full JSON response from the Twitter API v2.
        source_name: Name of the data source for provenance tracking.

    Returns:
        List of parsed TwitterPost objects.
    """
    tweets = data.get("data", [])
    if not tweets:
        return []

    includes = data.get("includes", {})
    user_lookup = _build_user_lookup(includes)
    media_lookup = _build_media_lookup(includes)

    posts: List[TwitterPost] = []
    for tweet in tweets:
        tweet_id = tweet.get("id", "")
        text = tweet.get("text", "")
        author_id = tweet.get("author_id", "")

        # Resolve author from includes
        author = user_lookup.get(author_id, {})
        author_handle = author.get("username")
        author_display_name = author.get("name")
        author_public_metrics = author.get("public_metrics", {})
        author_followers = author_public_metrics.get("followers_count", 0)

        # Tweet engagement metrics
        public_metrics = tweet.get("public_metrics", {})
        like_count = public_metrics.get("like_count", 0)
        reply_count = public_metrics.get("reply_count", 0)
        retweet_count = public_metrics.get("retweet_count", 0)
        quote_count = public_metrics.get("quote_count", 0)
        impression_count = public_metrics.get("impression_count", 0)

        # Timestamp
        created_at_str = tweet.get("created_at", "")
        created_at = _parse_timestamp(created_at_str) if created_at_str else None

        # Build permalink
        handle_for_url = author_handle or author_id
        url = f"https://x.com/{handle_for_url}/status/{tweet_id}"

        # External URL and image
        external_url = _extract_external_url(tweet)
        image_url = _extract_image_url(tweet, media_lookup)

        posts.append(TwitterPost(
            text=text,
            url=url,
            source_name=source_name,
            author_handle=author_handle,
            author_display_name=author_display_name,
            author_followers=author_followers,
            like_count=like_count,
            reply_count=reply_count,
            retweet_count=retweet_count,
            quote_count=quote_count,
            impression_count=impression_count,
            created_at=created_at,
            external_url=external_url,
            image_url=image_url,
        ))

    return posts


def fetch_twitter_search(
    source: DataSourceConfig,
    client: httpx.Client,
    query: str,
    max_results: int = 100,
) -> List[TwitterPost]:
    """Fetch tweets matching a search query via Twitter API v2.

    Uses the recent search endpoint which covers the last 7 days of tweets.

    Args:
        source: DataSourceConfig for provenance/naming.
        client: Configured httpx.Client.
        query: Search query string (Twitter search operators supported).
        max_results: Maximum results to return (10-100, default 100).

    Returns:
        List of TwitterPost. Empty list on error, empty query, or no results.
    """
    if not query:
        logger.warning(
            "Twitter source %s has empty query, skipping", source.name
        )
        return []

    bearer_token = _get_bearer_token()
    if not bearer_token:
        return []

    headers = _build_auth_headers(bearer_token)
    params = _build_request_params(query=query, max_results=max_results)

    try:
        response = client.get(
            TWITTER_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
        )
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
        logger.warning("Twitter API error for %s: %s", source.name, e)
        return []
    except Exception as e:
        logger.warning(
            "Twitter fetch unexpected error for %s: %s", source.name, e
        )
        return []

    data = response.json()
    posts = _parse_tweets(data, source.name)

    logger.info(
        "Fetched %d tweets from Twitter for %s (query=%r)",
        len(posts), source.name, query,
    )
    return posts


def fetch_twitter_user_timeline(
    source: DataSourceConfig,
    client: httpx.Client,
    user_id: str,
    max_results: int = 10,
) -> List[TwitterPost]:
    """Fetch recent tweets from a specific user's timeline via Twitter API v2.

    Args:
        source: DataSourceConfig for provenance/naming.
        client: Configured httpx.Client.
        user_id: Twitter user ID (numeric string).
        max_results: Maximum results to return (5-100, default 10).

    Returns:
        List of TwitterPost. Empty list on error, empty user_id, or no results.
    """
    if not user_id:
        logger.warning(
            "Twitter source %s has empty user_id, skipping", source.name
        )
        return []

    bearer_token = _get_bearer_token()
    if not bearer_token:
        return []

    headers = _build_auth_headers(bearer_token)
    params = _build_request_params(max_results=max_results)
    url = f"{TWITTER_API_BASE}/users/{user_id}/tweets"

    try:
        response = client.get(
            url,
            headers=headers,
            params=params,
        )
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
        logger.warning(
            "Twitter API error for %s (user %s): %s", source.name, user_id, e
        )
        return []
    except Exception as e:
        logger.warning(
            "Twitter fetch unexpected error for %s (user %s): %s",
            source.name, user_id, e,
        )
        return []

    data = response.json()
    posts = _parse_tweets(data, source.name)

    logger.info(
        "Fetched %d tweets from user %s for %s",
        len(posts), user_id, source.name,
    )
    return posts
