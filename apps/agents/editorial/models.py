"""Data models for the editorial governance pipeline.

Defines the structures that flow between editorial layers and
accumulate into the final editorial review result.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class FlagSeverity(str, Enum):
    """Severity levels for editorial review flags."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


class FlagCategory(str, Enum):
    """Categories that flags belong to."""

    PROVENANCE = "provenance"
    DATA_QUALITY = "data_quality"
    FACT_CHECK = "fact_check"
    BIAS = "bias"
    SEO = "seo"
    EDITORIAL = "editorial"


@dataclass
class ReviewFlag:
    """A flag raised during editorial review."""

    severity: FlagSeverity
    category: FlagCategory
    message: str
    layer: str
    detail: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "layer": self.layer,
            "detail": self.detail,
        }


@dataclass
class LayerResult:
    """Result from a single editorial pipeline layer."""

    layer_name: str
    passed: bool
    grade: str  # A, B, C, D
    flags: list[ReviewFlag] = field(default_factory=list)
    modifications: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_blockers(self) -> bool:
        return any(f.severity == FlagSeverity.BLOCKER for f in self.flags)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.flags if f.severity == FlagSeverity.WARNING)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.flags if f.severity == FlagSeverity.ERROR)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "passed": self.passed,
            "grade": self.grade,
            "flags": [f.to_dict() for f in self.flags],
            "modifications": self.modifications,
            "metadata": self.metadata,
            "executed_at": self.executed_at.isoformat(),
        }


@dataclass
class BiasMetrics:
    """Distribution metrics computed by the VIES (bias) layer."""

    geographic_distribution: dict[str, int] = field(default_factory=dict)
    sector_distribution: dict[str, int] = field(default_factory=dict)
    source_distribution: dict[str, int] = field(default_factory=dict)
    recency_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "geographic_distribution": self.geographic_distribution,
            "sector_distribution": self.sector_distribution,
            "source_distribution": self.source_distribution,
            "recency_distribution": self.recency_distribution,
        }


@dataclass
class EditorialResult:
    """Final result of the full editorial pipeline."""

    content_title: str
    agent_name: str
    run_id: str
    publish_ready: bool
    layer_results: list[LayerResult] = field(default_factory=list)
    all_flags: list[ReviewFlag] = field(default_factory=list)
    modified_body_md: Optional[str] = None
    modified_title: Optional[str] = None
    seo_metadata: dict[str, Any] = field(default_factory=dict)
    byline: Optional[str] = None
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def blocker_count(self) -> int:
        return sum(1 for f in self.all_flags if f.severity == FlagSeverity.BLOCKER)

    @property
    def overall_grade(self) -> str:
        """Lowest grade across all layers."""
        if not self.layer_results:
            return "D"
        grade_order = {"A": 4, "B": 3, "C": 2, "D": 1}
        min_grade_val = min(grade_order.get(lr.grade, 0) for lr in self.layer_results)
        reverse = {4: "A", 3: "B", 2: "C", 1: "D"}
        return reverse.get(min_grade_val, "D")

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_title": self.content_title,
            "agent_name": self.agent_name,
            "run_id": self.run_id,
            "publish_ready": self.publish_ready,
            "overall_grade": self.overall_grade,
            "blocker_count": self.blocker_count,
            "layer_results": [lr.to_dict() for lr in self.layer_results],
            "all_flags": [f.to_dict() for f in self.all_flags],
            "modified_title": self.modified_title,
            "seo_metadata": self.seo_metadata,
            "byline": self.byline,
            "reviewed_at": self.reviewed_at.isoformat(),
        }
