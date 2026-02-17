"""Editorial guidelines and content validation for Sinal.lab.

This package implements the editorial line defined in docs/EDITORIAL.md,
providing tools for:
- Territory classification
- Content quality validation
- Editorial guidelines enforcement
- Multi-criteria filtering

Usage:
    from packages.editorial import validate_content, classify_territory

    result = validate_content(content, metadata)
    if result.passes_editorial_bar:
        publish(content)
"""

from packages.editorial.validator import validate_content, ContentValidationResult
from packages.editorial.classifier import classify_territory, TerritoryClassification
from packages.editorial.guidelines import EDITORIAL_TERRITORIES, FILTER_CRITERIA

__all__ = [
    "validate_content",
    "ContentValidationResult",
    "classify_territory",
    "TerritoryClassification",
    "EDITORIAL_TERRITORIES",
    "FILTER_CRITERIA",
]
