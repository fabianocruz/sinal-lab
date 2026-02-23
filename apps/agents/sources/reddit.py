"""Shared Reddit API source for agent collectors.

Fetches posts from subreddits via the Reddit OAuth2 API using the
client_credentials flow. Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET
environment variables.

Usage:
    from apps.agents.sources.reddit import fetch_subreddit_posts

    posts = fetch_subreddit_posts(source_config, client, "brdev")
"""

import hashlib
import html
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"
REDDIT_USER_AGENT = "Sinal.lab/0.2 (LATAM tech intelligence)"


@dataclass
class RedditPost:
    """A single Reddit post from a subreddit listing.

    Content hash is computed for cross-source deduplication:
    - Link posts (external URL): hash the external URL
    - Self posts (reddit.com URL with permalink): hash the permalink
    - Fallback: hash the URL
    """

    title: str
    url: str
    source_name: str
    subreddit: str
    score: int = 0
    num_comments: int = 0
    created_utc: Optional[datetime] = None
    selftext: Optional[str] = None
    author: Optional[str] = None
    permalink: str = ""
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            if self.permalink and "reddit.com" in self.url:
                hash_input = self.permalink
            else:
                hash_input = self.url
            self.content_hash = hashlib.md5(hash_input.encode()).hexdigest()


# Thumbnail sentinel values that Reddit uses for non-image placeholders
_THUMBNAIL_SENTINELS = {"self", "default", "nsfw", "spoiler", "image", ""}


def extract_reddit_media(
    post_data: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    """Extract image and video URLs from a Reddit post's JSON data.

    Image priority:
    1. ``preview.images[0].source.url`` (highest quality, needs html.unescape)
    2. ``thumbnail`` (lower quality, filter sentinel values)
    3. ``url`` if it points to i.redd.it or i.imgur.com

    Video priority:
    1. ``media.reddit_video.fallback_url`` (Reddit-hosted video)
    2. ``url`` if it points to v.redd.it, youtube.com, youtu.be, or vimeo.com

    Args:
        post_data: The ``data`` dict from a Reddit API listing child.

    Returns:
        (image_url, video_url) tuple. Either or both may be None.
    """
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    post_url = post_data.get("url", "")

    # --- Image extraction ---
    preview = post_data.get("preview")
    if preview:
        images = preview.get("images", [])
        if images:
            source = images[0].get("source", {})
            raw_url = source.get("url", "")
            if raw_url:
                # Reddit HTML-encodes preview URLs (e.g. &amp; → &)
                image_url = html.unescape(raw_url)

    if not image_url:
        thumbnail = post_data.get("thumbnail", "")
        if thumbnail and thumbnail not in _THUMBNAIL_SENTINELS and thumbnail.startswith("http"):
            image_url = thumbnail

    if not image_url:
        if any(host in post_url for host in ("i.redd.it", "i.imgur.com")):
            image_url = post_url

    # --- Video extraction ---
    media = post_data.get("media")
    if media:
        reddit_video = media.get("reddit_video", {})
        fallback = reddit_video.get("fallback_url")
        if fallback:
            video_url = fallback

    if not video_url:
        if "v.redd.it" in post_url:
            video_url = post_url
        elif any(host in post_url for host in ("youtube.com", "youtu.be", "vimeo.com")):
            video_url = post_url

    return image_url, video_url


def authenticate_reddit(client: httpx.Client) -> Optional[str]:
    """Authenticate with Reddit using OAuth2 client_credentials flow.

    Reads REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET from environment
    variables and exchanges them for a bearer token.

    Args:
        client: Configured httpx.Client for making the auth request.

    Returns:
        Access token string on success, None on failure.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.warning(
            "Reddit credentials not configured "
            "(REDDIT_CLIENT_ID and/or REDDIT_CLIENT_SECRET missing)"
        )
        return None

    try:
        response = client.post(
            REDDIT_AUTH_URL,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": REDDIT_USER_AGENT},
        )
        response.raise_for_status()

        data = response.json()
        token = data.get("access_token")
        if not token:
            logger.warning("Reddit auth response missing access_token key")
            return None

        return token
    except httpx.HTTPStatusError as e:
        logger.warning("Reddit auth HTTP error: %s", e)
        return None
    except Exception as e:
        logger.warning("Reddit auth unexpected error: %s", e)
        return None


def fetch_subreddit_posts(
    source: DataSourceConfig,
    client: httpx.Client,
    subreddit: str,
    sort: str = "hot",
    time_filter: str = "week",
    limit: int = 25,
) -> List[RedditPost]:
    """Fetch posts from a subreddit via the Reddit API.

    Authenticates first, then fetches the listing endpoint for the
    given subreddit with the specified sort and time filter.

    Args:
        source: DataSourceConfig for provenance tracking.
        client: Configured httpx.Client.
        subreddit: Subreddit name (e.g., "brdev").
        sort: Sort method ("hot", "new", "top", "rising").
        time_filter: Time filter for "top" sort ("hour", "day", "week",
            "month", "year", "all").
        limit: Maximum number of posts to fetch (default 25).

    Returns:
        List of RedditPost objects. Empty list on error.
    """
    if not subreddit:
        logger.warning("Empty subreddit parameter, skipping %s", source.name)
        return []

    token = authenticate_reddit(client)
    if not token:
        return []

    url = f"{REDDIT_API_BASE}/r/{subreddit}/{sort}?t={time_filter}&limit={limit}"

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": REDDIT_USER_AGENT,
    }

    try:
        response = client.get(url, headers=headers)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Reddit API error for r/%s: %s", subreddit, e
        )
        return []
    except Exception as e:
        logger.warning(
            "Reddit fetch unexpected error for r/%s: %s", subreddit, e
        )
        return []

    data = response.json()
    children = data.get("data", {}).get("children", [])

    posts: List[RedditPost] = []
    for child in children:
        post_data = child.get("data", {})

        created_utc: Optional[datetime] = None
        raw_created = post_data.get("created_utc")
        if raw_created is not None:
            try:
                created_utc = datetime.fromtimestamp(
                    float(raw_created), tz=timezone.utc
                )
            except (ValueError, TypeError, OSError):
                pass

        img, vid = extract_reddit_media(post_data)

        posts.append(RedditPost(
            title=post_data.get("title", ""),
            url=post_data.get("url", ""),
            source_name=source.name,
            subreddit=post_data.get("subreddit", subreddit),
            score=post_data.get("score", 0),
            num_comments=post_data.get("num_comments", 0),
            created_utc=created_utc,
            selftext=post_data.get("selftext") or None,
            author=post_data.get("author"),
            permalink=post_data.get("permalink", ""),
            image_url=img,
            video_url=vid,
        ))

    logger.info(
        "Fetched %d posts from r/%s via %s",
        len(posts), subreddit, source.name,
    )
    return posts
