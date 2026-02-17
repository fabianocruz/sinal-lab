"""Tests for GuidelinesPack integration into the editorial pipeline.

These tests verify that the guidelines layer can be registered in the
pipeline and produces appropriate flags based on content quality.
"""

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.guidelines import run_guidelines
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
)
from apps.agents.editorial.pipeline import EditorialPipeline


def _make_output(**overrides) -> AgentOutput:
    """Create a well-formed AgentOutput."""
    defaults = {
        "title": "Pix alcança 3 bilhões de transações no Brasil",
        "body_md": (
            "Análise original do crescimento do Pix no Brasil: dados exclusivos "
            "mostram que o volume de transações Pix cresceu 45% no último trimestre, "
            "segundo dados do Banco Central do Brasil. O Nubank e o Mercado Pago "
            "lideram adoção na América Latina. Como implementar Pix em sua fintech: "
            "guia com benchmark de custos e comparativo com boleto. Dados de 2026 "
            "mostram 3.5 bilhões de transações mensais. A análise compara Brasil "
            "vs México vs Argentina em adoção de pagamentos digitais. Fonte: BCB, "
            "relatório mensal de estatísticas do Pix. Metodologia: agregação de "
            "dados públicos do BCB com pesquisa própria junto a 50 fintechs. "
            "ROI médio de implementação: 3 meses para fintechs em São Paulo. "
            + "Dados complementares incluem análise setorial detalhada. " * 50
        ),
        "agent_name": "sintese",
        "run_id": "sintese-20260215-guide01",
        "confidence": ConfidenceScore(
            data_quality=0.75,
            analysis_confidence=0.65,
            source_count=8,
            verified=True,
        ),
        "sources": [
            "https://bcb.gov.br/pix",
            "https://nubank.com.br",
            "https://mercadopago.com",
        ],
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


class TestGuidelinesLayerFunction:
    """Test the run_guidelines layer function directly."""

    def test_returns_layer_result(self) -> None:
        output = _make_output()
        result = run_guidelines(output)
        assert isinstance(result, LayerResult)
        assert result.layer_name == "guidelines"

    def test_good_content_passes(self) -> None:
        output = _make_output()
        result = run_guidelines(output)
        assert result.passed is True

    def test_bad_content_fails(self) -> None:
        output = _make_output(
            title="Tech Trends",
            body_md="Generic article about Silicon Valley tech trends.",
            sources=[],
        )
        result = run_guidelines(output)
        assert result.passed is False

    def test_red_flag_adds_blocker(self) -> None:
        output = _make_output(
            title="XYZ Announcement",
            body_md=(
                "Press release: Empresa XYZ tem o prazer de anunciar sua nova "
                "plataforma revolucionária que vai mudar tudo no mercado."
            ),
            sources=[],
        )
        result = run_guidelines(output)
        assert result.passed is False
        blockers = [f for f in result.flags if f.severity == FlagSeverity.BLOCKER]
        assert len(blockers) >= 1

    def test_guidelines_failure_adds_warning(self) -> None:
        output = _make_output(
            title="Short Note",
            body_md="Brief content about something. " * 5,
            sources=[],
        )
        result = run_guidelines(output)
        assert result.passed is False
        warnings = [f for f in result.flags if f.severity == FlagSeverity.WARNING]
        assert len(warnings) >= 1

    def test_metadata_includes_territory(self) -> None:
        output = _make_output()
        result = run_guidelines(output)
        assert "territory" in result.metadata
        assert "score" in result.metadata


class TestPipelineWithGuidelines:
    """Test guidelines layer registered in the pipeline."""

    def test_guidelines_layer_runs_in_pipeline(self) -> None:
        pipeline = EditorialPipeline()
        pipeline.register_layer("guidelines", run_guidelines)
        output = _make_output()
        result = pipeline.review(output)

        layer_names = [lr.layer_name for lr in result.layer_results]
        assert "guidelines" in layer_names

    def test_pipeline_without_guidelines_unchanged(self) -> None:
        """Default pipeline should NOT include guidelines layer."""
        pipeline = EditorialPipeline()
        output = _make_output()
        result = pipeline.review(output)

        layer_names = [lr.layer_name for lr in result.layer_results]
        assert "guidelines" not in layer_names
        assert len(layer_names) == 6  # Original 6 layers
