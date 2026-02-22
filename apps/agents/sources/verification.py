"""Shared types for source verification metadata.

Provides verification levels and authority tracking for data sources
that come from regulatory filings, official APIs, or curated databases.
The "verified" distinction lives in the data (SourceAuthority field),
not in a class hierarchy — consistent with the function-based source pattern.

Usage:
    from apps.agents.sources.verification import (
        VerificationLevel,
        SourceAuthority,
        verified_dq_floor,
    )

    authority = SourceAuthority(
        verification_level=VerificationLevel.REGULATORY,
        institution_name="SEC",
        regulatory_id="CIK-0001234567",
    )
    floor = verified_dq_floor(VerificationLevel.REGULATORY)  # 0.85
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VerificationLevel(str, Enum):
    """How authoritative is the data source?

    REGULATORY: Government filings (SEC, BCB) — highest authority.
    OFFICIAL: Company or institution APIs with verified data.
    CURATED: Editorially maintained databases (Crunchbase, LinkedIn).
    COMMUNITY: User-contributed or scraped data (forums, job boards).
    """

    REGULATORY = "regulatory"
    OFFICIAL = "official"
    CURATED = "curated"
    COMMUNITY = "community"


# Minimum DQ score for each verification level.
# These floors ensure that regulatory data always scores higher than
# unverified community data, even with fewer sources.
_DQ_FLOORS: dict[VerificationLevel, float] = {
    VerificationLevel.REGULATORY: 0.85,
    VerificationLevel.OFFICIAL: 0.75,
    VerificationLevel.CURATED: 0.55,
    VerificationLevel.COMMUNITY: 0.35,
}


def verified_dq_floor(level: VerificationLevel) -> float:
    """Return the minimum DQ score for a given verification level.

    Args:
        level: The verification level of the source.

    Returns:
        Float between 0.35 and 0.85 representing the DQ floor.
    """
    return _DQ_FLOORS[level]


@dataclass
class SourceAuthority:
    """Verification metadata attached to each source item.

    Tracks the authority level of the data source, the institution
    that published it, and any regulatory identifiers.
    """

    verification_level: VerificationLevel
    institution_name: str
    regulatory_id: Optional[str] = None
    data_lag_days: int = 0
