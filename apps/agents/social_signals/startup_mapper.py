"""Signal-to-Startup Mapping for Social Signals Intelligence agent.

Maps social signals to companies in the database by matching company
names against signal text. Produces a summary of which startups are
being discussed, with sentiment and theme breakdowns.

This bridges the Social Signals agent output with the INDEX agent's
company database, enabling cross-agent intelligence.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from apps.agents.social_signals.models import ProcessedSignal

logger = logging.getLogger(__name__)

# Minimum company name length to avoid false positives (e.g., "Nu", "AI")
MIN_COMPANY_NAME_LENGTH = 4


def _load_companies(session: Any) -> List[Tuple[str, str]]:
    """Load active companies from the database.

    Args:
        session: SQLAlchemy session.

    Returns:
        List of (name, slug) tuples.
    """
    from packages.database.models import Company

    companies = (
        session.query(Company.name, Company.slug)
        .filter(
            Company.status == "active",
            Company.name.isnot(None),
        )
        .all()
    )
    return [(name, slug) for name, slug in companies]


def _match_company_in_text(name: str, text_lower: str) -> bool:
    """Check if a company name appears in text using word boundary matching.

    Uses regex word boundaries to avoid partial matches (e.g., "Nu" matching
    "number" or "annual"). For names with special characters, falls back
    to simple substring match.

    Args:
        name: Company name (original case).
        text_lower: Lowered signal text.

    Returns:
        True if the company name appears as a distinct token.
    """
    name_lower = name.lower()
    try:
        pattern = r"\b" + re.escape(name_lower) + r"\b"
        return bool(re.search(pattern, text_lower))
    except re.error:
        return name_lower in text_lower


def map_signals_to_startups(
    signals: List[ProcessedSignal],
    session: Any,
    min_name_length: int = MIN_COMPANY_NAME_LENGTH,
) -> Dict[str, Dict[str, Any]]:
    """Map signals to companies in the database.

    For each active company, scans all signal texts for mentions. Returns
    a dict keyed by company slug with signal counts, snippets, average
    sentiment, and themes.

    Args:
        signals: Processed signals to scan for company mentions.
        session: SQLAlchemy session for loading companies.
        min_name_length: Minimum company name length to consider.
            Names shorter than this are skipped to avoid false positives.

    Returns:
        Dict: company_slug -> {
            "name": str,
            "signal_count": int,
            "signals": list (up to 5 signal summaries),
            "avg_sentiment": float,
            "themes": list[str],
        }
        Sorted by signal_count descending.
    """
    if not signals:
        return {}

    companies = _load_companies(session)
    if not companies:
        logger.info("No active companies found in database for signal mapping")
        return {}

    # Pre-compute lowered text for each signal (avoid repeated .lower() calls)
    signal_texts = [(s, s.post.text.lower()) for s in signals]

    mapping: Dict[str, Dict[str, Any]] = {}

    for name, slug in companies:
        if len(name) < min_name_length:
            continue

        matched_signals = [
            s for s, text_lower in signal_texts
            if _match_company_in_text(name, text_lower)
        ]

        if not matched_signals:
            continue

        sentiments = [s.sentiment for s in matched_signals]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        mapping[slug] = {
            "name": name,
            "signal_count": len(matched_signals),
            "signals": [
                {
                    "url": s.post.url,
                    "text": s.post.text[:150],
                    "sentiment": s.sentiment,
                    "platform": s.post.platform,
                }
                for s in matched_signals[:5]
            ],
            "avg_sentiment": round(avg_sentiment, 3),
            "themes": list(set(s.theme for s in matched_signals if s.theme)),
        }

    # Sort by signal_count descending
    sorted_mapping = dict(
        sorted(mapping.items(), key=lambda x: x[1]["signal_count"], reverse=True)
    )

    if sorted_mapping:
        logger.info(
            "Signal-startup mapping: %d companies matched across %d signals",
            len(sorted_mapping),
            len(signals),
        )

    return sorted_mapping


def map_signals_to_startups_static(
    signals: List[ProcessedSignal],
    companies: List[Tuple[str, str]],
    min_name_length: int = MIN_COMPANY_NAME_LENGTH,
) -> Dict[str, Dict[str, Any]]:
    """Map signals to a static list of companies (no DB required).

    Same logic as map_signals_to_startups but accepts companies as a
    parameter instead of loading from DB. Useful for testing and
    pipeline runs without database access.

    Args:
        signals: Processed signals to scan.
        companies: List of (name, slug) tuples.
        min_name_length: Minimum company name length.

    Returns:
        Same structure as map_signals_to_startups.
    """
    if not signals or not companies:
        return {}

    signal_texts = [(s, s.post.text.lower()) for s in signals]
    mapping: Dict[str, Dict[str, Any]] = {}

    for name, slug in companies:
        if len(name) < min_name_length:
            continue

        matched_signals = [
            s for s, text_lower in signal_texts
            if _match_company_in_text(name, text_lower)
        ]

        if not matched_signals:
            continue

        sentiments = [s.sentiment for s in matched_signals]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        mapping[slug] = {
            "name": name,
            "signal_count": len(matched_signals),
            "signals": [
                {
                    "url": s.post.url,
                    "text": s.post.text[:150],
                    "sentiment": s.sentiment,
                    "platform": s.post.platform,
                }
                for s in matched_signals[:5]
            ],
            "avg_sentiment": round(avg_sentiment, 3),
            "themes": list(set(s.theme for s in matched_signals if s.theme)),
        }

    return dict(
        sorted(mapping.items(), key=lambda x: x[1]["signal_count"], reverse=True)
    )
