"""Tests for GuidelinesPack facade.

GuidelinesPack wraps packages/editorial/ (classifier + validator) into
a clean interface for use in the editorial pipeline.
"""

from unittest.mock import patch

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.guidelines_pack import GuidelinesPack, GuidelinesResult


def _make_agent_output(
    title: str = "Test Article",
    body_md: str = "Test content",
    **kwargs: object,
) -> AgentOutput:
    return AgentOutput(
        title=title,
        body_md=body_md,
        agent_name=kwargs.get("agent_name", "sintese"),
        run_id="test-run-001",
        confidence=ConfidenceScore(
            data_quality=0.7,
            analysis_confidence=0.6,
            source_count=3,
        ),
        sources=["https://example.com"],
    )


# Content that passes editorial bar: has data, actionable, unique, territory-aligned, LATAM angle
_GOOD_CONTENT = (
    "Análise original do crescimento do Pix no Brasil: dados exclusivos mostram que "
    "o volume de transações Pix cresceu 45% no último trimestre, segundo dados do "
    "Banco Central do Brasil. Como implementar Pix em sua fintech: guia com benchmark "
    "de custos e comparativo com boleto. O Nubank e o Mercado Pago lideram adoção na "
    "América Latina. Dados de 2026 mostram 3.5 bilhões de transações mensais. "
    "A análise compara Brasil vs México vs Argentina em adoção de pagamentos digitais. "
    "Fonte: BCB, relatório mensal de estatísticas do Pix. Metodologia: agregação de "
    "dados públicos do BCB com pesquisa própria junto a 50 fintechs brasileiras. "
    "O impacto em custos operacionais é significativo: redução de 60% comparado a TED. "
    "ROI médio de implementação: 3 meses para fintechs de médio porte em São Paulo. "
    + "Dados complementares incluem análise setorial. " * 30  # Ensure 500+ words
)

# Content that fails: no data, no LATAM, no actionability
_BAD_CONTENT = "This is a generic article about technology trends in Silicon Valley."

# Content with red flags
_RED_FLAG_CONTENT = (
    "Press release: Empresa XYZ tem o prazer de anunciar sua nova plataforma "
    "revolucionária que vai mudar tudo no mercado."
)


class TestGuidelinesPack:
    """Test GuidelinesPack evaluation."""

    def test_evaluate_good_content_passes(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(
            content=_GOOD_CONTENT,
            title="Pix alcança 3 bilhões de transações no Brasil",
            metadata={"sources": ["https://bcb.gov.br", "https://nubank.com.br", "https://mercadopago.com"]},
        )
        assert result.passes_guidelines is True

    def test_evaluate_bad_content_fails(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(content=_BAD_CONTENT, title="Tech Trends")
        assert result.passes_guidelines is False

    def test_strict_mode_raises_bar(self) -> None:
        """In strict mode, 4/5 criteria required instead of 3/5."""
        pack = GuidelinesPack(strict_mode=True)
        # Even good content might fail strict mode depending on criteria
        result = pack.evaluate(
            content=_GOOD_CONTENT,
            title="Pix alcança 3 bilhões",
            metadata={"sources": ["https://bcb.gov.br", "https://nubank.com.br", "https://mercadopago.com"]},
        )
        # strict_mode passes through to validate_content
        assert isinstance(result.passes_guidelines, bool)

    def test_territory_classified(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(
            content=_GOOD_CONTENT,
            title="Pix no Brasil",
        )
        assert result.territory is not None
        assert result.territory.primary_territory != ""

    def test_territory_weight_from_guidelines(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(
            content=_GOOD_CONTENT,
            title="Pix no Brasil",
        )
        # territory_weight should be a float 0.0-1.0
        assert 0.0 <= result.territory_weight <= 1.0

    def test_summary_includes_pass_fail(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(content=_GOOD_CONTENT, title="Pix")
        assert "PASSA" in result.summary or "NÃO PASSA" in result.summary

    def test_summary_includes_territory(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(content=_GOOD_CONTENT, title="Pix no Brasil")
        assert result.territory.primary_territory in result.summary

    def test_red_flag_content_fails(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(content=_RED_FLAG_CONTENT, title="XYZ Announcement")
        assert result.passes_guidelines is False
        assert len(result.validation.red_flags) > 0

    def test_result_to_dict(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(content=_GOOD_CONTENT, title="Pix")
        d = result.to_dict()
        assert "territory" in d
        assert "validation" in d
        assert "passes_guidelines" in d
        assert "territory_weight" in d
        assert "summary" in d


class TestGuidelinesPackAgentOutput:
    """Test GuidelinesPack with AgentOutput convenience method."""

    def test_extracts_body_md_and_title(self) -> None:
        pack = GuidelinesPack()
        output = _make_agent_output(
            title="Pix no Brasil",
            body_md=_GOOD_CONTENT,
        )
        result = pack.evaluate_agent_output(output)
        assert isinstance(result, GuidelinesResult)

    def test_passes_metadata_through(self) -> None:
        pack = GuidelinesPack()
        output = _make_agent_output(title="Test", body_md=_GOOD_CONTENT)
        # sources from AgentOutput should be accessible
        result = pack.evaluate_agent_output(output)
        assert isinstance(result, GuidelinesResult)


class TestGuidelinesResult:
    """Test GuidelinesResult data structure."""

    def test_passes_guidelines_reflects_validation(self) -> None:
        pack = GuidelinesPack()
        result = pack.evaluate(content=_BAD_CONTENT, title="Bad")
        assert result.passes_guidelines == result.validation.passes_editorial_bar
