"""Confidence scoring for MERCADO agent.

Scores company profiles based on field completeness and source verification.
"""

import logging
from dataclasses import dataclass

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.mercado.collector import CompanyProfile

logger = logging.getLogger(__name__)


@dataclass
class ScoredCompanyProfile:
    """Company profile with confidence score."""

    profile: CompanyProfile
    confidence: ConfidenceScore
    composite_score: float


def compute_field_completeness(profile: CompanyProfile) -> float:
    """Compute field completeness score (0-1).

    Args:
        profile: CompanyProfile to evaluate

    Returns:
        Completeness score from 0.0 (empty) to 1.0 (all fields filled)
    """
    total_fields = 12
    filled_fields = 0

    if profile.name:
        filled_fields += 1
    if profile.slug:
        filled_fields += 1
    if profile.website:
        filled_fields += 1
    if profile.description:
        filled_fields += 1
    if profile.sector:
        filled_fields += 1
    if profile.city:
        filled_fields += 1
    if profile.country:
        filled_fields += 1
    if profile.founded_date:
        filled_fields += 1
    if profile.team_size:
        filled_fields += 1
    if profile.linkedin_url:
        filled_fields += 1
    if profile.github_url:
        filled_fields += 1
    if profile.tech_stack:
        filled_fields += 1

    return filled_fields / total_fields


def score_single_profile(profile: CompanyProfile) -> ScoredCompanyProfile:
    """Score a single company profile for confidence.

    Scoring criteria:
    - Data Quality (DQ): Field completeness + source verification
    - Analysis Confidence (AC): Sector classification accuracy

    Args:
        profile: CompanyProfile to score

    Returns:
        ScoredCompanyProfile with confidence scores
    """
    # Data Quality: based on field completeness
    completeness = compute_field_completeness(profile)
    dq = completeness

    # Boost DQ if from API source (more reliable)
    if "api" in profile.source_name or "dealroom" in profile.source_name:
        dq = min(1.0, dq * 1.2)

    # Penalize if missing critical fields
    if not profile.description:
        dq *= 0.7
    if not profile.sector:
        dq *= 0.9

    # Regulatory floor for BCB-verified institutions
    # Applied AFTER penalties so the floor is a true minimum
    if "bcb" in profile.source_name:
        from apps.agents.sources.verification import VerificationLevel, verified_dq_floor
        regulatory_floor = verified_dq_floor(VerificationLevel.REGULATORY)
        dq = max(dq, regulatory_floor)

    # Analysis Confidence: sector classification quality
    ac = 0.6  # Baseline for keyword-based classification

    if profile.sector:
        ac = 0.7  # Has sector classification
    if profile.description and len(profile.description) > 100:
        ac = min(1.0, ac * 1.1)  # More description = more confidence

    confidence = ConfidenceScore(data_quality=dq, analysis_confidence=ac)
    composite = (dq + ac) / 2

    return ScoredCompanyProfile(
        profile=profile,
        confidence=confidence,
        composite_score=composite,
    )


def score_all_profiles(profiles: list[CompanyProfile]) -> list[ScoredCompanyProfile]:
    """Score all company profiles for confidence.

    Args:
        profiles: List of CompanyProfile objects

    Returns:
        List of ScoredCompanyProfile objects sorted by confidence (highest first)
    """
    scored = [score_single_profile(p) for p in profiles]

    # Sort by composite score (highest first)
    scored.sort(key=lambda x: x.composite_score, reverse=True)

    avg_confidence = sum(s.composite_score for s in scored) / len(scored) if scored else 0.0
    logger.info(
        "Scored %d profiles with average confidence: %.2f",
        len(scored),
        avg_confidence,
    )

    return scored
