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
    """Create a well-formed AgentOutput.

    Body content must satisfy guidelines layer criteria:
    has_data (numbers + sources), actionable (decision-relevant),
    latam_angle (Brazil/LATAM context), aligns_territory (fintech/AI).
    """
    defaults = {
        "title": "Sinal Semanal #42 — Pix institucional cresce 47% e fintechs ajustam open finance",
        "body_md": (
            "# Sinal Semanal #42\n\n"
            "Esta semana o Pix institucional alcançou R$ 312 bilhões em volume mensal, "
            "alta de 47% no Brasil segundo dados do Banco Central. Para CTOs de fintechs "
            "brasileiras, três decisões ficam óbvias: (1) revisar limites de rate limiting "
            "nos endpoints de Pix antes do pico de novembro; (2) priorizar observabilidade "
            "de fraude com latência sub-200ms; (3) avaliar custo de open finance com 12 "
            "instituições conectadas. No México, a CNBV publicou 8 novas regras de KYC para "
            "stablecoins; na Colômbia, Bre-B (Pix colombiano) entrou em produção com 4 bancos.\n\n"
            "O ecossistema de developer tools cresceu 22% em adoção LATAM segundo o Stack "
            "Overflow Survey 2026, com Claude Code e Cursor liderando entre desenvolvedores "
            "brasileiros (38% e 27% respectivamente). Fundadores devem reavaliar seu stack: "
            "ferramentas de AI agentic já economizam 14 horas/semana por engenheiro sênior. " * 2
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
        "summary": (
            "Pix institucional alcança R$ 312 bilhões e fintechs LATAM revisam open finance. "
            "Análise para CTOs no Brasil, México e Colômbia."
        ),
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
        assert len(result.layer_results) == 7  # 6 review layers + sintese_final
        assert result.content_title.startswith("Sinal Semanal #42")
        assert result.agent_name == "sintese"

    def test_all_six_layers_run(self):
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        layer_names = [lr.layer_name for lr in result.layer_results]
        assert layer_names == [
            "pesquisa", "validacao", "verificacao",
            "guidelines", "vies", "seo", "sintese_final",
        ]

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

        # All 7 layers should run even with blockers (6 chain + sintese_final)
        assert len(result.layer_results) == 7
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
        assert names == [
            "pesquisa", "validacao", "verificacao",
            "guidelines", "vies", "seo", "sintese_final",
        ]


class TestDataAgentWarning:
    """Data agent outputs should trigger a warning when entering editorial pipeline."""

    def test_data_agent_gets_warning_flag(self):
        """Output from a DATA agent should receive a WARNING flag."""
        pipeline = EditorialPipeline()
        output = _make_output(agent_name="funding", agent_category="data")
        result = pipeline.review(output)

        data_warnings = [
            f for f in result.all_flags
            if f.severity == FlagSeverity.WARNING
            and "data" in f.message.lower()
        ]
        assert len(data_warnings) >= 1

    def test_data_agent_warning_does_not_block(self):
        """Data agent warning should NOT prevent publication."""
        pipeline = EditorialPipeline()
        output = _make_output(agent_name="mercado", agent_category="data")
        result = pipeline.review(output)

        # The warning alone should not block — other layers determine publish_ready
        data_blockers = [
            f for f in result.all_flags
            if f.severity == FlagSeverity.BLOCKER
            and "data" in f.message.lower()
            and "agent" in f.message.lower()
        ]
        assert len(data_blockers) == 0

    def test_content_agent_no_data_warning(self):
        """Output from a CONTENT agent should NOT get the data agent warning."""
        pipeline = EditorialPipeline()
        output = _make_output(agent_name="sintese", agent_category="content")
        result = pipeline.review(output)

        data_warnings = [
            f for f in result.all_flags
            if "data" in f.message.lower()
            and "agent" in f.message.lower()
            and f.layer == "pipeline"
        ]
        assert len(data_warnings) == 0

    def test_default_category_no_warning(self):
        """Output without explicit agent_category (default 'content') should NOT warn."""
        pipeline = EditorialPipeline()
        output = _make_output()  # default agent_category="content"
        result = pipeline.review(output)

        data_warnings = [
            f for f in result.all_flags
            if f.layer == "pipeline"
            and "data" in f.message.lower()
        ]
        assert len(data_warnings) == 0
