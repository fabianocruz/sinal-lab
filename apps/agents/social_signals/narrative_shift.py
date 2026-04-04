"""Narrative Shift Detection for Social Signals Intelligence agent.

Compares current-period clusters against previous-period clusters to detect
meaningful changes in narrative momentum: new narratives appearing,
existing narratives accelerating or decelerating.

Designed to be called after scoring in the pipeline, with results included
in the output metadata for editorial review.
"""

import logging
from typing import Dict, List, Optional

from apps.agents.social_signals.models import SignalClusterResult

logger = logging.getLogger(__name__)

# Minimum score delta to classify as acceleration or deceleration
SCORE_DELTA_THRESHOLD = 0.1


def detect_narrative_shifts(
    current_clusters: List[SignalClusterResult],
    previous_clusters: Optional[List[SignalClusterResult]] = None,
    score_delta_threshold: float = SCORE_DELTA_THRESHOLD,
) -> List[dict]:
    """Compare current vs previous period to detect narrative shifts.

    Identifies three types of shifts:
    - new_narrative: A theme appearing for the first time
    - acceleration: A theme whose composite score increased significantly
    - deceleration: A theme whose composite score decreased significantly

    Args:
        current_clusters: Clusters from the current run.
        previous_clusters: Clusters from the previous period (e.g., last week).
            If None or empty, all current clusters are treated as new narratives.
        score_delta_threshold: Minimum absolute score change to classify as
            acceleration or deceleration. Defaults to 0.1.

    Returns:
        List of shift dicts with type, cluster name, theme, and deltas.
    """
    shifts: List[dict] = []

    if not current_clusters:
        return shifts

    if not previous_clusters:
        # No previous data: all clusters are new narratives
        for cluster in current_clusters:
            shifts.append({
                "type": "new_narrative",
                "cluster": cluster.name,
                "theme": cluster.theme,
                "score": round(cluster.composite_score, 3),
                "signal_count": cluster.signal_count,
            })
        return shifts

    # Build lookup by theme for previous clusters
    prev_by_theme: Dict[str, SignalClusterResult] = {}
    for c in previous_clusters:
        theme = c.theme or c.name
        # Keep the highest-scoring cluster per theme
        if theme not in prev_by_theme or c.composite_score > prev_by_theme[theme].composite_score:
            prev_by_theme[theme] = c

    for cluster in current_clusters:
        theme = cluster.theme or cluster.name
        prev = prev_by_theme.get(theme)

        if not prev:
            shifts.append({
                "type": "new_narrative",
                "cluster": cluster.name,
                "theme": theme,
                "score": round(cluster.composite_score, 3),
                "signal_count": cluster.signal_count,
            })
            continue

        score_delta = cluster.composite_score - prev.composite_score
        count_delta = cluster.signal_count - prev.signal_count

        if score_delta > score_delta_threshold:
            shifts.append({
                "type": "acceleration",
                "cluster": cluster.name,
                "theme": theme,
                "score_delta": round(score_delta, 3),
                "count_delta": count_delta,
                "current_score": round(cluster.composite_score, 3),
                "previous_score": round(prev.composite_score, 3),
            })
        elif score_delta < -score_delta_threshold:
            shifts.append({
                "type": "deceleration",
                "cluster": cluster.name,
                "theme": theme,
                "score_delta": round(score_delta, 3),
                "count_delta": count_delta,
                "current_score": round(cluster.composite_score, 3),
                "previous_score": round(prev.composite_score, 3),
            })

    if shifts:
        logger.info(
            "Detected %d narrative shifts: %d new, %d accelerating, %d decelerating",
            len(shifts),
            sum(1 for s in shifts if s["type"] == "new_narrative"),
            sum(1 for s in shifts if s["type"] == "acceleration"),
            sum(1 for s in shifts if s["type"] == "deceleration"),
        )

    return shifts


def summarize_shifts(shifts: List[dict]) -> str:
    """Generate a human-readable summary of narrative shifts.

    Useful for including in the output metadata or alert emails.

    Args:
        shifts: List of shift dicts from detect_narrative_shifts().

    Returns:
        Markdown-formatted summary string.
    """
    if not shifts:
        return "Nenhuma mudanca narrativa significativa detectada."

    lines = []
    new_narratives = [s for s in shifts if s["type"] == "new_narrative"]
    accelerations = [s for s in shifts if s["type"] == "acceleration"]
    decelerations = [s for s in shifts if s["type"] == "deceleration"]

    if new_narratives:
        lines.append("**Novas narrativas:**")
        for s in new_narratives:
            lines.append(f"- {s['cluster']} (score: {s['score']:.2f})")

    if accelerations:
        lines.append("**Em aceleracao:**")
        for s in accelerations:
            lines.append(
                f"- {s['cluster']} (delta: +{s['score_delta']:.2f}, "
                f"sinais: {s.get('count_delta', 0):+d})"
            )

    if decelerations:
        lines.append("**Em desaceleracao:**")
        for s in decelerations:
            lines.append(
                f"- {s['cluster']} (delta: {s['score_delta']:.2f})"
            )

    return "\n".join(lines)
