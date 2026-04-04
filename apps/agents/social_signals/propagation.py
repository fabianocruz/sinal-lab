"""Cross-platform propagation tracking for social signals.

Groups signals by shared URL or content hash to detect when the same
topic surfaces across multiple platforms. The propagation score
rewards multi-platform coverage as a stronger signal of relevance.
"""

import logging
from collections import defaultdict
from typing import Dict, List

from apps.agents.social_signals.models import ProcessedSignal

logger = logging.getLogger(__name__)


def track_cross_platform(
    signals: List[ProcessedSignal],
) -> Dict[str, List[str]]:
    """Group signals by external_url or content_hash to find same topic across platforms.

    Two signals are considered related if they share the same external_url
    (the URL they link to) or the same content_hash. For each unique key,
    we collect all distinct platforms where the topic appeared.

    Args:
        signals: Processed signals from classification.

    Returns:
        Dict mapping group_key -> list of distinct platform names.
        Only includes groups with 2+ platforms.
    """
    # Map: group_key -> set of platforms
    url_platforms: Dict[str, set] = defaultdict(set)
    hash_platforms: Dict[str, set] = defaultdict(set)

    for signal in signals:
        platform = signal.post.platform

        # Group by external URL (the link target, not the post URL)
        if signal.post.external_url:
            url_platforms[signal.post.external_url].add(platform)

        # Group by content hash
        if signal.content_hash:
            hash_platforms[signal.content_hash].add(platform)

    # Merge: prefer external_url groups (more meaningful), supplement with hash
    result: Dict[str, List[str]] = {}

    for key, platforms in url_platforms.items():
        if len(platforms) >= 2:
            result[key] = sorted(platforms)

    for key, platforms in hash_platforms.items():
        if len(platforms) >= 2 and key not in result:
            result[key] = sorted(platforms)

    logger.info(
        "Cross-platform tracking: %d multi-platform groups found from %d signals",
        len(result),
        len(signals),
    )

    return result


def compute_propagation_score(platforms_seen: List[str]) -> float:
    """Compute a propagation score based on platform count.

    1 platform  = 0.2 (baseline, single source)
    2 platforms = 0.5
    3 platforms = 0.75
    4+ platforms = 1.0

    Args:
        platforms_seen: List of platform names where the topic was detected.

    Returns:
        Float 0.0-1.0 propagation score.
    """
    n = len(set(platforms_seen))
    if n <= 0:
        return 0.0
    elif n == 1:
        return 0.2
    elif n == 2:
        return 0.5
    elif n == 3:
        return 0.75
    else:
        return 1.0


def enrich_signals_with_propagation(
    signals: List[ProcessedSignal],
) -> Dict[str, float]:
    """Compute per-content-hash propagation scores for all signals.

    Returns a lookup dict that pipeline/scorer can use to augment
    the cross_platform_propagation dimension at the signal level.

    Args:
        signals: All processed signals.

    Returns:
        Dict mapping content_hash -> propagation_score.
    """
    cross_platform = track_cross_platform(signals)

    # Build a reverse index: for each signal, find its best propagation score
    hash_to_score: Dict[str, float] = {}

    # Index signals by their external_url and content_hash
    url_to_hashes: Dict[str, List[str]] = defaultdict(list)
    for signal in signals:
        if signal.post.external_url:
            url_to_hashes[signal.post.external_url].append(signal.content_hash)

    # Assign scores: signals whose external_url appears in cross_platform
    for url, platforms in cross_platform.items():
        score = compute_propagation_score(platforms)
        for content_hash in url_to_hashes.get(url, []):
            hash_to_score[content_hash] = max(
                hash_to_score.get(content_hash, 0.0), score,
            )

    # Also assign scores by content_hash directly
    hash_platforms: Dict[str, set] = defaultdict(set)
    for signal in signals:
        if signal.content_hash:
            hash_platforms[signal.content_hash].add(signal.post.platform)

    for content_hash, platforms in hash_platforms.items():
        if len(platforms) >= 2:
            score = compute_propagation_score(list(platforms))
            hash_to_score[content_hash] = max(
                hash_to_score.get(content_hash, 0.0), score,
            )

    return hash_to_score
