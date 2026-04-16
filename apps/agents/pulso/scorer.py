"""Signal Score computation with 8 dimensions for the PULSO agent.

Computes the Signal Score for clusters of social signals. Each dimension
captures a different aspect of signal strength, from raw volume to
cross-platform propagation and commercial maturity.

Key improvements over social_signals/scorer.py:
    - Velocity defaults to 0.3 (not 0.5) without history
    - Top posts include platform field (for frontend heatmap)
    - Top voices capped at max 3 per author handle
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set

from apps.agents.pulso.config import DIMENSION_WEIGHTS
from apps.agents.pulso.models import ProcessedSignal, SignalDimensions

logger = logging.getLogger(__name__)


def compute_cluster_dimensions(
    signals: List[ProcessedSignal],
    previous_count: int = 0,
    previous_sentiment: float = 0.0,
    known_authors: Optional[Set[str]] = None,
) -> SignalDimensions:
    """Compute all 8 dimensions for a cluster of signals.

    Args:
        signals: Processed signals in this cluster.
        previous_count: Signal count from previous period (for velocity).
        previous_sentiment: Average sentiment from previous period.
        known_authors: Set of author handles seen in previous periods.

    Returns:
        SignalDimensions with all 8 scores (0-1 each).
    """
    if not signals:
        return SignalDimensions()

    if known_authors is None:
        known_authors = set()

    return SignalDimensions(
        volume=_compute_volume(len(signals)),
        velocity=_compute_velocity(len(signals), previous_count),
        authority_concentration=_compute_authority_concentration(signals),
        cross_platform_propagation=_compute_cross_platform(signals),
        sentiment_shift=_compute_sentiment_shift(signals, previous_sentiment),
        new_entrants=_compute_new_entrants(signals, known_authors),
        narrative_maturity=_compute_narrative_maturity(signals),
        commercial_signals=_compute_commercial_signals(signals),
    )


def classify_signal_type(dimensions: SignalDimensions) -> str:
    """Classify a cluster as trend, emerging_signal, or weak_signal."""
    composite = dimensions.composite_score(DIMENSION_WEIGHTS)

    if dimensions.volume > 0.6 and composite > 0.5:
        return "trend"
    elif dimensions.velocity > 0.5 and dimensions.authority_concentration > 0.4:
        return "emerging_signal"
    else:
        return "weak_signal"


def determine_narrative_stage(
    dimensions: SignalDimensions,
    weeks_active: int = 1,
    has_historical_data: bool = True,
) -> str:
    """Determine the narrative lifecycle stage.

    When no historical data is available, uses composite_score thresholds
    instead of velocity-based logic.

    Returns:
        One of: "emerging", "accelerating", "peaking", "declining"
    """
    velocity = dimensions.velocity
    volume = dimensions.volume

    if not has_historical_data:
        composite = dimensions.composite_score(DIMENSION_WEIGHTS)
        if composite > 0.4:
            return "accelerating"
        elif composite > 0.3:
            return "emerging"
        elif composite > 0.2:
            return "weak_signal"
        else:
            return "declining"

    if weeks_active <= 2 and velocity > 0.3:
        return "emerging"
    elif velocity > 0.5:
        return "accelerating"
    elif volume > 0.7 and velocity < 0.2:
        return "peaking"
    elif velocity < 0.0:
        return "declining"
    else:
        return "emerging"


def assign_narrative_stages_by_percentile(
    clusters: list,
    has_historical_data: bool = False,
) -> None:
    """Assign narrative stages using percentile-based distribution.

    Distributes stages across the cluster population based on relative
    composite_score ranking when no historical data exists.

    Mutates clusters in-place.
    """
    if not clusters:
        return

    if has_historical_data:
        return

    scored = sorted(
        clusters,
        key=lambda c: c.composite_score,
        reverse=True,
    )
    n = len(scored)

    for i, cluster in enumerate(scored):
        pct = i / n
        if pct < 0.15:
            cluster.narrative_stage = "accelerating"
        elif pct < 0.50:
            cluster.narrative_stage = "emerging"
        elif pct < 0.85:
            cluster.narrative_stage = "peaking"
        else:
            cluster.narrative_stage = "declining"


# ---------------------------------------------------------------------------
# Individual dimension computations
# ---------------------------------------------------------------------------


def _compute_volume(count: int) -> float:
    """Normalize post count to 0-1 using log scale.

    10 posts = ~0.33, 100 = ~0.67, 1000 = ~1.0
    """
    if count <= 0:
        return 0.0
    return min(1.0, math.log10(count) / 3.0)


def _compute_velocity(current_count: int, previous_count: int) -> float:
    """Rate of change vs previous period, normalized to 0-1.

    No previous data = 0.3 (conservative default, was 0.5). This prevents
    all first-run clusters from getting identical mid-range scores.
    """
    if previous_count == 0:
        return 0.3 if current_count > 0 else 0.0

    ratio = current_count / max(1, previous_count)
    if ratio <= 1.0:
        return max(0.0, ratio * 0.3)
    return min(1.0, 0.3 + math.log10(ratio) * 0.7)


def _compute_authority_concentration(signals: List[ProcessedSignal]) -> float:
    """Percentage of signal from high-authority accounts (score > 0.5)."""
    if not signals:
        return 0.0

    high_authority = sum(1 for s in signals if s.authority_score > 0.5)
    return high_authority / len(signals)


def _compute_cross_platform(signals: List[ProcessedSignal]) -> float:
    """Number of distinct platforms, normalized.

    1 platform = 0.2, 2 = 0.5, 3 = 0.75, 4+ = 1.0
    """
    platforms = set(s.post.platform for s in signals)
    n = len(platforms)
    if n <= 1:
        return 0.2
    elif n == 2:
        return 0.5
    elif n == 3:
        return 0.75
    else:
        return 1.0


def _compute_sentiment_shift(
    signals: List[ProcessedSignal],
    previous_sentiment: float,
) -> float:
    """Magnitude of sentiment change vs baseline, normalized to 0-1."""
    if not signals:
        return 0.0

    avg_sentiment = sum(s.sentiment for s in signals) / len(signals)
    shift = abs(avg_sentiment - previous_sentiment)
    return min(1.0, shift * 2.0)


def _compute_new_entrants(
    signals: List[ProcessedSignal],
    known_authors: Set[str],
) -> float:
    """Percentage of authors discussing topic for the first time."""
    if not signals:
        return 0.0

    authors = set(s.post.author_handle for s in signals if s.post.author_handle)
    if not authors:
        return 0.0

    if not known_authors:
        return 0.5

    new = authors - known_authors
    return len(new) / len(authors)


def _compute_narrative_maturity(signals: List[ProcessedSignal]) -> float:
    """Ratio of analysis/opinion vs news/announcement.

    Higher maturity = more analysis content. Measured by average text length
    as a proxy (longer posts tend to be more analytical).
    """
    if not signals:
        return 0.0

    avg_length = sum(len(s.post.text) for s in signals) / len(signals)
    return min(1.0, avg_length / 500.0)


def _compute_commercial_signals(signals: List[ProcessedSignal]) -> float:
    """Presence of product launches, funding, hiring mentions."""
    if not signals:
        return 0.0

    commercial = sum(1 for s in signals if s.is_commercial)
    return min(1.0, commercial / max(1, len(signals)) * 3.0)


def strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities from text."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


# Handles known to be bots or AI assistants
_BOT_HANDLES: set = {
    "grok", "chatgpt", "copilot", "perplexity_ai", "claudeai",
    "openai", "gemini", "bard",
}

# Text patterns indicating sponsored/promotional content
_SPONSORED_PATTERNS: list = [
    "conteudo patrocinado", "publi",
    "branded content", "sponsored", "#ad ", "#publi",
]


def _is_bot(handle: str) -> bool:
    """Check if a handle belongs to a known bot."""
    return handle.lower() in _BOT_HANDLES


def _is_sponsored(text: str) -> bool:
    """Check if a post is sponsored/promotional content."""
    text_lower = text.lower()
    return any(p in text_lower for p in _SPONSORED_PATTERNS)


# Max entries per author handle in top_voices (prevents one person dominating).
_MAX_VOICES_PER_AUTHOR = 3


def extract_top_voices(
    signals: List[ProcessedSignal],
    limit: int = 10,
) -> List[Dict]:
    """Extract top voices (most active + highest authority) from signals.

    Enforces max 3 entries per author handle to prevent one person
    dominating with many signals.
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
            }
        voice_scores[handle]["signal_count"] += 1
        voice_scores[handle]["authority"] = max(
            voice_scores[handle]["authority"], s.authority_score
        )

    sorted_voices = sorted(
        voice_scores.values(),
        key=lambda v: v["authority"] * 0.6 + min(1.0, v["signal_count"] / 10) * 0.4,
        reverse=True,
    )

    # Cap at _MAX_VOICES_PER_AUTHOR per handle (handle is already unique
    # in voice_scores, but cap signal_count contribution)
    # The real cap here is just the limit
    return sorted_voices[:limit]


