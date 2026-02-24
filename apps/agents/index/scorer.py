"""Scoring module for INDEX agent.

Computes a composite score for merged companies based on:
- Source count (more independent sources = higher confidence)
- Field completeness (more filled fields = higher quality)
- Receita Federal boost (government data = higher trust)
"""

import logging
from typing import Optional

from apps.agents.index.pipeline import MergedCompany

logger = logging.getLogger(__name__)

# Weights for composite score
SOURCE_COUNT_WEIGHT = 0.4
COMPLETENESS_WEIGHT = 0.35
CONFIDENCE_WEIGHT = 0.25

# Bonus for Receita Federal (government data)
RF_BOOST = 0.1

# Fields checked for completeness scoring
_COMPLETENESS_FIELDS = [
    "name", "website", "description", "sector", "city",
    "country", "cnpj", "domain", "founded_date", "team_size",
    "business_model", "github_url", "linkedin_url",
    "funding_stage", "total_funding_usd",
]


def _source_count_score(source_count: int) -> float:
    """Score based on number of independent sources.

    1 source = 0.3, 2 sources = 0.6, 3 sources = 0.8, 4+ = 0.95+
    """
    if source_count <= 0:
        return 0.1
    elif source_count == 1:
        return 0.3
    elif source_count == 2:
        return 0.6
    elif source_count == 3:
        return 0.8
    else:
        return min(0.85 + (source_count - 3) * 0.05, 1.0)


def _completeness_score(merged: MergedCompany) -> float:
    """Score based on how many fields are filled.

    Returns 0-1 ratio of non-empty fields to total fields checked.
    """
    filled = 0
    for field_name in _COMPLETENESS_FIELDS:
        value = getattr(merged, field_name, None)
        if value:
            filled += 1

    return filled / len(_COMPLETENESS_FIELDS)


def _has_receita_federal(merged: MergedCompany) -> bool:
    """Check if company has Receita Federal as a source."""
    return "receita_federal" in merged.sources


def score_company(merged: MergedCompany) -> float:
    """Compute composite score for a merged company.

    Formula:
        score = (source_score * 0.4) + (completeness * 0.35) + (confidence * 0.25) + RF_boost

    Args:
        merged: MergedCompany after pipeline merge.

    Returns:
        Float 0-1 composite score.
    """
    source_score = _source_count_score(merged.source_count)
    completeness = _completeness_score(merged)
    confidence = merged.best_confidence

    score = (
        source_score * SOURCE_COUNT_WEIGHT
        + completeness * COMPLETENESS_WEIGHT
        + confidence * CONFIDENCE_WEIGHT
    )

    # RF boost
    if _has_receita_federal(merged):
        score += RF_BOOST

    return round(min(score, 1.0), 3)


def score_all(companies: list[MergedCompany]) -> list[tuple[MergedCompany, float]]:
    """Score all merged companies and return sorted by score descending.

    Args:
        companies: List of MergedCompany objects.

    Returns:
        List of (MergedCompany, score) tuples sorted by score descending.
    """
    scored = [(company, score_company(company)) for company in companies]
    scored.sort(key=lambda x: x[1], reverse=True)

    if scored:
        logger.info(
            "Scored %d companies: top=%.3f, median=%.3f, bottom=%.3f",
            len(scored),
            scored[0][1],
            scored[len(scored) // 2][1],
            scored[-1][1],
        )

    return scored
