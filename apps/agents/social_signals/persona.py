"""Persona-based Relevance Scoring for Social Signals Intelligence agent.

Computes how relevant each signal is for different reader personas
(CTO, VC, Founder). Used to personalize the Weekly Pulse output
and power future persona-specific email digests.

Each persona has theme weight preferences, keyword boosts, and
preferred voice types that influence ranking.
"""

import logging
from typing import Any, Dict, List, Optional

from apps.agents.social_signals.models import ProcessedSignal

logger = logging.getLogger(__name__)


PERSONAS: Dict[str, Dict[str, Any]] = {
    "cto": {
        "label": "CTO / Tech Lead",
        "themes_weight": {"AI": 1.5, "Fintech": 0.8, "AI in Banking": 1.2},
        "keywords_boost": [
            "infrastructure", "devops", "architecture", "scalability",
            "security", "observability", "microservices", "kubernetes",
            "latency", "reliability",
        ],
        "voice_types": ["exec", "founder", "thought_leader"],
    },
    "vc": {
        "label": "Investidor / VC",
        "themes_weight": {"AI": 1.0, "Fintech": 1.5, "AI in Banking": 1.3},
        "keywords_boost": [
            "funding", "series", "valuation", "exit", "portfolio",
            "deal", "round", "seed", "ipo", "acquisition",
        ],
        "voice_types": ["vc", "angel"],
    },
    "founder": {
        "label": "Fundador / CEO",
        "themes_weight": {"AI": 1.2, "Fintech": 1.2, "AI in Banking": 1.0},
        "keywords_boost": [
            "product", "growth", "market", "traction", "revenue",
            "hiring", "pmf", "gtm", "churn", "retention",
        ],
        "voice_types": ["founder"],
    },
}


def get_persona(persona_key: str) -> Optional[Dict[str, Any]]:
    """Look up a persona definition by key.

    Args:
        persona_key: One of "cto", "vc", "founder".

    Returns:
        Persona dict, or None if key is invalid.
    """
    return PERSONAS.get(persona_key)


def compute_persona_relevance(
    signal: ProcessedSignal,
    persona_key: str,
    account_type: Optional[str] = None,
) -> float:
    """Score 0-1 how relevant a signal is for a specific persona.

    Scoring factors:
        1. Theme weight: boost signals matching the persona's priority themes
        2. Keyword boost: boost signals containing persona-relevant keywords
        3. Authority from preferred voice types (when account_type is known)

    Args:
        signal: A processed social signal.
        persona_key: One of "cto", "vc", "founder".
        account_type: Optional account type of the signal author
            (e.g., "founder", "vc"). Used for voice type matching.

    Returns:
        Relevance score clamped to 0-1.

    Raises:
        KeyError: If persona_key is not in PERSONAS.
    """
    if persona_key not in PERSONAS:
        raise KeyError(f"Unknown persona: {persona_key}. Valid: {list(PERSONAS.keys())}")

    persona = PERSONAS[persona_key]
    score = 0.0

    # 1. Theme weight: base engagement scaled by theme priority
    theme_boost = persona["themes_weight"].get(signal.theme, 1.0)
    likes = signal.post.metrics.get("likes", 0) if signal.post.metrics else 0
    score += min(0.4, likes * theme_boost * 0.01)

    # 2. Keyword boost: count keyword hits in signal text
    text_lower = signal.post.text.lower()
    keyword_hits = sum(1 for kw in persona["keywords_boost"] if kw in text_lower)
    score += keyword_hits * 0.15

    # 3. Authority from preferred voice types
    if account_type and account_type in persona["voice_types"]:
        score += 0.2

    # 4. Base authority contribution (always applies)
    score += signal.authority_score * 0.1

    return min(1.0, max(0.0, score))


def rank_signals_for_persona(
    signals: List[ProcessedSignal],
    persona_key: str,
    account_types: Optional[Dict[str, str]] = None,
) -> List[ProcessedSignal]:
    """Re-rank signals by persona relevance.

    Args:
        signals: List of processed signals to rank.
        persona_key: One of "cto", "vc", "founder".
        account_types: Optional mapping of author_handle -> account_type
            for voice type matching.

    Returns:
        Signals sorted by persona relevance (highest first).
    """
    if not signals:
        return []

    if account_types is None:
        account_types = {}

    scored = []
    for s in signals:
        acct_type = account_types.get(s.post.author_handle, None)
        relevance = compute_persona_relevance(s, persona_key, account_type=acct_type)
        scored.append((relevance, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored]


def compute_all_persona_scores(
    signal: ProcessedSignal,
    account_type: Optional[str] = None,
) -> Dict[str, float]:
    """Compute relevance scores for all personas at once.

    Useful for storing multi-persona scores in signal metadata.

    Args:
        signal: A processed social signal.
        account_type: Optional account type for voice type matching.

    Returns:
        Dict mapping persona_key -> relevance score.
    """
    return {
        key: compute_persona_relevance(signal, key, account_type=account_type)
        for key in PERSONAS
    }
