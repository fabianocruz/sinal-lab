"""Shared web scraping source for agent collectors.

Fetches and extracts content from web pages, newsletter archives,
and blog post listings. Uses httpx for HTTP and html.parser for
HTML parsing (no BeautifulSoup dependency).

Usage:
    from apps.agents.sources.web_scraper import scrape_page, scrape_newsletter_archive

    text = scrape_page("https://example.com/article", client)
    posts = scrape_newsletter_archive(source_config, client)
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

# Standard browser-like headers to avoid bot detection on simple pages.
_SCRAPER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
}


# ---------------------------------------------------------------------------
# HTML text extraction using stdlib html.parser
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Minimal HTML parser that extracts visible text content.

    Strips script, style, and noscript tags. Collects text from
    all other elements into a single string.
    """

    _SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header"}

    def __init__(self) -> None:
        super().__init__()
        self._pieces: List[str] = []
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._pieces.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._pieces)


class _ArticleLinkExtractor(HTMLParser):
    """Extract article links from HTML archive/listing pages.

    Finds <a> tags within <article>, <div>, or <li> elements that look
    like post/article listings. Collects href, link text, and optional
    <time> datetime attributes.
    """

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.articles: List[Dict[str, Any]] = []
        self._current_link: Optional[Dict[str, Any]] = None
        self._in_time: bool = False
        self._last_datetime: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        attr_dict = dict(attrs)

        if tag == "a":
            href = attr_dict.get("href", "")
            if href and self._is_article_link(href):
                full_url = self._resolve_url(href)
                self._current_link = {"url": full_url, "title": ""}

        if tag == "time":
            self._in_time = True
            dt = attr_dict.get("datetime", "")
            if dt:
                self._last_datetime = dt

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_link:
            if self._current_link["title"].strip():
                self._current_link["datetime"] = self._last_datetime
                self.articles.append(self._current_link)
                self._last_datetime = None
            self._current_link = None

        if tag == "time":
            self._in_time = False

    def handle_data(self, data: str) -> None:
        if self._current_link is not None:
            self._current_link["title"] += data

    def _is_article_link(self, href: str) -> bool:
        """Heuristic: is this href likely an article/post link?"""
        # Skip anchors, javascript, mailto, and common non-article paths
        if href.startswith(("#", "javascript:", "mailto:")):
            return False
        # Common article URL patterns
        article_patterns = [
            r"/p/",          # Substack
            r"/post/",       # Ghost, various
            r"/posts/",      # Ghost
            r"/blog/",       # Blogs
            r"/article/",    # News sites
            r"/\d{4}/\d{2}", # Date-based URLs
            r"/newsletter/", # Newsletter archives
            r"/issue/",      # Newsletter issues
            r"/edition/",    # Newsletter editions
        ]
        return any(re.search(pattern, href) for pattern in article_patterns)

    def _resolve_url(self, href: str) -> str:
        """Resolve a relative URL against the base URL."""
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return f"https:{href}"
        if href.startswith("/"):
            # Extract scheme + host from base_url
            match = re.match(r"(https?://[^/]+)", self.base_url)
            if match:
                return f"{match.group(1)}{href}"
        return f"{self.base_url}/{href.lstrip('/')}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_text_from_html(html_content: str) -> str:
    """Extract visible text content from an HTML string.

    Strips script, style, nav, footer, and header tags. Returns
    clean text suitable for classification and summarization.

    Args:
        html_content: Raw HTML string.

    Returns:
        Extracted text, or empty string if parsing fails.
    """
    try:
        extractor = _TextExtractor()
        extractor.feed(html_content)
        return extractor.get_text()
    except Exception as e:
        logger.warning("HTML text extraction failed: %s", e)
        return ""


