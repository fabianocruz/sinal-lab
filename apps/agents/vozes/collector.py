"""Multi-source collector for the VOZES agent.

Fetches posts from Twitter/X, Reddit, Bluesky, RSS, YouTube, and web sources.
Each platform source is normalized into SocialPost for unified processing.
Applies spam/megathread filters and deduplicates by content_hash and text
similarity before returning.

Reuses platform-specific collection logic from social_signals/collector.py
normalizers and the shared source layer at apps/agents/sources/.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.social_signals.collector import (
    collect_from_bluesky,
    collect_from_rss,
    collect_from_twitter,
    collect_from_web_scraper,
    collect_from_youtube,
    is_on_topic,
    is_relevant_rss,
)
from apps.agents.social_signals.models import SocialPost
from apps.agents.sources.dedup import deduplicate_by_hash
from apps.agents.sources.http import create_http_client
from apps.agents.vozes.config import BLOCKED_PATTERNS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reddit megathread / self-promo filter
# ---------------------------------------------------------------------------


def filter_blocked_posts(posts: list[SocialPost]) -> list[SocialPost]:
    """Filter out Reddit megathreads, self-promo threads, and stickied posts.

    Checks post text against BLOCKED_PATTERNS from config. Case-insensitive.

    Args:
        posts: Raw SocialPost items from any platform collector.

    Returns:
        Filtered list with blocked patterns removed.
    """
    filtered = []
    removed = 0
    for p in posts:
        text_lower = (p.text or "").lower()
        if any(pattern in text_lower for pattern in BLOCKED_PATTERNS):
            removed += 1
            continue
        filtered.append(p)

    if removed:
        logger.info(
            "Blocked pattern filter: removed %d/%d posts",
            removed,
            len(posts),
        )
    return filtered


# ---------------------------------------------------------------------------
# Self-promo detection (standalone, for use in classifier too)
# ---------------------------------------------------------------------------


def is_self_promo(post: SocialPost) -> bool:
    """Detect self-promotional content.

    Checks for common self-promo phrases. Returns True if the post
    is likely self-promotional and should be filtered.

    Args:
        post: SocialPost to check.

    Returns:
        True if post matches self-promo indicators.
    """
    indicators = [
        "check out my", "i just launched", "we just launched",
        "our new product", "sign up for", "use my referral",
        "use my code", "discount code", "affiliate link",
        "weekly thread", "self-promo", "shameless plug",
        "hiring thread", "who is hiring",
    ]
    text = (post.text or "").lower()
    return any(ind in text for ind in indicators)


# ---------------------------------------------------------------------------
# Text similarity dedup
# ---------------------------------------------------------------------------


def _text_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two texts (word-level).

    Args:
        a: First text.
        b: Second text.

    Returns:
        Float 0-1 similarity score.
    """
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _get_engagement(post: SocialPost) -> int:
    """Sum engagement metrics for a post."""
    metrics = post.metrics or {}
    return (
        metrics.get("likes", 0)
        + metrics.get("replies", 0) * 2
        + metrics.get("reposts", 0) * 3
        + metrics.get("score", 0)
        + metrics.get("comments", 0) * 2
    )


def deduplicate_by_text_similarity(
    posts: list[SocialPost],
    threshold: float = 0.9,
) -> list[SocialPost]:
    """Remove near-duplicate posts by text similarity.

    When two posts have >threshold text overlap, keeps the one with more
    engagement. O(n^2) but n is bounded by max_items_per_run (~2000).

    Args:
        posts: SocialPost items (already hash-deduped).
        threshold: Jaccard similarity threshold (default 0.9).

    Returns:
        Deduplicated list.
    """
    if len(posts) <= 1:
        return posts

    # Sort by engagement descending so we keep the best version
    sorted_posts = sorted(posts, key=_get_engagement, reverse=True)
    kept: list[SocialPost] = []
    removed = 0

    for post in sorted_posts:
        is_dup = False
        text = post.text or ""
        if len(text) < 20:
            # Very short posts: skip similarity check, keep them
            kept.append(post)
            continue
        for existing in kept:
            if _text_similarity(text, existing.text or "") >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(post)
        else:
            removed += 1

    if removed:
        logger.info(
            "Text similarity dedup: removed %d/%d near-duplicates",
            removed,
            len(posts),
        )
    return kept


# ---------------------------------------------------------------------------
# Main collector orchestrator
# ---------------------------------------------------------------------------


