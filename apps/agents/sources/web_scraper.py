"""Shared web scraping source for agent collectors.

Fetches and extracts content from web pages, newsletter archives,
and blog post listings. Uses httpx for HTTP and html.parser for
HTML parsing (no BeautifulSoup dependency).

Two listing scrapers are provided:

- ``scrape_newsletter_archive``: newsletter archives, where article URLs
  follow well-known shapes (``/p/``, ``/issue/``, ``/2026/08/`` ...).
- ``scrape_article_listing``: generic blog indexes (VC blogs, corporate
  news pages) where URLs are plain slugs at any depth. Used as the
  fallback for sources that serve HTML where an RSS feed is expected.

Usage:
    from apps.agents.sources.web_scraper import scrape_page, scrape_article_listing

    text = scrape_page("https://example.com/article", client)
    posts = scrape_newsletter_archive(source_config, client)
    posts = scrape_article_listing(source_config, client)
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

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


class _BlogLinkExtractor(HTMLParser):
    """Extract post links from a generic blog index page.

    Unlike :class:`_ArticleLinkExtractor` (which matches known newsletter
    URL shapes), this parser keeps every same-domain link whose last path
    segment looks like a post slug. That is the only signal available on
    VC blogs, where post URLs are plain slugs at the site root
    (``/why-we-invested-in-nexu/``) or under an arbitrary folder
    (``blog/why-we-invested-in-sharpi.html``).
    """

    #: Listing/taxonomy paths that are never individual posts.
    _EXCLUDED_PATH_PARTS = (
        "/tag/", "/tags/", "/category/", "/categories/", "/author/",
        "/page/", "/wp-content/", "/wp-json/", "/feed/", "/search/",
    )

    #: Anchor text shorter than this is treated as a generic CTA
    #: ("Read more", "Leia mais") and replaced by the URL slug.
    _MIN_TITLE_LENGTH = 15

    #: A <time> element further than this many tags from a post link is
    #: assumed to belong to another card and is ignored.
    _MAX_TIME_DISTANCE = 12

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.base_host = _normalize_host(urlparse(base_url).netloc)
        self._articles: List[Dict[str, Any]] = []
        self._times: List[tuple] = []  # (tag_position, datetime string)
        self._seen_urls: set = set()
        self._current: Optional[Dict[str, Any]] = None
        self._tag_position: int = 0

    @property
    def articles(self) -> List[Dict[str, Any]]:
        """Extracted posts, each with url, title and datetime."""
        return self._associate_datetimes()

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        self._tag_position += 1
        attr_dict = dict(attrs)

        if tag == "time":
            datetime_attr = (attr_dict.get("datetime") or "").strip()
            if datetime_attr:
                self._times.append((self._tag_position, datetime_attr))

        if tag == "a" and self._current is None:
            href = (attr_dict.get("href") or "").strip()
            if not href:
                return
            full_url = urljoin(self.base_url, href)
            if self._is_post_url(full_url):
                self._current = {
                    "url": full_url,
                    "title": "",
                    "position": self._tag_position,
                }

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current is None:
            return

        url = self._current["url"]
        if url not in self._seen_urls:
            self._seen_urls.add(url)
            self._articles.append({
                "url": url,
                "title": self._resolve_title(self._current["title"], url),
                "position": self._current["position"],
            })
        self._current = None

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["title"] += data

    def _associate_datetimes(self) -> List[Dict[str, Any]]:
        """Attach each <time> to its nearest post link.

        Blog cards put the date either before or after the post link, so
        proximity (in tags parsed) is the only reliable signal. Each
        <time> is consumed by at most one post.
        """
        results: List[Dict[str, Any]] = []
        used: set = set()

        for article in self._articles:
            best_index: Optional[int] = None
            best_distance = self._MAX_TIME_DISTANCE + 1

            for index, (position, _value) in enumerate(self._times):
                if index in used:
                    continue
                distance = abs(position - article["position"])
                if distance < best_distance:
                    best_distance = distance
                    best_index = index

            datetime_value: Optional[str] = None
            if best_index is not None:
                used.add(best_index)
                datetime_value = self._times[best_index][1]

            results.append({
                "url": article["url"],
                "title": article["title"],
                "datetime": datetime_value,
            })

        return results

    def _is_post_url(self, url: str) -> bool:
        """Heuristic: same-domain URL whose last segment is a post slug."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if _normalize_host(parsed.netloc) != self.base_host:
            return False

        path = parsed.path
        if not path or path == "/":
            return False
        if any(part in path.lower() for part in self._EXCLUDED_PATH_PARTS):
            return False

        slug = re.sub(r"\.(html?|php|aspx)$", "", path.rstrip("/").rsplit("/", 1)[-1])
        # Real post slugs are multi-word ("why-we-invested-in-nexu");
        # section pages are single words ("team", "portfolio").
        return slug.count("-") >= 2

    def _resolve_title(self, anchor_text: str, url: str) -> str:
        """Use the anchor text, or derive a title from the URL slug."""
        title = re.sub(r"\s+", " ", anchor_text).strip()
        if len(title) >= self._MIN_TITLE_LENGTH:
            return title

        slug = re.sub(
            r"\.(html?|php|aspx)$", "", urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        )
        derived = slug.replace("-", " ").replace("_", " ").strip()
        return derived[:1].upper() + derived[1:] if derived else title