def scrape_page(url: str, client: httpx.Client) -> Optional[str]:
    """Fetch a URL and extract its text content.

    Uses browser-like headers to avoid basic bot detection.
    Returns None on any HTTP or parsing error.

    Args:
        url: The page URL to fetch.
        client: Configured httpx.Client.

    Returns:
        Extracted text content, or None on failure.
    """
    try:
        response = client.get(url, headers=_SCRAPER_HEADERS)
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("Failed to scrape %s: %s", url, e)
        return None

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        logger.warning("Non-HTML content type for %s: %s", url, content_type)
        return None

    text = extract_text_from_html(response.text)
    if not text:
        logger.warning("No text extracted from %s", url)
        return None

    return text


def _extract_article_links(
    html_content: str,
    base_url: str,
) -> List[Dict[str, Any]]:
    """Extract article links from an HTML archive/listing page.

    Args:
        html_content: Raw HTML of the archive page.
        base_url: Base URL for resolving relative links.

    Returns:
        List of dicts with keys: url, title, datetime (optional).
    """
    try:
        extractor = _ArticleLinkExtractor(base_url)
        extractor.feed(html_content)
        return extractor.articles
    except Exception as e:
        logger.warning("Article link extraction failed for %s: %s", base_url, e)
        return []


def _parse_article_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse a datetime string from an HTML time element.

    Handles ISO 8601 and common date formats.

    Args:
        dt_str: Datetime string, or None.

    Returns:
        Parsed datetime with UTC timezone, or None.
    """
    if not dt_str:
        return None

    # Try ISO 8601
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass

    # Try common date formats
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            dt = datetime.strptime(dt_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def scrape_newsletter_archive(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[Dict[str, Any]]:
    """Scrape a newsletter archive page and extract article entries.

    Fetches the archive URL from the source config, extracts article links,
    then fetches the summary text for each article (up to max_items).

    Each returned dict has keys compatible with SocialPost normalization:
    - title: str
    - url: str
    - published_at: Optional[datetime]
    - summary: Optional[str] (first 500 chars of article text)
    - source_name: str
    - content_hash: str

    Args:
        source: DataSourceConfig with url pointing to the archive page.
            params may contain:
            - max_items (int): Maximum articles to fetch (default 10).
            - fetch_content (bool): Whether to fetch individual article
              pages for summary text (default True).

    Returns:
        List of article dicts. Empty list on error.
    """
    if not source.url:
        logger.warning("Web scraper source %s has no URL, skipping", source.name)
        return []

    max_items = source.params.get("max_items", 10)
    fetch_content = source.params.get("fetch_content", True)

    # Fetch the archive/listing page
    try:
        response = client.get(source.url, headers=_SCRAPER_HEADERS)
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning(
            "Failed to fetch archive page %s (%s): %s",
            source.name, source.url, e,
        )
        return []

    # Extract article links
    articles = _extract_article_links(response.text, source.url)
    if not articles:
        logger.info("No article links found on %s (%s)", source.name, source.url)
        return []

    # Deduplicate by URL and limit
    seen_urls: set = set()
    unique_articles: List[Dict[str, Any]] = []
    for article in articles:
        url = article["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    articles = unique_articles[:max_items]

    results: List[Dict[str, Any]] = []
    for article in articles:
        title = article["title"].strip()
        url = article["url"]

        # Clean up title (remove extra whitespace)
        title = re.sub(r"\s+", " ", title)

        # Skip entries with very short or empty titles
        if len(title) < 5:
            continue

        summary: Optional[str] = None
        if fetch_content:
            page_text = scrape_page(url, client)
            if page_text:
                summary = page_text[:500]

        published_at = _parse_article_datetime(article.get("datetime"))
        content_hash = hashlib.md5(url.encode()).hexdigest()

        results.append({
            "title": title,
            "url": url,
            "published_at": published_at,
            "summary": summary,
            "source_name": source.name,
            "content_hash": content_hash,
        })

    logger.info(
        "Scraped %d articles from %s (%s)",
        len(results), source.name, source.url,
    )
    return results
