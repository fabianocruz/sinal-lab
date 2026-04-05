"""Enricher module for the Feed Curator agent.

Extracts og:image thumbnails from URLs and detects YouTube, Instagram,
and TikTok embeds. Enrichment is best-effort: failures are logged
and the item proceeds without thumbnail/embed data.
"""

import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Regex patterns for embed detection
_YOUTUBE_PATTERNS = [
    re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})"),
    re.compile(r"youtube\.com/embed/([\w-]{11})"),
]

_INSTAGRAM_PATTERN = re.compile(
    r"instagram\.com/(?:p|reel)/([\w-]+)"
)

_TIKTOK_PATTERN = re.compile(
    r"tiktok\.com/@[\w.]+/video/(\d+)"
)


def detect_embed(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Detect if a URL is an embeddable video/post.

    Args:
        url: The source URL to check.

    Returns:
        Tuple of (embed_type, embed_url) or (None, None).
        embed_type is one of: "youtube", "instagram", "tiktok".
    """
    if not url:
        return None, None

    # YouTube
    for pattern in _YOUTUBE_PATTERNS:
        match = pattern.search(url)
        if match:
            video_id = match.group(1)
            return "youtube", f"https://www.youtube.com/embed/{video_id}"

    # Instagram
    match = _INSTAGRAM_PATTERN.search(url)
    if match:
        post_id = match.group(1)
        return "instagram", f"https://www.instagram.com/p/{post_id}/embed"

    # TikTok
    match = _TIKTOK_PATTERN.search(url)
    if match:
        video_id = match.group(1)
        return "tiktok", f"https://www.tiktok.com/embed/v2/{video_id}"

    return None, None


def extract_og_image(url: str, timeout: float = 5.0) -> Optional[str]:
    """Fetch a URL and extract the og:image meta tag.

    Uses httpx for the HTTP request. Returns None on any failure
    (timeout, non-200, missing tag, etc.).

    Args:
        url: Page URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        og:image URL string, or None.
    """
    if not url:
        return None

    try:
        import httpx
    except ImportError:
        logger.debug("httpx not available, skipping og:image extraction")
        return None

    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "SinalBot/1.0 (https://sinal.tech)"},
        )
        if response.status_code != 200:
            return None

        # Parse og:image from HTML (lightweight regex, no lxml dependency)
        html = response.text[:50000]  # Only scan first 50KB
        match = re.search(
            r'<meta\s+[^>]*property=["\']og:image["\']\s+[^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        # Try reversed attribute order
        match = re.search(
            r'<meta\s+[^>]*content=["\']([^"\']+)["\']\s+[^>]*property=["\']og:image["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        return None

    except Exception as exc:
        logger.debug("og:image extraction failed for %s: %s", url, exc)
        return None


def enrich_items(
    items: List["CuratedItem"],
    fetch_thumbnails: bool = True,
) -> List["CuratedItem"]:
    """Enrich curated items with embed detection and og:image thumbnails.

    Modifies items in place and returns the same list.

    Args:
        items: List of CuratedItem instances to enrich.
        fetch_thumbnails: If True, fetch og:image for non-embed URLs.
            Set to False in tests or when speed is critical.

    Returns:
        The same list of items, now enriched.
    """
    from apps.agents.feed_curator.curator import CuratedItem  # noqa: F811

    for item in items:
        # Detect embeds
        embed_type, embed_url = detect_embed(item.source_url)
        if embed_type:
            item.embed_type = embed_type
            item.embed_url = embed_url

            # For YouTube embeds, use the known thumbnail URL pattern
            if embed_type == "youtube":
                # Extract video ID from embed URL
                video_id = embed_url.split("/")[-1] if embed_url else ""
                if video_id:
                    item.thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

        # Fetch og:image for items without a thumbnail
        if fetch_thumbnails and not item.thumbnail_url and item.source_url:
            item.thumbnail_url = extract_og_image(item.source_url)

    enriched_count = sum(
        1 for item in items
        if item.thumbnail_url or item.embed_type
    )
    logger.info(
        "Enriched %d/%d items with thumbnails or embeds",
        enriched_count,
        len(items),
    )

    return items