def collect_all(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "vozes",
    run_id: str = "",
    db_session: Optional[Session] = None,
) -> List[SocialPost]:
    """Orchestrate collection from all platform sources and deduplicate.

    Routes each DataSourceConfig to the appropriate platform collector,
    applies off-topic and blocked-pattern filters, deduplicates by
    content_hash and text similarity.

    Args:
        sources: All DataSourceConfig items from VOZES_CONFIG.
        provenance: Provenance tracker for the current run.
        agent_name: Agent name for provenance records.
        run_id: Current run ID for provenance records.
        db_session: Optional SQLAlchemy session for monitored account
            collection. If None, account collection is skipped.

    Returns:
        Deduplicated, filtered list of SocialPost across all platforms.
    """
    twitter_sources = [s for s in sources if "twitter" in s.name]
    reddit_sources = [s for s in sources if "reddit" in s.name]
    bluesky_sources = [s for s in sources if "bluesky" in s.name]
    rss_sources = [s for s in sources if s.source_type == "rss"]
    scraper_sources = [s for s in sources if s.source_type == "scraper"]

    all_posts: List[SocialPost] = []

    with create_http_client() as client:
        # Twitter/X
        if twitter_sources:
            all_posts.extend(collect_from_twitter(
                twitter_sources, provenance, client, agent_name, run_id,
            ))

        # Reddit (JSON API primary, OAuth fallback)
        if reddit_sources:
            try:
                from apps.agents.sources.reddit_json import fetch_all_subreddits
                reddit_posts = fetch_all_subreddits(limit_per_sub=15)
                for rp in reddit_posts:
                    all_posts.append(SocialPost(
                        text=rp.text,
                        url=rp.permalink or rp.url,
                        platform="reddit",
                        source_name=f"reddit_r_{rp.subreddit}",
                        author_handle=rp.author,
                        author_display_name=rp.author,
                        metrics={"likes": rp.score, "comments": rp.num_comments},
                        content_hash=f"reddit-{rp.id}",
                    ))
                    provenance.track(
                        source_url=rp.permalink or rp.url,
                        source_name=f"reddit_r_{rp.subreddit}",
                        extraction_method="json_api",
                        confidence=0.6,
                        collector_agent=agent_name,
                        collector_run_id=run_id,
                    )
                logger.info("Reddit (JSON API): %d posts", len(reddit_posts))
            except Exception as e:
                logger.warning("Reddit JSON API failed, trying OAuth: %s", e)
                from apps.agents.social_signals.collector import collect_from_reddit
                all_posts.extend(collect_from_reddit(
                    reddit_sources, provenance, client, agent_name, run_id,
                ))

        # Bluesky
        if bluesky_sources:
            all_posts.extend(collect_from_bluesky(
                bluesky_sources, provenance, client, agent_name, run_id,
            ))

        # RSS (with relevance + length filter)
        if rss_sources:
            rss_posts = collect_from_rss(
                rss_sources, provenance, client, agent_name, run_id,
            )
            rss_filtered = [
                p for p in rss_posts
                if len(p.text or "") >= 50 and is_relevant_rss(p)
            ]
            logger.info(
                "RSS quality filter: %d -> %d posts",
                len(rss_posts),
                len(rss_filtered),
            )
            all_posts.extend(rss_filtered)

        # Web scrapers
        if scraper_sources:
            all_posts.extend(collect_from_web_scraper(
                scraper_sources, provenance, client, agent_name, run_id,
            ))

        # YouTube
        try:
            youtube_posts = collect_from_youtube(provenance)
            all_posts.extend(youtube_posts)
        except Exception as e:
            logger.warning("YouTube collection failed (non-fatal): %s", e)

        # LinkedIn via FreshData RapidAPI (company + profile posts)
        li_company_sources = [s for s in sources if s.source_type == "linkedin_fresh_company" and s.enabled]
        li_profile_sources = [s for s in sources if s.source_type == "linkedin_fresh_profile" and s.enabled]

        if li_company_sources or li_profile_sources:
            try:
                from apps.agents.sources.linkedin_fresh import (
                    fetch_company_posts,
                    fetch_profile_posts,
                )
                import time as _li_time

                for li_src in li_company_sources:
                    limit = li_src.params.get("limit", 5)
                    li_posts = fetch_company_posts(li_src.url, client, li_src.name, limit)
                    for lp in li_posts:
                        all_posts.append(SocialPost(
                            text=lp.text,
                            url=lp.url,
                            platform="linkedin",
                            source_name=li_src.name,
                            author_handle=lp.author_name or "",
                            author_display_name=lp.author_name or "",
                            author_followers=0,
                            metrics={
                                "likes": lp.num_likes,
                                "comments": lp.num_comments,
                                "reactions": lp.num_reactions,
                                "reposts": lp.num_reposts,
                            },
                            content_hash=lp.content_hash,
                            image_url=lp.image_url,
                        ))
                        provenance.track(
                            source_url=lp.url,
                            source_name=li_src.name,
                            extraction_method="api",
                            collector_agent=agent_name,
                            collector_run_id=run_id,
                        )
                    _li_time.sleep(2)  # rate limit between sources

                for li_src in li_profile_sources:
                    limit = li_src.params.get("limit", 5)
                    li_posts = fetch_profile_posts(li_src.url, client, li_src.name, limit)
                    for lp in li_posts:
                        all_posts.append(SocialPost(
                            text=lp.text,
                            url=lp.url,
                            platform="linkedin",
                            source_name=li_src.name,
                            author_handle=lp.author_name or "",
                            author_display_name=lp.author_name or "",
                            author_followers=0,
                            metrics={
                                "likes": lp.num_likes,
                                "comments": lp.num_comments,
                                "reactions": lp.num_reactions,
                                "reposts": lp.num_reposts,
                            },
                            content_hash=lp.content_hash,
                            image_url=lp.image_url,
                        ))
                        provenance.track(
                            source_url=lp.url,
                            source_name=li_src.name,
                            extraction_method="api",
                            collector_agent=agent_name,
                            collector_run_id=run_id,
                        )
                    _li_time.sleep(2)

                logger.info(
                    "LinkedIn (FreshData): %d company sources, %d profile sources",
                    len(li_company_sources), len(li_profile_sources),
                )
            except Exception as e:
                logger.warning("LinkedIn FreshData collection failed (non-fatal): %s", e)

        # LinkedIn via Jina Reader (monitored voices)
        try:
            from apps.agents.sources.jina_reader import fetch_url_content
            from sqlalchemy import text as sa_text

            if db_session is not None:
                li_voices = db_session.execute(
                    sa_text(
                        "SELECT handle, display_name, profile_url "
                        "FROM monitored_accounts "
                        "WHERE platform='linkedin' AND is_active=true LIMIT 10"
                    )
                ).fetchall()

                li_count = 0
                for voice in li_voices:
                    profile_url = voice[2]
                    if not profile_url:
                        continue
                    activity_url = f"{profile_url.rstrip('/')}/recent-activity/all/"
                    content = fetch_url_content(activity_url)
                    if content and len(content.text) > 100:
                        all_posts.append(SocialPost(
                            text=content.text[:500],
                            url=activity_url,
                            platform="linkedin",
                            source_name="linkedin_jina",
                            author_handle=voice[0],
                            author_display_name=voice[1],
                            content_hash=f"li-{voice[0]}-{hash(content.text[:100]) % 10**8}",
                        ))
                        li_count += 1
                        provenance.track(
                            source_url=activity_url,
                            source_name="linkedin_jina",
                            extraction_method="jina_reader",
                        )
                    import time as _time
                    _time.sleep(3)  # respect rate limits
                logger.info("LinkedIn (Jina): %d posts", li_count)
        except Exception as e:
            logger.warning("LinkedIn/Jina collection failed (non-fatal): %s", e)

    # Layer 1: Off-topic filter (politics, sports, entertainment)
    on_topic_posts = [p for p in all_posts if is_on_topic(p)]
    off_topic_count = len(all_posts) - len(on_topic_posts)
    if off_topic_count:
        logger.info(
            "Off-topic filter: removed %d/%d posts",
            off_topic_count,
            len(all_posts),
        )

    # Layer 2: Blocked patterns (megathreads, self-promo, etc.)
    filtered_posts = filter_blocked_posts(on_topic_posts)

    # Layer 3: Dedup by content_hash
    hash_deduped = deduplicate_by_hash(filtered_posts, hash_fn=lambda p: p.content_hash)

    # Layer 4: Dedup by text similarity (catches reposts/paraphrases)
    unique_posts = deduplicate_by_text_similarity(hash_deduped)

    enabled_count = len([s for s in sources if s.enabled])
    logger.info(
        "VOZES collected %d unique posts from %d enabled sources "
        "(raw: %d, off-topic: -%d, blocked: -%d, dedup: -%d)",
        len(unique_posts),
        enabled_count,
        len(all_posts),
        off_topic_count,
        len(on_topic_posts) - len(filtered_posts),
        len(hash_deduped) - len(unique_posts) + len(filtered_posts) - len(hash_deduped),
    )

    return unique_posts
