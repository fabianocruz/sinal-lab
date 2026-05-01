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


def extract_image_from_html(html_text: str) -> Optional[str]:
    """Extract the first absolute http(s) <img src> from inline HTML.

    Reddit and many RSS-fed sources embed a preview image directly in the
    post body using <img src="..."> tags. When og:image fetching fails
    (Reddit blocks scrapers, paywalls, etc), this is a reliable fallback.

    Args:
        html_text: A blob of text that may contain HTML.

    Returns:
        First absolute image URL found, or None.
    """
    if not html_text:
        return None

    # Look for all <img src="http..."> tags (either ' or " quotes) and
    # return the first one that isn't an obvious tracking pixel or icon
    # or a host that we know returns 403 to non-Reddit referrers.
    skip_patterns = [
        "1x1", "pixel.gif", "pixel.png", "blank.gif", "spacer.gif", "tracker",
    ]
    # Hosts that block hotlinking / always 403 from non-origin requests.
    # external-preview.redd.it requires Reddit-internal cookies and rejects
    # everything else with 403 — saving those URLs leaves broken <img> tags
    # in the feed.
    skip_hosts = (
        "external-preview.redd.it",
        "preview.redd.it",
    )
    for match in re.finditer(
        r'<img[^>]+src=["\'](https?://[^"\']+)["\']',
        html_text,
        re.IGNORECASE,
    ):
        url = match.group(1)
        # Decode HTML entities (e.g. &amp; -> &) so the URL is usable.
        url = (
            url.replace("&amp;", "&")
               .replace("&quot;", '"')
               .replace("&#39;", "'")
        )
        lower = url.lower()
        if any(skip in lower for skip in skip_patterns):
            continue
        if any(host in lower for host in skip_hosts):
            continue
        return url
    return None


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
            img_url = match.group(1)
            # Skip relative URLs (browser can't resolve them in email/feed)
            if img_url.startswith("http"):
                return img_url
            return None

        # Try reversed attribute order
        match = re.search(
            r'<meta\s+[^>]*content=["\']([^"\']+)["\']\s+[^>]*property=["\']og:image["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            img_url = match.group(1)
            if img_url.startswith("http"):
                return img_url
            return None

        return None

    except Exception as exc:
        logger.debug("og:image extraction failed for %s: %s", url, exc)
        return None


def enrich_items(
    items: List["CuratedItem"],
    fetch_thumbnails: bool = True,
    session: Optional[object] = None,
) -> List["CuratedItem"]:
    """Enrich curated items with embed detection and og:image thumbnails.

    Modifies items in place and returns the same list. Embed detection
    checks both ``source_url`` and ``source_text``: Twitter posts store
    YouTube/Instagram/TikTok links inside the tweet text rather than in
    the post URL, so scanning source_text catches those embeds.

    Args:
        items: List of CuratedItem instances to enrich.
        fetch_thumbnails: If True, fetch og:image for non-embed URLs.
            Set to False in tests or when speed is critical.
        session: Optional SQLAlchemy session. When provided, the enricher
            falls back to scanning the ORIGINAL signal.text (HTML) for
            <img> tags when og:image fails — most useful for Reddit and
            RSS sources that block scrapers but embed previews inline.

    Returns:
        The same list of items, now enriched.
    """
    from apps.agents.feed_curator.curator import CuratedItem  # noqa: F811

    # Lazy load: only if a session is provided AND we'll actually need it.
    raw_texts_by_hash: dict = {}
    if session is not None:
        try:
            from packages.database.models.social_signal import SocialSignal
            hashes = [it.content_hash for it in items if it.content_hash]
            if hashes:
                rows = (
                    session.query(SocialSignal.content_hash, SocialSignal.text)
                    .filter(SocialSignal.content_hash.in_(hashes))
                    .all()
                )
                raw_texts_by_hash = {ch: txt for ch, txt in rows if txt}
        except Exception as exc:
            logger.debug("Could not load raw signal texts for enrichment: %s", exc)

    for item in items:
        # Detect embeds — check source_url first, then scan source_text for video links.
        # Twitter posts store YouTube/Instagram/TikTok links inside the tweet text,
        # so source_url (the tweet permalink) won't match embed patterns.
        embed_type, embed_url = detect_embed(item.source_url)
        if not embed_type and item.source_text:
            embed_type, embed_url = detect_embed(item.source_text)

        if embed_type:
            item.embed_type = embed_type
            item.embed_url = embed_url

            # For YouTube embeds, use the known thumbnail URL pattern
            if embed_type == "youtube":
                video_id = embed_url.split("/")[-1] if embed_url else ""
                if video_id:
                    item.thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

        # Fetch og:image for items without a thumbnail. Skip Reddit URLs:
        # their og:image is external-preview.redd.it which blocks hotlinking,
        # and the JSON API rate-limits anonymous IPs aggressively. Reddit
        # items will fall through to the source_text / signal.text scan or
        # render text-only on /feed.
        if (
            fetch_thumbnails
            and not item.thumbnail_url
            and item.source_url
            and "reddit.com" not in item.source_url
        ):
            item.thumbnail_url = extract_og_image(item.source_url)
        if not item.thumbnail_url and item.source_text:
            item.thumbnail_url = extract_image_from_html(item.source_text)
        # Last resort: pull the original (HTML-bearing) text from the matching
        # social_signals row. source_text is LLM-cleaned and usually has no
        # <img> tags; the raw signal text often does (Reddit RSS especially).
        if not item.thumbnail_url and item.content_hash in raw_texts_by_hash:
            item.thumbnail_url = extract_image_from_html(
                raw_texts_by_hash[item.content_hash]
            )

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
