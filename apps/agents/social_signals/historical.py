"""Historical context loading for velocity and sentiment shift computation.

Loads previous SignalCluster records from the database to provide the
baseline needed for velocity (signal count growth) and sentiment shift
(sentiment change) dimensions in the current period's scoring.

Gracefully degrades: returns empty context if DB is unavailable.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from apps.agents.social_signals.models import SignalClusterResult, SignalDimensions

logger = logging.getLogger(__name__)


def load_previous_clusters(
    session: Any,
    weeks_back: int = 4,
    current_year: Optional[int] = None,
    current_week: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Load recent SignalCluster records from DB for velocity computation.

    Fetches clusters from the last N weeks to build historical context.
    Uses the SignalCluster model from packages.database.models.

    Args:
        session: SQLAlchemy session (or None for graceful degradation).
        weeks_back: Number of weeks of history to load (default 4).
        current_year: Override current year (for testing). Defaults to now.
        current_week: Override current week (for testing). Defaults to now.

    Returns:
        List of dicts with cluster data from DB. Empty list if DB unavailable.
    """
    if session is None:
        logger.info("No DB session provided, returning empty historical context")
        return []

    try:
        from packages.database.models.signal_cluster import SignalCluster

        now = datetime.now(timezone.utc)
        year = current_year or now.year
        week = current_week or now.isocalendar()[1]

        # Compute the range of (year, week) pairs to query
        week_ranges = []
        for i in range(1, weeks_back + 1):
            target_week = week - i
            target_year = year
            if target_week <= 0:
                target_week += 52
                target_year -= 1
            week_ranges.append((target_year, target_week))

        # Build query: clusters from the specified weeks
        query = session.query(SignalCluster)
        conditions = []
        from sqlalchemy import and_, or_

        for y, w in week_ranges:
            conditions.append(
                and_(SignalCluster.year == y, SignalCluster.week_number == w)
            )

        if not conditions:
            return []

        clusters = query.filter(or_(*conditions)).all()

        result = []
        for cluster in clusters:
            result.append({
                "name": cluster.name,
                "slug": cluster.slug,
                "theme": cluster.theme,
                "sub_theme": cluster.sub_theme,
                "signal_count": cluster.signal_count or 0,
                "composite_score": cluster.composite_score or 0.0,
                "dimensions": cluster.dimensions or {},
                "narrative_stage": cluster.narrative_stage,
                "top_voices": cluster.top_voices or [],
                "week_number": cluster.week_number,
                "year": cluster.year,
            })

        logger.info(
            "Loaded %d historical clusters from %d weeks back (year=%d, week=%d)",
            len(result),
            weeks_back,
            year,
            week,
        )
        return result

    except Exception as exc:
        logger.warning(
            "Failed to load historical clusters from DB: %s. "
            "Returning empty context (graceful degradation).",
            exc,
        )
        return []


def build_historical_context(
    previous_clusters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Extract theme counts, sentiments, and known authors from historical data.

    Builds the lookup structures needed by the scorer for computing
    velocity (count change), sentiment_shift (sentiment delta), and
    new_entrants (new authors) dimensions.

    Args:
        previous_clusters: List of cluster dicts from load_previous_clusters().

    Returns:
        Dict with:
            - theme_counts: Dict[theme -> total signal count]
            - theme_sentiments: Dict[theme -> average sentiment]
            - known_authors: Set of author handles seen in previous periods
            - weeks_active: Dict[theme -> number of weeks this theme appeared]
    """
    theme_counts: Dict[str, int] = {}
    theme_sentiments: Dict[str, float] = {}
    theme_sentiment_counts: Dict[str, int] = {}
    known_authors: Set[str] = set()
    theme_weeks: Dict[str, Set[int]] = {}

    for cluster in previous_clusters:
        theme = cluster.get("theme") or "other"
        signal_count = cluster.get("signal_count", 0)
        week_number = cluster.get("week_number", 0)

        # Accumulate signal counts
        theme_counts[theme] = theme_counts.get(theme, 0) + signal_count

        # Track unique weeks per theme
        if theme not in theme_weeks:
            theme_weeks[theme] = set()
        if week_number:
            theme_weeks[theme].add(week_number)

        # Accumulate sentiment from dimensions if available
        dimensions = cluster.get("dimensions", {})
        if isinstance(dimensions, dict):
            sentiment_shift = dimensions.get("sentiment_shift", 0.0)
            if sentiment_shift:
                theme_sentiments[theme] = (
                    theme_sentiments.get(theme, 0.0) + sentiment_shift
                )
                theme_sentiment_counts[theme] = (
                    theme_sentiment_counts.get(theme, 0) + 1
                )

        # Extract known authors from top_voices
        top_voices = cluster.get("top_voices", [])
        if isinstance(top_voices, list):
            for voice in top_voices:
                if isinstance(voice, dict):
                    handle = voice.get("handle", "")
                    if handle:
                        known_authors.add(handle)

    # Normalize sentiment averages
    for theme in theme_sentiments:
        count = theme_sentiment_counts.get(theme, 1)
        theme_sentiments[theme] = theme_sentiments[theme] / max(count, 1)

    # Convert theme_weeks to counts
    weeks_active: Dict[str, int] = {
        theme: len(weeks) for theme, weeks in theme_weeks.items()
    }

    context = {
        "theme_counts": theme_counts,
        "theme_sentiments": theme_sentiments,
        "known_authors": known_authors,
        "weeks_active": weeks_active,
    }

    logger.info(
        "Built historical context: %d themes, %d known authors, %d weeks of data",
        len(theme_counts),
        len(known_authors),
        sum(len(w) for w in theme_weeks.values()),
    )

    return context
