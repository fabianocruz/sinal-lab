"""Stable identity for signal clusters, derived from content not from labels.

A cluster's database key used to be a slug of the name an LLM generated for
it. That name is regenerated on every run, so a re-labelled bucket produced
an INSERT instead of an UPDATE. With the clustering job running every 6h,
production accumulated ~277 rows per week for what is really ~10 clusters,
and one bucket appeared on the site under several near-identical names.

The fix is to key a cluster on what it contains. Two clusters built from
substantially the same signals are the same cluster, whatever the LLM
decided to call them this time.
"""

import logging
from typing import Any, Optional, Set

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

#: Fraction of the smaller cluster's signals that must be shared for two
#: clusters to be considered the same bucket. Containment against the
#: smaller set (rather than Jaccard) is deliberate: the signal pool grows
#: during the week, so a later run legitimately holds a superset of an
#: earlier run's signals and Jaccard would drift below any usable threshold
#: by Friday.
MEMBERSHIP_OVERLAP_THRESHOLD = 0.60

#: Absolute floor on shared signals. Without it, two 3-signal clusters that
#: happen to share 2 posts would be merged on a 0.67 ratio.
MIN_SHARED_SIGNALS = 5


def find_cluster_by_membership(
    session: Session,
    content_hashes: Set[str],
    year: int,
    week_number: int,
    threshold: float = MEMBERSHIP_OVERLAP_THRESHOLD,
    min_shared: int = MIN_SHARED_SIGNALS,
) -> Optional[Any]:
    """Return the existing cluster for this week holding the same signals.

    Membership is read from ``SignalCluster.signal_hashes``, written by the
    agent on every upsert. It cannot be recovered from
    ``social_signals.cluster_id``: that column records the cluster a signal
    landed in when first written, not the composition of each cluster at
    each run. Comparison is scoped to the same ISO week, so week boundaries
    still start a fresh identity and week-over-week history stays intact.

    Args:
        session: Active SQLAlchemy session.
        content_hashes: Content hashes of the incoming cluster's signals.
        year: ISO year of the incoming cluster.
        week_number: ISO week of the incoming cluster.
        threshold: Minimum shared fraction of the smaller cluster.
        min_shared: Minimum absolute number of shared signals.

    Returns:
        The best-matching SignalCluster row, or None when no cluster in this
        week is made of substantially the same signals.
    """
    from packages.database.models.signal_cluster import SignalCluster

    if not content_hashes or len(content_hashes) < min_shared:
        return None

    candidates = (
        session.query(SignalCluster)
        .filter(
            SignalCluster.year == year,
            SignalCluster.week_number == week_number,
            SignalCluster.signal_hashes.isnot(None),
        )
        .all()
    )

    best = None
    best_ratio = 0.0
    for candidate in candidates:
        stored = candidate.signal_hashes or []
        if not isinstance(stored, list):
            continue
        hashes = {h for h in stored if h}
        if not hashes:
            continue
        shared = len(hashes & content_hashes)
        if shared < min_shared:
            continue
        # Containment against the smaller set, not Jaccard: see the note on
        # MEMBERSHIP_OVERLAP_THRESHOLD.
        ratio = shared / min(len(hashes), len(content_hashes))
        if ratio >= threshold and ratio > best_ratio:
            best, best_ratio = candidate, ratio

    if best is not None:
        logger.info(
            "Cluster matched by membership (%.0f%% shared): reusing '%s' (%s)",
            best_ratio * 100,
            best.name,
            best.slug,
        )
    return best
