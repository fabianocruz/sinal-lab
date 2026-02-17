"""Tests for Layer 1: PESQUISA — provenance validation."""

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.pesquisa import run_pesquisa
from apps.agents.editorial.models import FlagSeverity


def _make_output(**overrides) -> AgentOutput:
    """Create a valid AgentOutput with sensible defaults."""
    defaults = {
        "title": "Test Newsletter #1",
        "body_md": "This is a test body with enough words to pass the minimum threshold. " * 5,
        "agent_name": "sintese",
        "run_id": "sintese-20260215-abc123",
        "confidence": ConfidenceScore(
            data_quality=0.7,
            analysis_confidence=0.6,
            source_count=5,
            verified=True,
        ),
        "sources": [
            "https://techcrunch.com/rss",
            "https://github.com/trending",
            "https://news.ycombinator.com/rss",
        ],
        "summary": "Weekly digest of LATAM tech ecosystem.",
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


class TestPesquisaGradeA:
    """Grade A: complete provenance, multi-source, summary present."""

    def test_well_formed_output_gets_grade_a(self):
        output = _make_output()
        result = run_pesquisa(output)
        assert result.grade == "A"
        assert result.passed is True
        assert not result.has_blockers

    def test_metadata_includes_counts(self):
        output = _make_output()
        result = run_pesquisa(output)
        assert result.metadata["source_count"] == 5
        assert result.metadata["source_urls"] == 3
        assert result.metadata["word_count"] > 50


class TestPesquisaGradeB:
    """Grade B: good provenance, fewer sources."""

    def test_two_sources_no_summary(self):
        output = _make_output(
            confidence=ConfidenceScore(
                data_quality=0.6, analysis_confidence=0.5, source_count=2, verified=True,
            ),
            summary=None,
        )
        result = run_pesquisa(output)
        assert result.grade == "B"
        assert result.passed is True


class TestPesquisaGradeC:
    """Grade C: warnings or sparse provenance."""

    def test_single_source_gets_warning(self):
        output = _make_output(
            confidence=ConfidenceScore(
                data_quality=0.4, analysis_confidence=0.3, source_count=1,
            ),
        )
        result = run_pesquisa(output)
        assert result.grade == "C"
        warnings = [f for f in result.flags if f.severity == FlagSeverity.WARNING]
        assert len(warnings) >= 1

    def test_empty_source_url_gets_warning(self):
        output = _make_output(sources=["https://example.com", "", "https://other.com"])
        result = run_pesquisa(output)
        warnings = [f for f in result.flags if f.severity == FlagSeverity.WARNING]
        assert any("empty source" in f.message.lower() for f in warnings)


class TestPesquisaGradeD:
    """Grade D: blockers — missing critical provenance."""

    def test_empty_title_is_blocker(self):
        output = _make_output(title="")
        result = run_pesquisa(output)
        assert result.grade == "D"
        assert result.passed is False
        assert result.has_blockers

    def test_short_body_is_blocker(self):
        output = _make_output(body_md="Too short.")
        result = run_pesquisa(output)
        assert result.grade == "D"
        assert result.passed is False

    def test_no_sources_list_is_blocker(self):
        output = _make_output(sources=[])
        result = run_pesquisa(output)
        assert result.grade == "D"
        assert result.passed is False

    def test_very_low_confidence_is_blocker(self):
        output = _make_output(
            confidence=ConfidenceScore(
                data_quality=0.05, analysis_confidence=0.05, source_count=0,
            ),
        )
        result = run_pesquisa(output)
        assert result.grade == "D"
        blockers = [f for f in result.flags if f.severity == FlagSeverity.BLOCKER]
        assert len(blockers) >= 1

    def test_empty_agent_name_gets_error(self):
        output = _make_output(agent_name="")
        result = run_pesquisa(output)
        errors = [f for f in result.flags if f.severity == FlagSeverity.ERROR]
        assert any("agent name" in f.message.lower() for f in errors)

    def test_empty_run_id_gets_error(self):
        output = _make_output(run_id="")
        result = run_pesquisa(output)
        errors = [f for f in result.flags if f.severity == FlagSeverity.ERROR]
        assert any("run id" in f.message.lower() for f in errors)


class TestPesquisaLayerResult:
    def test_layer_name(self):
        output = _make_output()
        result = run_pesquisa(output)
        assert result.layer_name == "pesquisa"

    def test_result_is_serializable(self):
        output = _make_output()
        result = run_pesquisa(output)
        d = result.to_dict()
        assert "layer_name" in d
        assert "flags" in d
        assert isinstance(d["flags"], list)
