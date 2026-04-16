"""Authority scoring and top voice extraction for VOZES.

Computes per-post authority scores based on follower count, platform weight,
and engagement metrics. Extracts top voices with diversity capping to prevent
a single prolific author from dominating the rankings.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List

from apps.agents.social_signals.models import ProcessedSignal, SocialPost
from apps.agents.vozes.config import BOT_PATTERNS, MIN_AUTHORITY_SCORE

logger = logging.getLogger(__name__)

# Platform authority weights — LinkedIn and Twitter carry more weight
# because authors are identity-verified or have established followings.
_PLATFORM_WEIGHTS: Dict[str, float] = {
    "twitter": 0.15,
    "linkedin": 0.20,
    "bluesky": 0.10,
    "reddit": 0.05,
    "rss": 0.10,
    "youtube": 0.12,
    "web": 0.05,
}


def _is_bot(handle: str) -> bool:
    """Check if a handle belongs to a known bot.

    Args:
        handle: Author handle to check.

    Returns:
        True if the handle matches any known bot pattern.
    """
    handle_lower = handle.lower()
    return any(pattern in handle_lower for pattern in BOT_PATTERNS)


def compute_authority_score(post: SocialPost) -> float:
    """Compute authority score 0-1 for a post's author.

    Combines three signals:
        - Follower count (log scale, max 0.4)
        - Platform weight (max 0.2)
        - Engagement metrics (log scale, max 0.3)

    Args:
        post: SocialPost with author and engagement data.

    Returns:
        Float 0-1 authority score.
    """
    score = 0.0
    followers = post.author_followers or 0

    # Follower-based (log scale)
    if followers > 0:
        score += min(0.4, math.log10(max(1, followers)) / 15)

    # Platform bonus
    score += _PLATFORM_WEIGHTS.get(post.platform, 0.05)

    # Engagement-based
    metrics = post.metrics or {}
    engagement = (
        metrics.get("likes", 0)
        + metrics.get("replies", 0) * 2
        + metrics.get("reposts", 0) * 3
        + metrics.get("score", 0)
        + metrics.get("comments", 0) * 2
    )
    if engagement > 0:
        score += min(0.3, math.log10(max(1, engagement)) / 10)

    return min(1.0, round(score, 3))


def filter_low_authority(
    signals: List[ProcessedSignal],
    min_score: float = MIN_AUTHORITY_SCORE,
) -> List[ProcessedSignal]:
    """Remove signals from very low-authority sources.

    Args:
        signals: ProcessedSignal list with authority_score set.
        min_score: Minimum authority score to keep.

    Returns:
        Filtered list of signals.
    """
    filtered = [s for s in signals if s.authority_score >= min_score]
    removed = len(signals) - len(filtered)
    if removed:
        logger.info(
            "Authority filter: removed %d/%d signals below %.2f",
            removed,
            len(signals),
            min_score,
        )
    return filtered


def extract_top_voices(
    signals: List[ProcessedSignal],
    limit: int = 10,
    max_per_author: int = 3,
) -> List[Dict]:
    """Extract top voices with diversity cap.

    Ranks authors by a weighted combination of authority score (60%)
    and signal count (40%, capped at max_per_author). This prevents
    prolific but low-authority accounts from dominating.

    Filters out known bot handles.

    Args:
        signals: All ProcessedSignal from the run.
        limit: Maximum number of voices to return.
        max_per_author: Cap for signal_count contribution to ranking.

    Returns:
        List of voice dicts with handle, name, platform, authority, signal_count.
    """
    voice_scores: Dict[str, Dict] = {}

    for s in signals:
        handle = s.post.author_handle
        if not handle or _is_bot(handle):
            continue

        if handle not in voice_scores:
            voice_scores[handle] = {
                "handle": handle,
                "name": s.post.author_display_name,
                "platform": s.post.platform,
                "authority": s.authority_score,
                "signal_count": 0,
                "themes": set(),
            }
        voice_scores[handle]["signal_count"] += 1
        voice_scores[handle]["authority"] = max(
            voice_scores[handle]["authority"], s.authority_score
        )
        if s.theme:
            voice_scores[handle]["themes"].add(s.theme)

    # Diversity: cap signal_count contribution
    sorted_voices = sorted(
        voice_scores.values(),
        key=lambda v: (
            v["authority"] * 0.6
            + min(1.0, v["signal_count"] / max_per_author) * 0.4
        ),
        reverse=True,
    )

    # Convert themes set to list for serialization
    result = []
    for v in sorted_voices[:limit]:
        result.append({
            "handle": v["handle"],
            "name": v["name"],
            "platform": v["platform"],
            "authority": v["authority"],
            "signal_count": v["signal_count"],
            "themes": sorted(v["themes"]),
        })

    return result
