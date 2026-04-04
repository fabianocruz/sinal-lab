"""Async multi-source collector for the Social Signals Intelligence agent.

Wraps the existing sync per-platform collectors using asyncio.to_thread()
so they run concurrently without rewriting their internals. Each platform
group has a 30-second timeout; failures are logged and skipped (graceful
degradation).

Usage:
    posts = await async_collect_all(sources, provenance, agent_name, run_id)
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.social_signals.models import SocialPost
from apps.agents.sources.dedup import deduplicate_by_hash
from apps.agents.sources.http import create_http_client

logger = logging.getLogger(__name__)

# Default timeout per source group (seconds)
SOURCE_TIMEOUT_SECONDS = 30.0


async def _run_with_timeout(
    label: str,
    coro: Any,
    timeout: float = SOURCE_TIMEOUT_SECONDS,
) -> Tuple[str, List[SocialPost]]:
    """Run a coroutine with a timeout and graceful error handling.

    Args:
        label: Human-readable label for logging (e.g., "twitter").
        coro: The awaitable to execute.
        timeout: Maximum seconds to wait before cancelling.

    Returns:
        Tuple of (label, list of SocialPost). Empty list on failure.
    """
    try:
        posts = await asyncio.wait_for(coro, timeout=timeout)
        return label, posts
    except asyncio.TimeoutError:
        logger.warning(
            "Async collector timed out after %.1fs: %s", timeout, label,
        )
        return label, []
    except Exception as exc:
        logger.warning(
            "Async collector failed for %s (non-fatal): %s", label, exc,
        )
        return label, []


def _collect_twitter_sync(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[SocialPost]:
    """Sync wrapper: collect from Twitter sources using a fresh HTTP client."""
    from apps.agents.social_signals.collector import collect_from_twitter

    with create_http_client() as client:
        return collect_from_twitter(sources, provenance, client, agent_name, run_id)


def _collect_reddit_sync(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[SocialPost]:
    """Sync wrapper: collect from Reddit sources using a fresh HTTP client."""
    from apps.agents.social_signals.collector import collect_from_reddit

    with create_http_client() as client:
        return collect_from_reddit(sources, provenance, client, agent_name, run_id)


def _collect_bluesky_sync(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[SocialPost]:
    """Sync wrapper: collect from Bluesky sources using a fresh HTTP client."""
    from apps.agents.social_signals.collector import collect_from_bluesky

    with create_http_client() as client:
        return collect_from_bluesky(sources, provenance, client, agent_name, run_id)


def _collect_rss_sync(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[SocialPost]:
    """Sync wrapper: collect from RSS sources using a fresh HTTP client."""
    from apps.agents.social_signals.collector import collect_from_rss

    with create_http_client() as client:
        return collect_from_rss(sources, provenance, client, agent_name, run_id)


def _collect_scraper_sync(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[SocialPost]:
    """Sync wrapper: collect from web scraper sources using a fresh HTTP client."""
    from apps.agents.social_signals.collector import collect_from_web_scraper

    with create_http_client() as client:
        return collect_from_web_scraper(sources, provenance, client, agent_name, run_id)


def _collect_polymarket_sync(
    provenance: ProvenanceTracker,
) -> List[SocialPost]:
    """Sync wrapper: collect from Polymarket prediction markets."""
    from apps.agents.sources.polymarket import collect_polymarket_signals

    pm_markets = collect_polymarket_signals(provenance, limit=15)
    posts: List[SocialPost] = []
    for m in pm_markets:
        pct = f"{m.outcome_yes * 100:.0f}%"
        posts.append(SocialPost(
            text=f"[Polymarket {pct} YES] {m.title}. {m.description[:200]}",
            url=m.url,
            platform="polymarket",
            source_name="polymarket",
            metrics={
                "volume_usd": m.volume_usd,
                "liquidity_usd": m.liquidity_usd,
                "outcome_yes": m.outcome_yes,
            },
            content_hash=m.content_hash,
        ))
    return posts


def _collect_sc_research_sync(
    provenance: ProvenanceTracker,
) -> List[SocialPost]:
    """Sync wrapper: collect from sc-research CLI tool."""
    from apps.agents.sources.sc_research import (
        collect_from_sc_research,
        is_available as sc_available,
    )

    if not sc_available():
        logger.debug("sc-research not installed, skipping")
        return []

    sc_queries = [
        "AI agents fintech banking",
        "LLM startup LATAM venture capital",
        "neobank payments infrastructure",
    ]
    sc_results = collect_from_sc_research(sc_queries, provenance, max_per_query=15)
    posts: List[SocialPost] = []
    for r in sc_results:
        posts.append(SocialPost(
            text=r.text,
            url=r.url,
            platform=r.platform,
            author_handle=r.author,
            published_at=None,
            source_name=f"sc_research_{r.platform}",
            metrics=r.metrics,
            content_hash=r.content_hash,
        ))
    return posts


def _collect_accounts_sync(
    db_session: Session,
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[SocialPost]:
    """Sync wrapper: collect from monitored accounts (requires DB)."""
    from apps.agents.social_signals.account_collector import (
        collect_from_monitored_accounts,
    )

    with create_http_client() as client:
        return collect_from_monitored_accounts(
            db_session, provenance, client, agent_name, run_id,
        )


async def async_collect_all(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "social_signals",
    run_id: str = "",
    db_session: Optional[Session] = None,
    timeout: float = SOURCE_TIMEOUT_SECONDS,
) -> List[SocialPost]:
    """Orchestrate async collection from all platform sources and deduplicate.

    Each platform group runs in a separate thread via asyncio.to_thread(),
    with asyncio.gather() for true parallelism. Each group has an independent
    timeout so a slow source does not block the others.

    Args:
        sources: All DataSourceConfig items from SOCIAL_SIGNALS_CONFIG.
        provenance: Provenance tracker for the current run.
        agent_name: Agent name for provenance records.
        run_id: Current run ID for provenance records.
        db_session: Optional SQLAlchemy session for monitored account
            collection. If None, account collection is skipped.
        timeout: Per-source timeout in seconds (default 30).

    Returns:
        Deduplicated list of SocialPost across all platforms.
    """
    start_time = time.monotonic()

    # Route sources to platform groups
    twitter_sources = [s for s in sources if "twitter" in s.name]
    reddit_sources = [s for s in sources if "reddit" in s.name]
    bluesky_sources = [s for s in sources if "bluesky" in s.name]
    rss_sources = [s for s in sources if s.source_type == "rss"]
    scraper_sources = [s for s in sources if s.source_type == "scraper"]

    # Build task list: (label, coroutine) pairs
    tasks: List[Tuple[str, Any]] = []

    if twitter_sources:
        tasks.append((
            "twitter",
            asyncio.to_thread(
                _collect_twitter_sync, twitter_sources, provenance, agent_name, run_id,
            ),
        ))

    if reddit_sources:
        tasks.append((
            "reddit",
            asyncio.to_thread(
                _collect_reddit_sync, reddit_sources, provenance, agent_name, run_id,
            ),
        ))

    if bluesky_sources:
        tasks.append((
            "bluesky",
            asyncio.to_thread(
                _collect_bluesky_sync, bluesky_sources, provenance, agent_name, run_id,
            ),
        ))

    if rss_sources:
        tasks.append((
            "rss",
            asyncio.to_thread(
                _collect_rss_sync, rss_sources, provenance, agent_name, run_id,
            ),
        ))

    if scraper_sources:
        tasks.append((
            "scraper",
            asyncio.to_thread(
                _collect_scraper_sync, scraper_sources, provenance, agent_name, run_id,
            ),
        ))

    # Polymarket (always attempted)
    tasks.append((
        "polymarket",
        asyncio.to_thread(_collect_polymarket_sync, provenance),
    ))

    # sc-research (always attempted)
    tasks.append((
        "sc_research",
        asyncio.to_thread(_collect_sc_research_sync, provenance),
    ))

    # Monitored accounts (only if DB session available)
    if db_session is not None:
        tasks.append((
            "monitored_accounts",
            asyncio.to_thread(
                _collect_accounts_sync, db_session, provenance, agent_name, run_id,
            ),
        ))

    # Execute all tasks concurrently with per-task timeouts
    results = await asyncio.gather(
        *[_run_with_timeout(label, coro, timeout=timeout) for label, coro in tasks],
        return_exceptions=False,  # _run_with_timeout handles exceptions internally
    )

    # Aggregate results and log per-source counts
    all_posts: List[SocialPost] = []
    source_counts: Dict[str, int] = {}
    for label, posts in results:
        source_counts[label] = len(posts)
        all_posts.extend(posts)

    # Deduplicate
    unique_posts = deduplicate_by_hash(all_posts, hash_fn=lambda p: p.content_hash)

    elapsed = time.monotonic() - start_time
    enabled_count = len([s for s in sources if s.enabled])
    logger.info(
        "Async collector completed in %.2fs: %d unique posts from %d enabled sources "
        "(before dedup: %d). Per-source: %s",
        elapsed,
        len(unique_posts),
        enabled_count,
        len(all_posts),
        ", ".join(f"{k}={v}" for k, v in source_counts.items()),
    )

    return unique_posts
