"""Tests for editorial pipeline data models."""

import pytest
from datetime import datetime, timezone

from apps.agents.editorial.models import (
    BiasMetrics,
    EditorialResult,
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)


class TestReviewFlag:
    def test_create_flag(self):
        flag = ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.DATA_QUALITY,
            message="Low confidence",
            layer="validacao",
        )
        assert flag.severity == FlagSeverity.WARNING
        assert flag.category == FlagCategory.DATA_QUALITY
        assert flag.detail is None

    def test_flag_to_dict(self):
        flag = ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.FACT_CHECK,
            message="Red flag",
            layer="verificacao",
            detail="Percentage exceeds 100",
        )
        d = flag.to_dict()
        assert d["severity"] == "blocker"
        assert d["category"] == "fact_check"
        assert d["detail"] == "Percentage exceeds 100"


class TestLayerResult:
    def test_no_blockers(self):
        result = LayerResult(
            layer_name="pesquisa",
            passed=True,
            grade="A",
            flags=[
                ReviewFlag(
                    severity=FlagSeverity.INFO,
                    category=FlagCategory.PROVENANCE,
                    message="info",
                    layer="pesquisa",
                ),
            ],
        )
        assert result.has_blockers is False
        assert result.warning_count == 0
        assert result.error_count == 0

    def test_has_blockers(self):
        result = LayerResult(
            layer_name="validacao",
            passed=False,
            grade="D",
            flags=[
                ReviewFlag(
                    severity=FlagSeverity.BLOCKER,
                    category=FlagCategory.DATA_QUALITY,
                    message="blocked",
                    layer="validacao",
                ),
                ReviewFlag(
                    severity=FlagSeverity.WARNING,
                    category=FlagCategory.DATA_QUALITY,
                    message="warn",
                    layer="validacao",
                ),
            ],
        )
        assert result.has_blockers is True
        assert result.warning_count == 1
        assert result.error_count == 0

    def test_to_dict(self):
        result = LayerResult(layer_name="test", passed=True, grade="B")
        d = result.to_dict()
        assert d["layer_name"] == "test"
        assert d["passed"] is True
        assert d["grade"] == "B"
        assert "executed_at" in d


class TestEditorialResult:
    def test_overall_grade_takes_lowest(self):
        result = EditorialResult(
            content_title="Test",
            agent_name="sintese",
            run_id="run-1",
            publish_ready=True,
            layer_results=[
                LayerResult(layer_name="l1", passed=True, grade="A"),
                LayerResult(layer_name="l2", passed=True, grade="B"),
                LayerResult(layer_name="l3", passed=True, grade="A"),
            ],
        )
        assert result.overall_grade == "B"

    def test_overall_grade_empty(self):
        result = EditorialResult(
            content_title="Test",
            agent_name="sintese",
            run_id="run-1",
            publish_ready=False,
        )
        assert result.overall_grade == "D"

    def test_blocker_count(self):
        result = EditorialResult(
            content_title="Test",
            agent_name="sintese",
            run_id="run-1",
            publish_ready=False,
            all_flags=[
                ReviewFlag(severity=FlagSeverity.BLOCKER, category=FlagCategory.PROVENANCE, message="a", layer="l1"),
                ReviewFlag(severity=FlagSeverity.WARNING, category=FlagCategory.PROVENANCE, message="b", layer="l1"),
                ReviewFlag(severity=FlagSeverity.BLOCKER, category=FlagCategory.FACT_CHECK, message="c", layer="l3"),
            ],
        )
        assert result.blocker_count == 2

    def test_to_dict(self):
        result = EditorialResult(
            content_title="Test",
            agent_name="test",
            run_id="run-x",
            publish_ready=True,
        )
        d = result.to_dict()
        assert d["content_title"] == "Test"
        assert d["publish_ready"] is True
        assert "reviewed_at" in d


class TestBiasMetrics:
    def test_to_dict(self):
        metrics = BiasMetrics(
            geographic_distribution={"Sao Paulo": 5, "Florianopolis": 2},
            sector_distribution={"fintech": 3, "ai": 4},
        )
        d = metrics.to_dict()
        assert d["geographic_distribution"]["Sao Paulo"] == 5
        assert d["sector_distribution"]["ai"] == 4


class TestFlagSeverityOrdering:
    def test_severity_values(self):
        assert FlagSeverity.INFO.value == "info"
        assert FlagSeverity.WARNING.value == "warning"
        assert FlagSeverity.ERROR.value == "error"
        assert FlagSeverity.BLOCKER.value == "blocker"

    def test_category_values(self):
        assert FlagCategory.PROVENANCE.value == "provenance"
        assert FlagCategory.BIAS.value == "bias"
        assert FlagCategory.SEO.value == "seo"
