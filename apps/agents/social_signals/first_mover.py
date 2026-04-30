"""First Mover Detection for Social Signals Intelligence agent.

For each signal cluster, identifies who posted about the topic FIRST,
the early adopters (within 24h of first post), and how far ahead the
first mover was relative to the median post in the cluster.

This data powers the "Who Started It" section in the Weekly Pulse,
helping readers understand information flow dynamics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from apps.agents.social_signals.models import ProcessedSignal, SignalClusterResult

logger = logging.getLogger(__name__)

# Signals within this window of the first post are considered early adopters
EARLY_ADOPTER_WINDOW_HOURS = 24


def _compute_median_timestamp(timestamps: List[datetime]) -> Optional[datetime]:
    """Return the median timestamp from a sorted list.

    Args:
        timestamps: Sorted list of timezone-aware datetimes.

    Returns:
        Median datetime, or None if list is empty.
    """
    if not timestamps:
        return None
    mid = len(timestamps) // 2
    if len(timestamps) % 2 == 0:
        # Average the two middle timestamps
        delta = (timestamps[mid] - timestamps[mid - 1]) / 2
        return timestamps[mid - 1] + delta
    return timestamps[mid]


def detect_first_movers(
    signals: List[ProcessedSignal],
    clusters: List[SignalClusterResult],
    early_adopter_window_hours: float = EARLY_ADOPTER_WINDOW_HOURS,
) -> Dict[str, Dict[str, Any]]:
    """For each cluster, find who posted about the topic FIRST.

    Signals without a published_at timestamp are excluded from analysis.

    Args:
        signals: All processed signals (used for lookup if needed).
        clusters: Signal clusters from the pipeline.
        early_adopter_window_hours: Hours after first post to count as
            early adopter. Defaults to 24.

    Returns:
        Dict mapping cluster slug -> {
            "first_mover": {"handle", "name", "platform", "posted_at", "url"},
            "early_adopters": [top 5 authors within the early window],
            "hours_before_mainstream": float (hours between first and median)
        }
    """
    result: Dict[str, Dict[str, Any]] = {}

    for cluster in clusters:
        slug = cluster.slug or cluster.name
        first_mover_data = _analyze_cluster_timing(
            cluster, early_adopter_window_hours,
        )
        if first_mover_data:
            result[slug] = first_mover_data

    if result:
        logger.info(
            "First mover detection: analyzed %d clusters, %d had timing data",
            len(clusters),
            len(result),
        )

    return result


def _analyze_cluster_timing(
    cluster: SignalClusterResult,
    early_adopter_window_hours: float,
) -> Optional[Dict[str, Any]]:
    """Analyze timing for a single cluster.

    Args:
        cluster: The signal cluster to analyze.
        early_adopter_window_hours: Window for early adopters.

    Returns:
        First mover dict, or None if no signals have timestamps.
    """
    # Filter signals with valid timestamps. Some collectors (RSS) emit
    # published_at as ISO string instead of datetime; coerce here to keep
    # sorting comparable across sources.
    timed_signals: list[ProcessedSignal] = []
    for s in cluster.signals:
        ts = s.post.published_at
        if ts is None:
            continue
        if isinstance(ts, str):
            try:
                s.post.published_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
        timed_signals.append(s)

    if not timed_signals:
        return None

    # Sort by published_at ascending (earliest first)
    timed_signals.sort(key=lambda s: s.post.published_at)  # type: ignore[arg-type]

    first_signal = timed_signals[0]
    first_time = first_signal.post.published_at
    assert first_time is not None  # guaranteed by filter above

    # Compute median timestamp
    timestamps = [s.post.published_at for s in timed_signals]  # type: ignore[misc]
    median_time = _compute_median_timestamp(timestamps)  # type: ignore[arg-type]

    # Hours before mainstream (first -> median)
    hours_before_mainstream = 0.0
    if median_time and median_time > first_time:
        delta = median_time - first_time
        hours_before_mainstream = delta.total_seconds() / 3600.0

    # Early adopters: authors within the window after first post
    window_cutoff = first_time + timedelta(hours=early_adopter_window_hours)
    seen_handles: set = set()
    early_adopters: List[Dict[str, Any]] = []

    for signal in timed_signals:
        pub_time = signal.post.published_at
        assert pub_time is not None
        if pub_time > window_cutoff:
            break

        handle = signal.post.author_handle
        if not handle or handle in seen_handles:
            continue

        # Skip the first mover from early adopters list
        if signal is first_signal:
            seen_handles.add(handle)
            continue

        seen_handles.add(handle)
        early_adopters.append({
            "handle": handle,
            "name": signal.post.author_display_name or handle,
            "platform": signal.post.platform,
            "posted_at": pub_time.isoformat() if pub_time else "",
            "url": signal.post.url,
        })

        if len(early_adopters) >= 5:
            break

    return {
        "first_mover": {
            "handle": first_signal.post.author_handle,
            "name": first_signal.post.author_display_name or first_signal.post.author_handle,
            "platform": first_signal.post.platform,
            "posted_at": first_time.isoformat(),
            "url": first_signal.post.url,
        },
        "early_adopters": early_adopters,
        "hours_before_mainstream": round(hours_before_mainstream, 2),
    }
