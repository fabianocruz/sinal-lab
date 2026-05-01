"""LLM-powered curation logic for the Feed Curator agent.

Loads recent social signals from the database, pre-filters spam,
batches to the LLM for editorial selection, and returns curated items
with editorial headlines and context.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from apps.agents.base.llm import LLMClient, LLMConfig, strip_code_fences
from apps.agents.feed_curator.config import (
    CURATOR_SYSTEM_PROMPT,
    CURATOR_USER_PROMPT_TEMPLATE,
    FEED_CURATOR_CONFIG,
)

logger = logging.getLogger(__name__)


@dataclass
class CuratedItem:
    """A single curated feed item produced by the LLM.

    Attributes:
        content_hash: FK reference to the source social_signals row.
        editorial_headline: Short headline in pt-BR (max 80 chars).
        editorial_context: 1-2 sentence explanation of why this matters.
        relevance_score: 0-100 relevance rating from the LLM.
        category: One of AI, Fintech, Banking, Startup.
        source_platform: Platform the original signal came from.
        source_url: URL of the original post.
        source_author: Author handle from the original signal.
        source_text: Truncated original text for display.
        thumbnail_url: og:image or embed thumbnail (populated by enricher).
        embed_type: youtube, instagram, tiktok, or None.
        embed_url: Embeddable URL (populated by enricher).
    """

    content_hash: str
    editorial_headline: str
    editorial_context: str
    relevance_score: int
    category: str
    source_platform: str = ""
    source_url: str = ""
    source_author: str = ""
    source_text: str = ""
    thumbnail_url: Optional[str] = None
    embed_type: Optional[str] = None
    embed_url: Optional[str] = None


def load_recent_signals(
    session: Any,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Load the most recent social signals that have not been curated yet.

    Filters out obvious noise so the LLM sees mostly editorial-grade content:
    - already-curated content_hashes (we'd just re-curate them)
    - login/signup wall pages scraped from LinkedIn
    - Reddit AutoModerator / generic daily-discussion threads
    - empty or very short bodies
    - signals without a published_at (usually scrape errors)

    Args:
        session: SQLAlchemy session.
        limit: Maximum number of signals to load.

    Returns:
        List of dicts with signal data for LLM input.
    """
    from sqlalchemy import desc, func

    from packages.database.models.curated_feed_item import CuratedFeedItem
    from packages.database.models.social_signal import SocialSignal

    # Patterns we have seen produce useless LLM input. Each match (case-insensitive)
    # in the first ~200 chars of `text` rejects the signal.
    NOISE_PATTERNS = [
        "sign in | linkedin",
        "agree & join linkedin",
        "discover new opportunities",
        "daily crypto discussion",
        "daily discussion thread",
        "weekly thread",
        "i will not promote",
        "[deleted]",
        "[removed]",
    ]
    NOISE_AUTHORS = [
        "automoderator",
    ]
    MIN_TEXT_LENGTH = 80

    # We split the input batch into two pools and merge them so a single
    # noisy news cycle on Reddit/HN doesn't push every Twitter/blog signal
    # off the LLM's input. Reddit/HN posts often lack hotlinkable thumbnails,
    # so capping their share keeps the visual quality of /feed reasonable.
    LOW_MEDIA_HOSTS = ("reddit.com", "news.ycombinator.com")
    LOW_MEDIA_FRACTION = 0.30  # at most 30% of the batch from these hosts

    already_curated = session.query(CuratedFeedItem.content_hash).subquery()

    def _base_query():
        q = (
            session.query(SocialSignal)
            .filter(SocialSignal.theme.isnot(None))
            .filter(~SocialSignal.content_hash.in_(already_curated))
            .filter(SocialSignal.published_at.isnot(None))
            .filter(func.char_length(SocialSignal.text) >= MIN_TEXT_LENGTH)
        )
        for pattern in NOISE_PATTERNS:
            q = q.filter(~func.lower(SocialSignal.text).contains(pattern))
        for author in NOISE_AUTHORS:
            q = q.filter(func.lower(SocialSignal.author_handle) != author)
        return q

    # Build two filters: one matches low-media hosts (URL contains any host),
    # the other excludes them. SQLAlchemy or_/and_ on a list of LIKE clauses.
    from sqlalchemy import or_

    low_media_filter = or_(*[
        SocialSignal.post_url.ilike(f"%{host}%") for host in LOW_MEDIA_HOSTS
    ])

    low_media_cap = max(1, int(limit * LOW_MEDIA_FRACTION))
    rich_media_target = limit - low_media_cap

    rich_rows = (
        _base_query()
        .filter(~low_media_filter)
        .order_by(desc(SocialSignal.published_at))
        .limit(rich_media_target)
        .all()
    )
    low_rows = (
        _base_query()
        .filter(low_media_filter)
        .order_by(desc(SocialSignal.published_at))
        .limit(low_media_cap)
        .all()
    )

    # Merge while keeping recency: combined sort by published_at desc.
    rows = sorted(
        list(rich_rows) + list(low_rows),
        key=lambda r: r.published_at,
        reverse=True,
    )

    logger.info(
        "Loaded %d signals (rich=%d, low_media=%d, cap=%d)",
        len(rows), len(rich_rows), len(low_rows), low_media_cap,
    )

    signals = []
    for row in rows:
        signals.append({
            "content_hash": row.content_hash,
            "platform": row.platform,
            "author_handle": row.author_handle or "",
            "text": (row.text or "")[:300],
            "post_url": row.post_url,
            "theme": row.theme or "",
            "sub_theme": row.sub_theme or "",
            "published_at": row.published_at.isoformat() if row.published_at else "",
            "sentiment": row.sentiment,
            "authority_score": row.authority_score,
        })

    return signals


