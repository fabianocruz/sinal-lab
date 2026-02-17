"""Tests for the EditorialPipeline orchestrator."""

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.models import (
    EditorialResult,
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)
from apps.agents.editorial.pipeline import EditorialPipeline


def _make_output(**overrides) -> AgentOutput:
    """Create a well-formed AgentOutput."""
    defaults = {
        "title": "Sinal Semanal #42",
        "body_md": (
            "# Sinal Semanal #42\n\n"
            "This week we cover the latest in LATAM tech. "
            "Multiple startups announced funding rounds. "
            "The ecosystem continues to grow with new developer tools. "
            "AI adoption is accelerating across the region. " * 5
        ),
        "agent_name": "sintese",
        "run_id": "sintese-20260215-pipe01",
        "confidence": ConfidenceScore(
            data_quality=0.75,
            analysis_confidence=0.65,
            source_count=8,
            verified=True,
        ),
        "sources": [
            "https://techcrunch.com/feed",
            "https://news.ycombinator.com/rss",
            "https://github.com/trending",
        ],
        "summary": "Weekly digest covering LATAM tech ecosystem trends.",
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


class TestPipelineHappyPath:
    """Well-formed output should pass all layers."""

    def test_clean_output_is_publish_ready(self):
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        assert result.publish_ready is True
        assert result.blocker_count == 0
        assert len(result.layer_results) == 6  # all 6 layers
        assert result.content_title == "Sinal Semanal #42"
        assert result.agent_name == "sintese"

    def test_all_six_layers_run(self):
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        layer_names = [lr.layer_name for lr in result.layer_results]
        assert layer_names == ["pesquisa", "validacao", "verificacao", "vies", "seo", "sintese_final"]

    def test_all_layers_pass(self):
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        for lr in result.layer_results:
            assert lr.passed is True, f"Layer {lr.layer_name} failed unexpectedly"

    def test_overall_grade_reflects_layers(self):
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        assert result.overall_grade in ("A", "B")

    def test_byline_populated(self):
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        assert result.byline is not None
        assert "SINTESE" in result.byline


class TestPipelineHaltOnBlocker:
    """Pipeline should halt when a layer produces a blocker."""

    def test_halts_at_pesquisa_on_empty_title(self):
        pipeline = EditorialPipeline(halt_on_blocker=True)
        output = _make_output(title="")
        result = pipeline.review(output)

        assert result.publish_ready is False
        # Should halt at pesquisa (layer 1) — only 1 layer result, no sintese_final
        assert len(result.layer_results) == 1
        assert result.layer_results[0].layer_name == "pesquisa"
        assert result.layer_results[0].has_blockers

    def test_halts_at_validacao_on_low_dq(self):
        pipeline = EditorialPipeline(halt_on_blocker=True)
        output = _make_output(
            confidence=ConfidenceScore(
                data_quality=0.2,
                analysis_confidence=0.15,
                source_count=1,
            ),
        )
        result = pipeline.review(output)

        assert result.publish_ready is False
        # Should halt at validacao (layer 2)
        assert len(result.layer_results) <= 2
        assert result.blocker_count >= 1

    def test_no_halt_when_disabled(self):
        pipeline = EditorialPipeline(halt_on_blocker=False)
        output = _make_output(title="")
        result = pipeline.review(output)

        # All 6 layers should run even with blockers (5 chain + sintese_final)
        assert len(result.layer_results) == 6
        assert result.publish_ready is False


class TestPipelineBlockerPropagation:
    """Blocker flags from any layer should affect the final result."""

    def test_blocker_in_any_layer_means_not_publish_ready(self):
        pipeline = EditorialPipeline(halt_on_blocker=False)
        output = _make_output(
            body_md="The startup raised $50M. " * 10,
            confidence=ConfidenceScore(
                data_quality=0.5,
                analysis_confidence=0.4,
                source_count=1,
            ),
        )
        result = pipeline.review(output)

        assert result.publish_ready is False
        # Financial claim + single source = blocker from validacao
        blockers = [f for f in result.all_flags if f.severity == FlagSeverity.BLOCKER]
        assert len(blockers) >= 1

    def test_all_flags_accumulated(self):
        pipeline = EditorialPipeline(halt_on_blocker=False)
        output = _make_output()
        result = pipeline.review(output)

        # Flags from all layers should be in all_flags
        layer_flag_count = sum(len(lr.flags) for lr in result.layer_results)
        assert len(result.all_flags) == layer_flag_count


class TestPipelineLayerRegistration:
    """Custom layers can be registered dynamically."""

    def test_register_custom_layer(self):
        pipeline = EditorialPipeline()
        initial_count = len(pipeline.get_layer_names())

        def custom_layer(output: AgentOutput) -> LayerResult:
            return LayerResult(layer_name="custom", passed=True, grade="A")

        pipeline.register_layer("custom", custom_layer)
        assert len(pipeline.get_layer_names()) == initial_count + 1
        assert "custom" in pipeline.get_layer_names()

    def test_custom_layer_runs_in_pipeline(self):
        pipeline = EditorialPipeline()

        def custom_layer(output: AgentOutput) -> LayerResult:
            return LayerResult(
                layer_name="custom",
                passed=True,
                grade="B",
                flags=[ReviewFlag(
                    severity=FlagSeverity.INFO,
                    category=FlagCategory.EDITORIAL,
                    message="Custom check passed",
                    layer="custom",
                )],
            )

        pipeline.register_layer("custom", custom_layer)
        output = _make_output()
        result = pipeline.review(output)

        layer_names = [lr.layer_name for lr in result.layer_results]
        assert "custom" in layer_names
        assert any(f.message == "Custom check passed" for f in result.all_flags)


class TestPipelineEdgeCases:
    """Edge cases and error handling."""

    def test_empty_body_halts_at_pesquisa(self):
        pipeline = EditorialPipeline()
        output = _make_output(body_md="")
        result = pipeline.review(output)

        assert result.publish_ready is False
        assert len(result.layer_results) == 1

    def test_no_sources_halts_at_pesquisa(self):
        pipeline = EditorialPipeline()
        output = _make_output(sources=[])
        result = pipeline.review(output)

        assert result.publish_ready is False

    def test_result_is_serializable(self):
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        d = result.to_dict()
        assert isinstance(d, dict)
        assert "layer_results" in d
        assert "all_flags" in d
        assert "publish_ready" in d

    def test_get_layer_names(self):
        pipeline = EditorialPipeline()
        names = pipeline.get_layer_names()
        assert names == ["pesquisa", "validacao", "verificacao", "vies", "seo", "sintese_final"]
