"""YouTube Data API v3 connector -- search videos by topic.

Fetches videos from the YouTube Data API v3 using an API key.
Requires YOUTUBE_API_KEY environment variable.

Usage:
    from apps.agents.sources.youtube import fetch_youtube_videos

    videos = fetch_youtube_videos("AI fintech LATAM", max_results=25)
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass
class YouTubeVideo:
    """A single video from the YouTube Data API v3.

    Content hash is computed from the video URL (permalink) for
    cross-source deduplication.
    """

    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    subscriber_count: int = 0
    duration: str = ""
    url: str = ""
    embed_url: str = ""
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.url:
            self.url = f"https://www.youtube.com/watch?v={self.video_id}"
        if not self.embed_url:
            self.embed_url = f"https://www.youtube.com/embed/{self.video_id}"
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def _get_api_key(api_key: Optional[str] = None) -> Optional[str]:
    """Read the YOUTUBE_API_KEY from environment or parameter.

    Args:
        api_key: Explicit API key, takes precedence over env var.

    Returns:
        API key string, or None if not configured.
    """
    key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not key:
        logger.warning(
            "YouTube credentials not configured (YOUTUBE_API_KEY missing)"
        )
    return key


def _parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp from the YouTube API.

    YouTube API returns timestamps like "2026-02-15T14:30:00Z".

    Returns None if the timestamp is malformed.
    """
    try:
        return datetime.fromisoformat(
            timestamp_str.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        return None


def _select_best_thumbnail(thumbnails: Dict[str, Any]) -> Optional[str]:
    """Select the best available thumbnail URL from a thumbnails dict.

    YouTube provides thumbnails at multiple resolutions. We prefer the
    highest quality available: maxres > high > medium > default.

    Args:
        thumbnails: The "thumbnails" dict from a YouTube API snippet.

    Returns:
        URL string for the best thumbnail, or None if no thumbnails.
    """
    for quality in ("maxres", "high", "medium", "default"):
        thumb = thumbnails.get(quality)
        if thumb and thumb.get("url"):
            return thumb["url"]
    return None


def _parse_search_results(
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Parse search.list response items into partial video dicts.

    Extracts snippet data from search results. Statistics are fetched
    separately via videos.list.

    Args:
        items: The "items" list from a YouTube search.list response.

    Returns:
        List of dicts with video_id and snippet fields.
    """
    results: List[Dict[str, Any]] = []
    for item in items:
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue

        snippet = item.get("snippet", {})
        results.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_id": snippet.get("channelId", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnails": snippet.get("thumbnails", {}),
        })

    return results


def _enrich_with_statistics(
    partial_videos: List[Dict[str, Any]],
    stats_items: List[Dict[str, Any]],
) -> List[YouTubeVideo]:
    """Merge search snippet data with video statistics and content details.

    Args:
        partial_videos: Partial dicts from _parse_search_results.
        stats_items: Items from a videos.list response with statistics
            and contentDetails parts.

    Returns:
        List of fully populated YouTubeVideo dataclass instances.
    """
    stats_lookup: Dict[str, Dict[str, Any]] = {}
    for item in stats_items:
        vid_id = item.get("id", "")
        stats = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        stats_lookup[vid_id] = {
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "duration": content_details.get("duration", ""),
        }

    videos: List[YouTubeVideo] = []
    for pv in partial_videos:
        video_id = pv["video_id"]
        stats = stats_lookup.get(video_id, {})

        published_at_str = pv.get("published_at", "")
        published_at = _parse_timestamp(published_at_str) if published_at_str else None

        thumbnail_url = _select_best_thumbnail(pv.get("thumbnails", {}))

        videos.append(YouTubeVideo(
            video_id=video_id,
            title=pv["title"],
            description=pv["description"],
            channel_id=pv["channel_id"],
            channel_title=pv["channel_title"],
            published_at=published_at,
            thumbnail_url=thumbnail_url,
            view_count=stats.get("view_count", 0),
            like_count=stats.get("like_count", 0),
            comment_count=stats.get("comment_count", 0),
            duration=stats.get("duration", ""),
        ))

    return videos


def fetch_youtube_videos(
    query: str,
    max_results: int = 25,
    api_key: Optional[str] = None,
    published_after: Optional[datetime] = None,
    relevance_language: str = "pt",
    order: str = "relevance",
) -> List[YouTubeVideo]:
    """Search YouTube videos by query using Data API v3.

    Uses two API calls:
    1. search.list -- find videos matching query
    2. videos.list -- get full statistics for found videos

    Requires YOUTUBE_API_KEY env var or api_key param.
    Returns empty list if API key is not configured.

    Args:
        query: Search query string.
        max_results: Maximum number of videos to return (1-50).
        api_key: Explicit API key. Falls back to YOUTUBE_API_KEY env var.
        published_after: Only return videos published after this datetime.
        relevance_language: ISO 639-1 language code for relevance ranking.
        order: Sort order: relevance, date, rating, viewCount.

    Returns:
        List of YouTubeVideo. Empty list on error or missing credentials.
    """
    if not query:
        logger.warning("YouTube search called with empty query, skipping")
        return []

    key = _get_api_key(api_key)
    if not key:
        return []

    # Step 1: Search for videos
    search_params: Dict[str, Any] = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "maxResults": min(max_results, 50),
        "key": key,
        "relevanceLanguage": relevance_language,
        "order": order,
    }

    if published_after is not None:
        search_params["publishedAfter"] = (
            published_after.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    try:
        with httpx.Client(timeout=30.0) as client:
            search_response = client.get(
                YOUTUBE_SEARCH_URL,
                params=search_params,
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            partial_videos = _parse_search_results(
                search_data.get("items", [])
            )

            if not partial_videos:
                logger.info(
                    "YouTube search returned no results for query=%r", query
                )
                return []

            # Step 2: Batch fetch statistics
            video_ids = ",".join(pv["video_id"] for pv in partial_videos)
            stats_params: Dict[str, Any] = {
                "part": "statistics,contentDetails",
                "id": video_ids,
                "key": key,
            }

            stats_response = client.get(
                YOUTUBE_VIDEOS_URL,
                params=stats_params,
            )
            stats_response.raise_for_status()
            stats_data = stats_response.json()

            videos = _enrich_with_statistics(
                partial_videos, stats_data.get("items", [])
            )

    except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
        logger.warning("YouTube API error for query=%r: %s", query, e)
        return []
    except Exception as e:
        logger.warning(
            "YouTube fetch unexpected error for query=%r: %s", query, e
        )
        return []

    logger.info(
        "Fetched %d videos from YouTube for query=%r",
        len(videos), query,
    )
    return videos
