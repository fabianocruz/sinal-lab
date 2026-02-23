"""Territory classification for AI-generated content.

This module implements keyword-based classification to assign content to one of
4 editorial territories defined in guidelines.py. It's used by AI agents to
automatically categorize their outputs before editorial review.

Classification Algorithm:
    1. Extract and normalize content + title text (title weighted 2x)
    2. Count keyword matches per territory using word-boundary regex
    3. Identify primary territory (highest match count)
    4. Calculate confidence score (normalized by content length)
    5. Identify secondary territories (≥30% of primary score)
    6. Flag regulatory content (meta-territory)

Key Features:
    - Title gets 2x weight in classification (counted twice)
    - Case-insensitive keyword matching with word boundaries
    - Confidence score scales with content length (prevents short-content bias)
    - Secondary territories capture multi-domain content
    - Regulatory flag for cross-cutting compliance content

Confidence Scoring:
    confidence = min(1.0, matches / (words / 100))
    - Short content (50 words) needs 5+ matches for 1.0 confidence
    - Long content (500 words) needs 50+ matches for 1.0 confidence

Usage:
    >>> from packages.editorial.classifier import classify_territory
    >>> result = classify_territory(
    ...     title="Pix alcança 3 bilhões de transações mensais",
    ...     content="O volume de Pix cresceu 45% no Brasil..."
    ... )
    >>> print(result.primary_territory)
    'fintech'
    >>> print(result.confidence)
    0.92

Integration Points:
    - Called by AI agents before saving output
    - Used in validate_content() to check territory alignment
    - Feeds territory_classification field in agent outputs

See Also:
    - guidelines.py: Territory definitions and keyword lists
    - validator.py: Uses classification in validation pipeline
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re

from packages.editorial.guidelines import (
    EDITORIAL_TERRITORIES,
    REGULATORY_KEYWORDS,
    get_territory_keywords,
)


@dataclass
class TerritoryClassification:
    """Result of territory classification."""

    primary_territory: str
    confidence: float  # 0.0 to 1.0
    secondary_territories: List[str]
    is_regulatory: bool
    keyword_matches: Dict[str, int]  # territory -> match count

    def to_dict(self) -> dict:
        return {
            "primary_territory": self.primary_territory,
            "confidence": self.confidence,
            "secondary_territories": self.secondary_territories,
            "is_regulatory": self.is_regulatory,
            "keyword_matches": self.keyword_matches,
        }


def classify_territory(
    content: str,
    title: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> TerritoryClassification:
    """Classify content into editorial territories.

    Uses keyword matching with weighted scoring. Title gets 2x weight.

    Args:
        content: The full text content to classify
        title: Optional title (gets higher weight in classification)
        metadata: Optional metadata dict (can include tags, categories, etc.)

    Returns:
        TerritoryClassification with primary territory and confidence

    Example:
        >>> result = classify_territory(
        ...     title="Pix alcança 3 bilhões de transações mensais",
        ...     content="O volume de Pix cresceu 45% no último trimestre..."
        ... )
        >>> result.primary_territory
        'fintech'
        >>> result.confidence
        0.92
    """
    # Normalize text for matching
    full_text = ""
    if title:
        full_text += title.lower() + " " + title.lower()  # Title counts 2x
    full_text += " " + content.lower()

    # Count keyword matches per territory
    territory_scores: Dict[str, int] = {}

    for territory_key in EDITORIAL_TERRITORIES.keys():
        keywords = get_territory_keywords(territory_key)
        matches = 0

        for keyword in keywords:
            # Use word boundary to avoid partial matches
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            count = len(re.findall(pattern, full_text))
            matches += count

        territory_scores[territory_key] = matches

    # Check for regulatory content (meta-territory)
    regulatory_matches = sum(
        len(re.findall(r'\b' + re.escape(kw.lower()) + r'\b', full_text))
        for kw in REGULATORY_KEYWORDS
    )
    is_regulatory = regulatory_matches >= 3

    # Find primary territory (highest score)
    if not territory_scores or max(territory_scores.values()) == 0:
        # No matches - default to most general territory
        return TerritoryClassification(
            primary_territory="unknown",
            confidence=0.0,
            secondary_territories=[],
            is_regulatory=is_regulatory,
            keyword_matches=territory_scores,
        )

    sorted_territories = sorted(
        territory_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    primary_territory = sorted_territories[0][0]
    primary_score = sorted_territories[0][1]

    # Secondary territories (score >= 30% of primary)
    threshold = primary_score * 0.3
    secondary_territories = [
        t for t, score in sorted_territories[1:]
        if score >= threshold
    ]

    # Calculate confidence (normalized by content length)
    content_words = len(full_text.split())
    # Confidence = matches / (content_words / 100), capped at 1.0
    if content_words > 0:
        confidence = min(1.0, (primary_score / (content_words / 100)))
    else:
        confidence = 0.0

    return TerritoryClassification(
        primary_territory=primary_territory,
        confidence=confidence,
        secondary_territories=secondary_territories,
        is_regulatory=is_regulatory,
        keyword_matches=territory_scores,
    )


def get_territory_display_name(territory_key: str) -> str:
    """Get human-readable name for territory."""
    return EDITORIAL_TERRITORIES.get(territory_key, {}).get("name", territory_key)
