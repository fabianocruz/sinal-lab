"""Tests for Layer 6: SINTESE_FINAL — editorial synthesis."""

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.sintese_final import run_sintese_final
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)


def _make_output(**overrides) -> AgentOutput:
    defaults = {
        "title": "Test Content",
        "body_md": "Content body. " * 20,
        "agent_name": "radar",
        "run_id": "radar-20260215-final01",
        "confidence": ConfidenceScore(
            data_quality=0.7, analysis_confidence=0.6, source_count=5, verified=True,
        ),
        "sources": ["https://source1.com", "https://source2.com"],
        "content_type": "DATA_REPORT",
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


def _make_prior_results(all_passed=True) -> list:
    """Create mock prior layer results."""
    results = [
        LayerResult(layer_name="pesquisa", passed=True, grade="A"),
        LayerResult(layer_name="validacao", passed=True, grade="B"),
        LayerResult(layer_name="verificacao", passed=True, grade="A"),
        LayerResult(layer_name="vies", passed=True, grade="A"),
        LayerResult(layer_name="seo", passed=True, grade="B"),
    ]
    if not all_passed:
        results[1] = LayerResult(
            layer_name="validacao",
            passed=False,
            grade="D",
            flags=[ReviewFlag(
                severity=FlagSeverity.BLOCKER,
                category=FlagCategory.DATA_QUALITY,
                message="DQ too low",
                layer="validacao",
            )],
        )
    return results


class TestByline:
    def test_generates_byline(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        assert "byline" in result.modifications
        assert "RADAR" in result.modifications["byline"]
        assert "pipeline editorial" in result.modifications["byline"].lower()

    def test_byline_uses_agent_name(self):
        output = _make_output(agent_name="sintese")
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        assert "SINTESE" in result.modifications["byline"]


class TestConfidenceBadge:
    def test_badge_data_present(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        badge = result.metadata["confidence_badge"]
        assert "data_quality" in badge
        assert "analysis_confidence" in badge
        assert "grade" in badge
        assert badge["grade"] in ("A", "B", "C", "D")

    def test_badge_values_match_output(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        badge = result.metadata["confidence_badge"]
        assert badge["data_quality"] == output.confidence.dq_display
        assert badge["source_count"] == output.confidence.source_count


class TestSourceList:
    def test_source_list_formatted(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        source_list = result.modifications["source_list"]
        assert len(source_list) == 2
        assert source_list[0]["index"] == 1
        assert source_list[0]["url"] == "https://source1.com"


class TestRevisionHistory:
    def test_revision_entry_created(self):
        output = _make_output()
        priors = _make_prior_results()
        result = run_sintese_final(output, prior_layer_results=priors)
        history = result.metadata["revision_history"]
        assert len(history) == 1
        assert history[0]["action"] == "editorial_review"
        assert history[0]["overall_passed"] is True
        assert len(history[0]["layers_run"]) == 5


class TestContentTypeReview:
    def test_data_report_no_extra_review(self):
        output = _make_output(content_type="DATA_REPORT")
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        editorial_flags = [f for f in result.flags if "human editorial review" in f.message.lower()]
        assert len(editorial_flags) == 0

    def test_analysis_requires_review(self):
        output = _make_output(content_type="ANALYSIS")
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        editorial_flags = [f for f in result.flags if "human editorial review" in f.message.lower()]
        assert len(editorial_flags) == 1
        assert editorial_flags[0].severity == FlagSeverity.WARNING

    def test_opinion_requires_review(self):
        output = _make_output(content_type="OPINION")
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        editorial_flags = [f for f in result.flags if "human editorial review" in f.message.lower()]
        assert len(editorial_flags) >= 1


class TestPriorBlockerDetection:
    def test_prior_blockers_escalated(self):
        output = _make_output()
        priors = _make_prior_results(all_passed=False)
        result = run_sintese_final(output, prior_layer_results=priors)
        assert result.passed is False
        blockers = [f for f in result.flags if f.severity == FlagSeverity.BLOCKER]
        assert len(blockers) >= 1

    def test_no_prior_blockers_passes(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        assert result.passed is True


class TestSinteseFinalIntegration:
    def test_layer_name(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        assert result.layer_name == "sintese_final"

    def test_grade_with_all_passing(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        assert result.grade in ("A", "B")

    def test_grade_d_with_blockers(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results(all_passed=False))
        assert result.grade == "D"

    def test_no_prior_results_handled(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=None)
        assert result.layer_name == "sintese_final"

    def test_publish_ready_metadata(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        assert result.metadata["publish_ready"] is True
        assert result.metadata["all_prior_layers_passed"] is True

    def test_serializable(self):
        output = _make_output()
        result = run_sintese_final(output, prior_layer_results=_make_prior_results())
        d = result.to_dict()
        assert "metadata" in d
