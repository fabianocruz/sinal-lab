"""Shared Bluesky AT Protocol source for agent collectors.

Fetches posts from the Bluesky public search API (AT Protocol).
No authentication required -- uses the public API endpoint.

Usage:
    from apps.agents.sources.bluesky import fetch_bluesky_search

    posts = fetch_bluesky_search(source_config, client, "latam startups")
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

BLUESKY_API_BASE = "https://public.api.bsky.app"
BLUESKY_SEARCH_ENDPOINT = (
    f"{BLUESKY_API_BASE}/xrpc/app.bsky.feed.searchPosts"
)


@dataclass
class BlueskyPost:
    """A single Bluesky post from the AT Protocol search API.

    Cross-source dedup: content_hash is computed from external_url when
    present (so two posts linking to the same article share a hash),
    falling back to the bsky.app permalink URL.
    """

    text: str
    url: str
    source_name: str
    author_handle: Optional[str] = None
    author_display_name: Optional[str] = None
    external_url: Optional[str] = None
    like_count: int = 0
    reply_count: int = 0
    repost_count: int = 0
    created_at: Optional[datetime] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            hash_source = self.external_url if self.external_url else self.url
            self.content_hash = hashlib.md5(hash_source.encode()).hexdigest()


def build_post_url(handle: str, rkey: str) -> str:
    """Build a bsky.app permalink from author handle and post record key.

    Args:
        handle: Author handle (e.g., "maria.bsky.social").
        rkey: Post record key extracted from the AT URI.

    Returns:
        Full bsky.app permalink URL.
    """
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def _extract_rkey(uri: str) -> str:
    """Extract the record key (last segment) from an AT Protocol URI.

    AT URIs look like: at://did:plc:{id}/app.bsky.feed.post/{rkey}
    """
    return uri.rsplit("/", 1)[-1]


def _parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp string into a datetime.

    Returns None if the timestamp is malformed.
    """
    try:
        return datetime.fromisoformat(
            timestamp_str.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        return None


def _extract_media_urls(
    raw_post: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    """Extract image and video URLs from a Bluesky post's embed view.

    Uses the *view* embed (``raw_post["embed"]``), not the record embed,
    because the view object contains resolved CDN URLs ready for display.

    Supported embed types:
    - ``app.bsky.embed.images#view`` — first image thumbnail
    - ``app.bsky.embed.external#view`` — external link thumbnail
    - ``app.bsky.embed.video#view`` — video thumbnail + HLS playlist
    - ``app.bsky.embed.recordWithMedia#view`` — unwraps inner media embed

    Returns:
        (image_url, video_url) tuple. Either or both may be None.
    """
    embed = raw_post.get("embed")
    if not embed:
        return None, None

    embed_type = embed.get("$type", "")

    # recordWithMedia wraps another media embed — unwrap it
    if embed_type == "app.bsky.embed.recordWithMedia#view":
        embed = embed.get("media", {})
        embed_type = embed.get("$type", "")

    image_url: Optional[str] = None
    video_url: Optional[str] = None

    if embed_type == "app.bsky.embed.images#view":
        images = embed.get("images", [])
        if images:
            image_url = images[0].get("thumb") or images[0].get("fullsize")

    elif embed_type == "app.bsky.embed.external#view":
        external = embed.get("external", {})
        image_url = external.get("thumb")

    elif embed_type == "app.bsky.embed.video#view":
        image_url = embed.get("thumbnail")
        video_url = embed.get("playlist")

    return image_url, video_url


def _extract_external_url(record: Dict[str, Any]) -> Optional[str]:
    """Extract external URL from a post record's embed, if present.

    Only extracts from app.bsky.embed.external embed type.
    """
    embed = record.get("embed")
    if embed is None:
        return None

    embed_type = embed.get("$type", "")
    if embed_type != "app.bsky.embed.external":
        return None

    external = embed.get("external")
    if external is None:
        return None

    return external.get("uri")


def parse_bluesky_post(
    raw_post: Dict[str, Any],
    source_name: str,
) -> Optional[BlueskyPost]:
    """Parse a raw AT Protocol post object into a BlueskyPost.

    Returns None if required fields (uri, author, record, record.text)
    are missing.

    Args:
        raw_post: Raw post dict from the AT Protocol search API.
        source_name: Name of the data source for provenance tracking.

    Returns:
        Parsed BlueskyPost, or None if required fields are missing.
    """
    uri = raw_post.get("uri")
    author = raw_post.get("author")
    record = raw_post.get("record")

    if uri is None or author is None or record is None:
        logger.warning("Bluesky post missing required fields, skipping")
        return None

    text = record.get("text")
    if text is None:
        logger.warning("Bluesky post missing record.text, skipping")
        return None

    handle = author.get("handle", "")
    rkey = _extract_rkey(uri)
    post_url = build_post_url(handle, rkey)

    created_at = _parse_timestamp(record.get("createdAt", ""))
    external_url = _extract_external_url(record)
    image_url, video_url = _extract_media_urls(raw_post)

    return BlueskyPost(
        text=text,
        url=post_url,
        source_name=source_name,
        author_handle=author.get("handle"),
        author_display_name=author.get("displayName"),
        external_url=external_url,
        like_count=raw_post.get("likeCount", 0),
        reply_count=raw_post.get("replyCount", 0),
        repost_count=raw_post.get("repostCount", 0),
        created_at=created_at,
        image_url=image_url,
        video_url=video_url,
    )


def fetch_bluesky_search(
    source: DataSourceConfig,
    client: httpx.Client,
    query: str,
    limit: int = 25,
) -> List[BlueskyPost]:
    """Fetch Bluesky posts matching a search query via the AT Protocol API.

    Args:
        source: DataSourceConfig for provenance/naming.
        client: Configured httpx.Client.
        query: Search query string.
        limit: Maximum number of results to request (default 25).

    Returns:
        List of BlueskyPost. Empty list on error, empty query, or no results.
    """
    if not query:
        logger.warning(
            "Bluesky source %s has empty query, skipping", source.name
        )
        return []

    try:
        response = client.get(
            BLUESKY_SEARCH_ENDPOINT,
            params={"q": query, "limit": limit},
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("Bluesky API error for %s: %s", source.name, e)
        return []

    data = response.json()
    raw_posts = data.get("posts", [])

    posts: List[BlueskyPost] = []
    for raw_post in raw_posts:
        parsed = parse_bluesky_post(raw_post, source.name)
        if parsed is not None:
            posts.append(parsed)

    logger.info(
        "Fetched %d posts from Bluesky for %s (query=%r)",
        len(posts), source.name, query,
    )
    return posts