def _normalize_host(netloc: str) -> str:
    """Lowercase a host and drop the leading ``www.`` for comparison."""
    host = netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


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
    return _scrape_listing_page(source, client, _extract_article_links)


def extract_article_listing_links(
    html_content: str,
    base_url: str,
) -> List[Dict[str, Any]]:
    """Extract post links from a generic blog index page.

    Keeps same-domain links whose last path segment looks like a post
    slug, deduplicates by URL, and derives a title from the slug when
    the anchor text is a generic CTA ("Read more").

    Args:
        html_content: Raw HTML of the listing page.
        base_url: URL the page was fetched from (used to resolve
            relative links and to scope links to the same domain).

    Returns:
        List of dicts with keys: url, title, datetime (optional).
        Empty list if parsing fails.
    """
    try:
        extractor = _BlogLinkExtractor(base_url)
        extractor.feed(html_content)
        return extractor.articles
    except Exception as e:
        logger.warning("Blog link extraction failed for %s: %s", base_url, e)
        return []


def scrape_article_listing(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[Dict[str, Any]]:
    """Scrape a blog index page and extract its posts.

    HTML fallback for sources whose "feed" URL serves a rendered page
    instead of RSS/Atom (typical of VC blogs). Returns the same dict
    shape as :func:`scrape_newsletter_archive`.

    Args:
        source: DataSourceConfig with url pointing to the blog index.
            params may contain:
            - max_items (int): Maximum posts to keep (default 10).
            - fetch_content (bool): Whether to fetch each post page for
              summary text (default True).
        client: Configured httpx.Client.

    Returns:
        List of article dicts. Empty list on error or when the page has
        no recognisable posts.
    """
    return _scrape_listing_page(source, client, extract_article_listing_links)


def _scrape_listing_page(
    source: DataSourceConfig,
    client: httpx.Client,
    link_extractor: Any,
) -> List[Dict[str, Any]]:
    """Fetch a listing page, extract links, and build article dicts.

    Shared by :func:`scrape_newsletter_archive` and
    :func:`scrape_article_listing`; they differ only in the link
    extraction heuristic.

    Args:
        source: DataSourceConfig with the listing URL and params.
        client: Configured httpx.Client.
        link_extractor: Callable (html, base_url) -> list of link dicts.

    Returns:
        List of article dicts. Empty list on any failure.
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

    articles = link_extractor(response.text, source.url)
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
        url = article["url"]
        # Clean up title (remove extra whitespace)
        title = re.sub(r"\s+", " ", article["title"].strip())

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
