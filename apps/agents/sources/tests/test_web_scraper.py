"""Tests for the shared web scraper source.

Focus: ``scrape_article_listing`` — the HTML fallback used by sources
whose "feed" URL serves a rendered blog index instead of RSS/Atom
(Canary, Maya Capital, Valor Capital, monashees).
"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.web_scraper import (
    extract_article_listing_links,
    extract_text_from_html,
    scrape_article_listing,
)

# Realistic snippet of a VC blog index: absolute + relative links, nav
# entries, a category link, a duplicated post link, and a card where the
# anchor text is a generic "Read more" (title must come from the slug).
LISTING_HTML = """
<html>
  <body>
    <nav>
      <a href="/">Home</a>
      <a href="/team">Team</a>
      <a href="https://vcfund.example/portfolio">Portfolio</a>
      <a href="/category/news/">News</a>
    </nav>
    <main>
      <article>
        <a href="https://vcfund.example/why-we-invested-in-zenpli/">
          Why we invested in Zenpli
        </a>
        <time datetime="2026-08-10">10 Aug 2026</time>
      </article>
      <article>
        <a href="blog/why-we-invested-in-sharpi.html">Read more &rarr;</a>
      </article>
      <article>
        <a href="/2026/08/fintech-x-raises-12m-series-a/">
          Fintech X raises $12M Series A led by Canary
        </a>
      </article>
      <article>
        <a href="https://vcfund.example/why-we-invested-in-zenpli/">
          Why we invested in Zenpli
        </a>
      </article>
      <a href="mailto:hi@vcfund.example">Contact us by email</a>
      <a href="#top">Back to top</a>
      <a href="https://twitter.com/vcfund/status/12345678">Follow us on Twitter</a>
    </main>
  </body>
