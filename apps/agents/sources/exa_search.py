"""Exa AI semantic search for signal discovery.

Exa provides AI-powered semantic search that finds content by meaning,
not just keywords. Useful for discovering signals that keyword-based
searches miss (e.g. posts about "neobank growth" when searching for
"fintech trends").

Requires EXA_API_KEY environment variable. Gracefully skips when not set.

Usage:
    from apps.agents.sources.exa_search import search_signals, is_available
    if is_available():
        results = search_signals("AI agents replacing compliance analysts")
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

_EXA_API_KEY = os.getenv("EXA_API_KEY", "")


def is_available() -> bool:
    """Check if Exa API key is configured."""
    return bool(_EXA_API_KEY)


@dataclass
class ExaResult:
    """A search result from Exa."""

    title: str
    url: str
    text: str = ""
    author: str = ""
    published_date: Optional[str] = None
    score: float = 0.0
    source: str = "exa"
    content_hash: str = ""

    @property
    def full_text(self) -> str:
        """Title + content text."""
        if self.text:
            return f"{self.title}\n\n{self.text[:1000]}"
        return self.title


# Default queries aligned with our SIGNAL_TAXONOMY themes
DEFAULT_QUERIES = [
    "AI agents for fintech and banking compliance",
    "LATAM startup funding rounds 2026",
    "neobank payments infrastructure Latin America",
    "LLM AI developer tools open source",
    "venture capital investment thesis LATAM",
    "embedded finance BaaS platform",
    "AI safety governance regulation",
]


def search_signals(
    query: str,
    num_results: int = 10,
    days_back: int = 7,
    use_autoprompt: bool = True,
) -> List[ExaResult]:
    """Search Exa for signals matching a semantic query.

    Args:
        query: Natural language search query.
        num_results: Max results to return.
        days_back: Only return content from the last N days.
        use_autoprompt: Let Exa optimize the query for better results.

    Returns:
        List of ExaResult with title, URL, and content text.
    """
    if not is_available():
        logger.debug("EXA_API_KEY not set, skipping Exa search")
        return []

    try:
        from exa_py import Exa
    except ImportError:
        logger.debug("exa-py not installed, skipping Exa search")
        return []

    try:
        exa = Exa(api_key=_EXA_API_KEY)

        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        response = exa.search_and_contents(
            query=query,
            num_results=num_results,
            use_autoprompt=use_autoprompt,
            start_published_date=start_date,
            text={"max_characters": 1000},
        )

        results: List[ExaResult] = []
        for r in response.results:
            url = r.url or ""
            content_hash = f"exa-{hash(url) % 10**10}"

            results.append(ExaResult(
                title=r.title or "",
                url=url,
                text=(r.text or "")[:1000],
                author=r.author or "",
                published_date=r.published_date,
                score=r.score or 0.0,
                content_hash=content_hash,
            ))

        logger.info("Exa: %d results for '%s'", len(results), query[:40])
        return results

    except Exception as e:
        logger.warning("Exa search failed for '%s': %s", query[:40], e)
        return []


def search_all_themes(
    queries: Optional[List[str]] = None,
    num_per_query: int = 10,
    days_back: int = 7,
) -> List[ExaResult]:
    """Search Exa across all default theme queries.

    Args:
        queries: Custom queries. Defaults to DEFAULT_QUERIES.
        num_per_query: Results per query.
        days_back: Recency window in days.

    Returns:
        Combined list of ExaResult across all queries.
    """
    if not is_available():
        return []

    queries = queries or DEFAULT_QUERIES
    all_results: List[ExaResult] = []
    seen_urls: set = set()

    for query in queries:
        results = search_signals(
            query,
            num_results=num_per_query,
            days_back=days_back,
        )
        for r in results:
            if r.url not in seen_urls:
                all_results.append(r)
                seen_urls.add(r.url)

    logger.info(
        "Exa total: %d unique results from %d queries",
        len(all_results),
        len(queries),
    )
    return all_results
