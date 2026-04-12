"""Signal Score computation with 8 dimensions.

Computes the Signal Score for clusters of social signals. Each dimension
captures a different aspect of signal strength, from raw volume to
cross-platform propagation and commercial maturity.

Signal classification:
    Trend: high volume, high engagement, high recurrence. Already visible.
    Emerging Signal: low volume but high authority, rapid growth, cross-platform.
    Weak Signal: sporadic in relevant niches, new language, few but authoritative authors.
"""

import logging
import math
from collections import Counter
from typing import Dict, List, Optional

from apps.agents.social_signals.config import DIMENSION_WEIGHTS
from apps.agents.social_signals.models import ProcessedSignal, SignalDimensions

logger = logging.getLogger(__name__)


def compute_cluster_dimensions(
    signals: List[ProcessedSignal],
    previous_count: int = 0,
    previous_sentiment: float = 0.0,
    known_authors: Optional[set] = None,
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

    n = len(signals)
    if known_authors is None:
        known_authors = set()

    return SignalDimensions(
        volume=_compute_volume(n),
        velocity=_compute_velocity(n, previous_count),
        authority_concentration=_compute_authority_concentration(signals),
        cross_platform_propagation=_compute_cross_platform(signals),
        sentiment_shift=_compute_sentiment_shift(signals, previous_sentiment),
        new_entrants=_compute_new_entrants(signals, known_authors),
        narrative_maturity=_compute_narrative_maturity(signals),
        commercial_signals=_compute_commercial_signals(signals),
    )


def classify_signal_type(dimensions: SignalDimensions) -> str:
    """Classify a cluster as trend, emerging_signal, or weak_signal.

    Args:
        dimensions: Computed signal dimensions.

    Returns:
        One of: "trend", "emerging_signal", "weak_signal"
    """
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

    When historical data is available, uses velocity-based logic.
    On first run (no historical data), falls back to composite_score
    thresholds so that high-scoring clusters can appear as "accelerating"
    instead of everything defaulting to "emerging".

    Args:
        dimensions: Computed signal dimensions.
        weeks_active: How many weeks this cluster has been detected.
        has_historical_data: Whether previous-period data was available
            for velocity computation. When False, uses score-based
            thresholds instead of velocity.

    Returns:
        One of: "emerging", "accelerating", "peaking", "declining"
    """
    velocity = dimensions.velocity
    volume = dimensions.volume

    if not has_historical_data:
        # First run: no velocity data is meaningful (all velocities are
        # the neutral 0.5 default). Use composite_score thresholds instead.
        composite = dimensions.composite_score(DIMENSION_WEIGHTS)
        if composite > 0.4:
            return "accelerating"
        elif composite > 0.3:
            return "emerging"
        elif composite > 0.2:
            return "weak_signal"
        else:
            return "declining"

    # Velocity-based logic when historical data is available
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

    No previous data = 0.5 (neutral). Doubling = 0.75. 10x = 1.0.
    """
    if previous_count == 0:
        return 0.5 if current_count > 0 else 0.0

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
    return min(1.0, shift * 2.0)  # 0.5 shift = 1.0 score


def _compute_new_entrants(
    signals: List[ProcessedSignal],
    known_authors: set,
) -> float:
    """Percentage of authors discussing topic for the first time."""
    if not signals:
        return 0.0

    authors = set(s.post.author_handle for s in signals if s.post.author_handle)
    if not authors:
        return 0.0

    if not known_authors:
        return 0.5  # No historical data, neutral

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
    # Short posts (~100 chars) = low maturity, long (500+) = high
    return min(1.0, avg_length / 500.0)


def _compute_commercial_signals(signals: List[ProcessedSignal]) -> float:
    """Presence of product launches, funding, hiring mentions."""
    if not signals:
        return 0.0

    commercial = sum(1 for s in signals if s.is_commercial)
    return min(1.0, commercial / max(1, len(signals)) * 3.0)


# Handles known to be bots or AI assistants — excluded from top voices/posts.
_BOT_HANDLES: set = {
    "grok", "chatgpt", "copilot", "perplexity_ai", "claudeai",
    "openai", "gemini", "bard",
}

# Text patterns indicating sponsored/promotional content.
_SPONSORED_PATTERNS: list = [
    "conteúdo patrocinado", "conteudo patrocinado", "publi",
    "branded content", "sponsored", "#ad ", "#publi",
]


def _is_bot(handle: str) -> bool:
    """Check if a handle belongs to a known bot."""
    return handle.lower() in _BOT_HANDLES


def _is_sponsored(text: str) -> bool:
    """Check if a post is sponsored/promotional content."""
    text_lower = text.lower()
    return any(p in text_lower for p in _SPONSORED_PATTERNS)


def extract_top_voices(
    signals: List[ProcessedSignal],
    limit: int = 10,
) -> List[Dict]:
    """Extract top voices (most active + highest authority) from signals."""
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
    return sorted_voices[:limit]


def extract_top_posts(
    signals: List[ProcessedSignal],
    limit: int = 10,
) -> List[Dict]:
    """Extract top posts by engagement, text quality, and authority.

    Social media posts are ranked by engagement metrics. RSS/web posts
    (which have no engagement data) are ranked by text length and
    commercial signal presence as a proxy for quality.
    """
    scored = []
    for s in signals:
        # Skip bots and sponsored content
        if _is_bot(s.post.author_handle or ""):
            continue
        if _is_sponsored(s.post.text or ""):
            continue

        metrics = s.post.metrics or {}
        engagement = (
            metrics.get("likes", 0)
            + metrics.get("replies", 0) * 2
            + metrics.get("reposts", 0) * 3
            + metrics.get("score", 0)  # Reddit score
            + metrics.get("views", 0) * 0.01  # YouTube views
        )

        if engagement > 0:
            # Social media: rank by engagement + authority
            score = engagement * 0.5 + s.authority_score * 1000 * 0.5
        else:
            # RSS/web: rank by text quality (length + commercial signals)
            text_len = len(s.post.text or "")
            if text_len < 50:
                continue  # Too short to be useful
            quality = min(1.0, text_len / 500.0)  # Longer = more analytical
            commercial_bonus = 0.3 if s.is_commercial else 0.0
            score = (quality + commercial_bonus) * 10  # Lower scale than engagement

        scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "url": s.post.url,
            "text": s.post.text[:200],
            "author": s.post.author_display_name or s.post.author_handle,
            "platform": s.post.platform,
            "metrics": s.post.metrics,
        }
        for _, s in scored[:limit]
    ]