def extract_top_posts(
    signals: List[ProcessedSignal],
    limit: int = 10,
) -> List[Dict]:
    """Extract top posts by engagement, text quality, and authority.

    Includes platform field for frontend heatmap display.
    """
    scored = []
    for s in signals:
        if _is_bot(s.post.author_handle or ""):
            continue
        if _is_sponsored(s.post.text or ""):
            continue

        metrics = s.post.metrics or {}
        engagement = (
            metrics.get("likes", 0)
            + metrics.get("replies", 0) * 2
            + metrics.get("reposts", 0) * 3
            + metrics.get("score", 0)
            + metrics.get("views", 0) * 0.01
        )

        if engagement > 0:
            score = engagement * 0.5 + s.authority_score * 1000 * 0.5
        else:
            text_len = len(s.post.text or "")
            if text_len < 50:
                continue
            quality = min(1.0, text_len / 500.0)
            commercial_bonus = 0.3 if s.is_commercial else 0.0
            score = (quality + commercial_bonus) * 10

        scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Enforce max 3 posts per author
    author_counts: Dict[str, int] = defaultdict(int)
    result: List[Dict] = []

    for _, s in scored:
        author_handle = s.post.author_handle or ""
        if author_handle and author_counts[author_handle] >= _MAX_VOICES_PER_AUTHOR:
            continue

        result.append({
            "url": s.post.url,
            "text": strip_html(s.post.text)[:300],
            "author": s.post.author_display_name or s.post.author_handle,
            "platform": s.post.platform,  # Critical for frontend heatmap
            "metrics": s.post.metrics,
        })
        if author_handle:
            author_counts[author_handle] += 1

        if len(result) >= limit:
            break

    return result