def pre_filter_spam(
    signals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove obvious spam signals before sending to LLM.

    Uses keyword matching against the skip_keywords list in config.
    This reduces token usage by filtering garbage before the LLM call.

    Args:
        signals: Raw signal dicts from DB.

    Returns:
        Filtered list with spam removed.
    """
    skip_keywords = FEED_CURATOR_CONFIG.skip_keywords
    filtered = []

    for signal in signals:
        text_lower = signal.get("text", "").lower()
        is_spam = any(kw in text_lower for kw in skip_keywords)
        if not is_spam:
            filtered.append(signal)

    removed = len(signals) - len(filtered)
    if removed:
        logger.info("Pre-filter removed %d spam signals", removed)

    return filtered


def curate_via_llm(
    signals: List[Dict[str, Any]],
    output_limit: int = 20,
    llm_client: Optional[LLMClient] = None,
) -> List[CuratedItem]:
    """Send signals to the LLM for editorial curation.

    Args:
        signals: Pre-filtered signal dicts.
        output_limit: Number of items to request from LLM.
        llm_client: LLMClient instance (created if not provided).

    Returns:
        List of CuratedItem instances sorted by relevance_score desc.
        Returns empty list if LLM is unavailable.
    """
    if not signals:
        logger.warning("No signals to curate")
        return []

    client = llm_client or LLMClient(LLMConfig(
        max_tokens=4096,
        temperature=0.3,
    ))

    if not client.is_available:
        logger.warning("LLM not available, returning empty curation")
        return []

    # Build the prompt with signal data
    signals_json = json.dumps(signals, ensure_ascii=False, indent=2)
    user_prompt = CURATOR_USER_PROMPT_TEMPLATE.format(
        limit=output_limit,
        signals_json=signals_json,
    )

    logger.info(
        "Sending %d signals to LLM for curation (requesting top %d)",
        len(signals),
        output_limit,
    )

    raw_response = client.generate(
        user_prompt=user_prompt,
        system_prompt=CURATOR_SYSTEM_PROMPT,
        max_tokens=4096,
        temperature=0.3,
    )

    if not raw_response:
        logger.warning("LLM returned empty response")
        return []

    return _parse_llm_response(raw_response, signals)


def _parse_llm_response(
    raw_response: str,
    source_signals: List[Dict[str, Any]],
) -> List[CuratedItem]:
    """Parse LLM JSON response into CuratedItem instances.

    Validates each item and enriches with source signal metadata.
    Invalid items are logged and skipped.

    Args:
        raw_response: Raw LLM output (expected: JSON array).
        source_signals: Original signals for cross-referencing.

    Returns:
        List of valid CuratedItem instances.
    """
    cleaned = strip_code_fences(raw_response)

    # Try parsing as JSON array first, then JSON lines, then extract array from text
    items_data = None
    try:
        items_data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try JSON lines (one object per line)
        try:
            jsonl_items = [json.loads(line) for line in cleaned.strip().split("\n") if line.strip().startswith("{")]
            if jsonl_items:
                items_data = jsonl_items
        except json.JSONDecodeError:
            pass

    if items_data is None:
        # Try to extract JSON array from mixed text
        import re
        array_match = re.search(r'\[[\s\S]*\]', cleaned)
        if array_match:
            try:
                items_data = json.loads(array_match.group())
            except json.JSONDecodeError:
                pass

    if items_data is None:
        logger.error("Failed to parse LLM curation response from any format")
        return []

    if not isinstance(items_data, list):
        items_data = [items_data]

    # Build lookup for source signal metadata
    signal_lookup: Dict[str, Dict[str, Any]] = {
        s["content_hash"]: s for s in source_signals
    }

    valid_categories = set(FEED_CURATOR_CONFIG.valid_categories)
    max_headline = FEED_CURATOR_CONFIG.max_headline_length
    curated: List[CuratedItem] = []

    for i, item in enumerate(items_data):
        if not isinstance(item, dict):
            logger.warning("Skipping non-dict item at index %d", i)
            continue

        content_hash = item.get("content_hash", "")
        headline = item.get("editorial_headline", "")
        context = item.get("editorial_context", "")
        score = item.get("relevance_score", 0)
        category = item.get("category", "")

        # Validate required fields
        if not content_hash or not headline:
            logger.warning("Skipping item %d: missing content_hash or headline", i)
            continue

        # Validate category
        if category not in valid_categories:
            category = "AI"  # fallback

        # Truncate headline if needed
        if len(headline) > max_headline:
            headline = headline[:max_headline - 3] + "..."

        # Clamp relevance score
        score = max(0, min(100, int(score)))

        # Enrich with source signal data
        source = signal_lookup.get(content_hash, {})

        curated.append(CuratedItem(
            content_hash=content_hash,
            editorial_headline=headline,
            editorial_context=context,
            relevance_score=score,
            category=category,
            source_platform=source.get("platform", ""),
            source_url=source.get("post_url", ""),
            source_author=source.get("author_handle", ""),
            source_text=source.get("text", "")[:200],
        ))

    # Sort by relevance_score descending
    curated.sort(key=lambda c: c.relevance_score, reverse=True)

    logger.info(
        "LLM curation produced %d valid items (from %d raw)",
        len(curated),
        len(items_data),
    )

    return curated