</html>
"""


def _mock_client(
    pages: Optional[Dict[str, str]] = None,
    status_code: int = 200,
    side_effect: Optional[Exception] = None,
) -> MagicMock:
    """Build a mock httpx.Client serving canned HTML per URL."""
    pages = pages or {}
    client = MagicMock(spec=httpx.Client)

    def _get(url: str, **kwargs: Any) -> MagicMock:
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = pages.get(url, "<html><body><p>article body</p></body></html>")
        response.url = url
        response.headers = {"content-type": "text/html; charset=utf-8"}
        if status_code >= 400:
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=response
            )
        else:
            response.raise_for_status.return_value = None
        return response

    if side_effect is not None:
        client.get.side_effect = side_effect
    else:
        client.get.side_effect = _get
    return client


class TestExtractArticleListingLinks:
    """Link/title extraction from a blog index page."""

    def _links(self) -> List[Dict[str, Any]]:
        return extract_article_listing_links(LISTING_HTML, "https://vcfund.example/blog")

    def test_extracts_article_links(self) -> None:
        urls = [link["url"] for link in self._links()]

        assert "https://vcfund.example/why-we-invested-in-zenpli/" in urls
        assert "https://vcfund.example/blog/why-we-invested-in-sharpi.html" in urls
        assert "https://vcfund.example/2026/08/fintech-x-raises-12m-series-a/" in urls

    def test_uses_anchor_text_as_title(self) -> None:
        by_url = {link["url"]: link["title"] for link in self._links()}

        assert (
            by_url["https://vcfund.example/2026/08/fintech-x-raises-12m-series-a/"]
            == "Fintech X raises $12M Series A led by Canary"
        )

    def test_falls_back_to_slug_when_anchor_text_is_generic(self) -> None:
        by_url = {link["url"]: link["title"] for link in self._links()}

        assert (
            by_url["https://vcfund.example/blog/why-we-invested-in-sharpi.html"]
            == "Why we invested in sharpi"
        )

    def test_skips_navigation_and_non_article_links(self) -> None:
        urls = [link["url"] for link in self._links()]

        assert "https://vcfund.example/" not in urls
        assert "https://vcfund.example/team" not in urls
        assert "https://vcfund.example/portfolio" not in urls
        assert "https://vcfund.example/category/news/" not in urls
        assert not any(url.startswith("mailto:") for url in urls)
        assert not any("#top" in url for url in urls)

    def test_skips_external_domains(self) -> None:
        urls = [link["url"] for link in self._links()]

        assert not any("twitter.com" in url for url in urls)

    def test_deduplicates_repeated_links(self) -> None:
        urls = [link["url"] for link in self._links()]

        assert urls.count("https://vcfund.example/why-we-invested-in-zenpli/") == 1

    def test_captures_datetime_when_present(self) -> None:
        by_url = {link["url"]: link for link in self._links()}

        assert (
            by_url["https://vcfund.example/why-we-invested-in-zenpli/"]["datetime"]
            == "2026-08-10"
        )

    def test_malformed_html_does_not_raise(self) -> None:
        links = extract_article_listing_links(
            "<html><a href='/a-b-c'>unclosed", "https://vcfund.example"
        )

        assert isinstance(links, list)


class TestScrapeArticleListing:
    """End-to-end listing scrape against a mocked HTTP client."""

    def _source(self, **params: Any) -> DataSourceConfig:
        return DataSourceConfig(
            name="vcfund",
            source_type="html",
            url="https://vcfund.example/blog",
            params=params,
        )

    def test_returns_article_dicts(self) -> None:
        client = _mock_client({"https://vcfund.example/blog": LISTING_HTML})

        results = scrape_article_listing(
            self._source(fetch_content=False), client
        )

        assert len(results) == 3
        first = results[0]
        assert first["title"] == "Why we invested in Zenpli"
        assert first["url"] == "https://vcfund.example/why-we-invested-in-zenpli/"
        assert first["source_name"] == "vcfund"
        assert first["content_hash"]
        assert first["published_at"] is not None
        assert first["published_at"].year == 2026

    def test_no_url_returns_empty(self) -> None:
        source = DataSourceConfig(name="vcfund", source_type="html", url=None)
        client = _mock_client()

        assert scrape_article_listing(source, client) == []
        client.get.assert_not_called()

    def test_http_error_returns_empty(self) -> None:
        client = _mock_client(side_effect=httpx.TimeoutException("timeout"))

        assert scrape_article_listing(self._source(), client) == []

    def test_http_status_error_returns_empty(self) -> None:
        client = _mock_client(status_code=404)

        assert scrape_article_listing(self._source(), client) == []

    def test_page_without_articles_returns_empty(self) -> None:
        client = _mock_client(
            {"https://vcfund.example/blog": "<html><body><p>nothing</p></body></html>"}
        )

        assert scrape_article_listing(self._source(), client) == []

    def test_respects_max_items(self) -> None:
        client = _mock_client({"https://vcfund.example/blog": LISTING_HTML})

        results = scrape_article_listing(
            self._source(max_items=2, fetch_content=False), client
        )

        assert len(results) == 2

    def test_fetch_content_disabled_skips_article_requests(self) -> None:
        client = _mock_client({"https://vcfund.example/blog": LISTING_HTML})

        results = scrape_article_listing(
            self._source(fetch_content=False), client
        )

        assert all(r["summary"] is None for r in results)
        assert client.get.call_count == 1

    def test_fetch_content_enabled_populates_summary(self) -> None:
        client = _mock_client(
            {
                "https://vcfund.example/blog": LISTING_HTML,
                "https://vcfund.example/why-we-invested-in-zenpli/": (
                    "<html><body><p>Zenpli raised US$ 6.5M led by Maya.</p></body></html>"
                ),
            }
        )

        results = scrape_article_listing(self._source(fetch_content=True), client)

        summary = results[0]["summary"]
        assert summary is not None
        assert "Zenpli raised US$ 6.5M led by Maya." in summary
        assert client.get.call_count == 4  # listing + 3 articles


class TestExtractTextFromHtmlRegression:
    """Existing helpers must keep working (used by other agents)."""

    def test_strips_tags_and_scripts(self) -> None:
        text = extract_text_from_html(
            "<html><script>ignore()</script><p>Hello</p><p>World</p></html>"
        )

        assert "Hello" in text
        assert "World" in text
        assert "ignore()" not in text
