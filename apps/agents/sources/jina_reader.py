"""Jina Reader — convert any URL to clean text/markdown.

Uses the free Jina Reader API (r.jina.ai) to extract readable content
from any web page. No API key needed for basic usage.

Also attempts LinkedIn profile extraction with rate-limit handling.

Usage:
    from apps.agents.sources.jina_reader import fetch_url_content, fetch_linkedin_profile

    content = fetch_url_content("https://sequoiacap.com/article/...")
    profile = fetch_linkedin_profile("fabriciobloisi")
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

JINA_BASE = "https://r.jina.ai"
JINA_TIMEOUT = 20
RATE_LIMIT_DELAY = 2  # seconds between requests


@dataclass
class WebContent:
    """Extracted content from a web page."""

    url: str
    title: str
    text: str
    published_time: Optional[str] = None


@dataclass
class LinkedInProfile:
    """Basic LinkedIn profile data."""

    handle: str
    name: str
    headline: str
    summary: str
    url: str


def fetch_url_content(url: str) -> Optional[WebContent]:
    """Fetch and extract clean text from any URL via Jina Reader.

    Args:
        url: Full URL to extract content from.

    Returns:
        WebContent with title and text, or None on failure.
    """
    jina_url = f"{JINA_BASE}/{url}"

    try:
        with httpx.Client(timeout=JINA_TIMEOUT, follow_redirects=True) as client:
            r = client.get(jina_url, headers={"Accept": "text/plain"})

            if r.status_code == 429:
                logger.warning("Jina rate limited for %s", url[:50])
                return None
            r.raise_for_status()

            text = r.text
            if not text or len(text) < 50:
                return None

            # Parse title from first line
            lines = text.strip().split("\n")
            title = ""
            content_start = 0
            for i, line in enumerate(lines):
                if line.startswith("Title:"):
                    title = line.replace("Title:", "").strip()
                elif line.startswith("Markdown Content:"):
                    content_start = i + 1
                    break

            body = "\n".join(lines[content_start:]).strip()

            # Extract published time if present
            pub_time = None
            for line in lines:
                if line.startswith("Published Time:"):
                    pub_time = line.replace("Published Time:", "").strip()
                    break

            return WebContent(
                url=url,
                title=title or lines[0][:100],
                text=body[:2000],
                published_time=pub_time,
            )

    except Exception as e:
        logger.debug("Jina fetch failed for %s: %s", url[:50], e)
        return None


def fetch_multiple_urls(urls: List[str], delay: float = RATE_LIMIT_DELAY) -> List[WebContent]:
    """Fetch content from multiple URLs with rate limiting.

    Args:
        urls: List of URLs to fetch.
        delay: Seconds between requests.

    Returns:
        List of successfully fetched WebContent.
    """
    results = []
    for url in urls:
        content = fetch_url_content(url)
        if content:
            results.append(content)
        time.sleep(delay)

    logger.info("Jina Reader: %d/%d URLs fetched", len(results), len(urls))
    return results


def fetch_linkedin_profile(handle: str) -> Optional[LinkedInProfile]:
    """Fetch a LinkedIn profile via Jina Reader.

    Note: LinkedIn frequently rate-limits Jina (429). This is best-effort.

    Args:
        handle: LinkedIn handle (e.g., "fabriciobloisi").

    Returns:
        LinkedInProfile or None if blocked/failed.
    """
    url = f"https://www.linkedin.com/in/{handle}/"
    content = fetch_url_content(url)

    if not content:
        return None

    # Parse basic profile info from the extracted text
    return LinkedInProfile(
        handle=handle,
        name=content.title.split("|")[0].strip() if "|" in content.title else content.title,
        headline="",
        summary=content.text[:500],
        url=url,
    )
