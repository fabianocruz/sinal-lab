"""Confidence scoring module for Sinal.lab agents.

Every agent output carries a confidence score with two dimensions:
    - data_quality (DQ): How reliable is the underlying data? (0-1)
    - analysis_confidence (AC): How reliable is the analysis/synthesis? (0-1)

Scores map to quality grades:
    0.0-0.3: Low (grade D) — single source, unverified
    0.3-0.6: Medium (grade C) — multiple signals, partially verified
    0.6-0.8: High (grade B) — multi-source verified, cross-validated
    0.8-1.0: Very high (grade A) — multi-source, expert-reviewed
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConfidenceScore:
    """A confidence score for a piece of agent output."""

    data_quality: float  # 0.0 to 1.0
    analysis_confidence: float  # 0.0 to 1.0
    source_count: int = 0
    verified: bool = False
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.data_quality <= 1.0:
            raise ValueError(f"data_quality must be 0-1, got {self.data_quality}")
        if not 0.0 <= self.analysis_confidence <= 1.0:
            raise ValueError(
                f"analysis_confidence must be 0-1, got {self.analysis_confidence}"
            )

    @property
    def composite(self) -> float:
        """Weighted composite score (DQ 60%, AC 40%)."""
        return round(self.data_quality * 0.6 + self.analysis_confidence * 0.4, 3)

    @property
    def grade(self) -> str:
        """Quality grade based on composite score."""
        score = self.composite
        if score >= 0.8:
            return "A"
        elif score >= 0.6:
            return "B"
        elif score >= 0.3:
            return "C"
        else:
            return "D"

    @property
    def dq_display(self) -> float:
        """Data quality on 1-5 scale (for display in content badges)."""
        return round(self.data_quality * 5, 1)

    @property
    def ac_display(self) -> float:
        """Analysis confidence on 1-5 scale (for display in content badges)."""
        return round(self.analysis_confidence * 5, 1)

    def to_dict(self) -> dict:
        """Serialize for storage and API responses."""
        return {
            "data_quality": self.data_quality,
            "analysis_confidence": self.analysis_confidence,
            "composite": self.composite,
            "grade": self.grade,
            "dq_display": self.dq_display,
            "ac_display": self.ac_display,
            "source_count": self.source_count,
            "verified": self.verified,
            "notes": self.notes,
        }


def compute_confidence(
    source_count: int,
    sources_verified: int = 0,
    data_freshness_days: int = 0,
    cross_validated: bool = False,
) -> ConfidenceScore:
    """Compute a confidence score from objective signals.

    Args:
        source_count: Number of independent sources for this data.
        sources_verified: Number of sources independently verified.
        data_freshness_days: Age of the data in days (0 = today).
        cross_validated: Whether data was validated across sources.

    Returns:
        A ConfidenceScore reflecting these inputs.
    """
    # Data quality: based on source count and verification
    if source_count == 0:
        dq = 0.1
    elif source_count == 1:
        dq = 0.3 + (0.1 if sources_verified >= 1 else 0.0)
    elif source_count == 2:
        dq = 0.5 + (0.15 if sources_verified >= 2 else 0.05)
    else:
        dq = min(0.7 + (source_count - 3) * 0.05, 0.95)

    if cross_validated:
        dq = min(dq + 0.1, 1.0)

    # Freshness penalty
    if data_freshness_days > 90:
        dq *= 0.7
    elif data_freshness_days > 30:
        dq *= 0.85

    # Analysis confidence: conservative baseline, improves with verification
    ac = min(dq * 0.9, 0.95)  # AC can't exceed DQ significantly

    return ConfidenceScore(
        data_quality=round(dq, 3),
        analysis_confidence=round(ac, 3),
        source_count=source_count,
        verified=sources_verified >= 2,
    )
