"""Tests for Layer 2: VALIDACAO — data quality validation."""

import pytest
from datetime import datetime, timezone, timedelta

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.validacao import run_validacao, _detect_financial_claims
from apps.agents.editorial.models import FlagSeverity


def _make_output(**overrides) -> AgentOutput:
    """Create a valid AgentOutput with sensible defaults."""
    defaults = {
        "title": "Test Content",
        "body_md": "This is test content with enough words to be valid. " * 5,
        "agent_name": "radar",
        "run_id": "radar-20260215-def456",
        "confidence": ConfidenceScore(
            data_quality=0.7,
            analysis_confidence=0.6,
            source_count=5,
            verified=True,
        ),
        "sources": ["https://source1.com", "https://source2.com"],
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


class TestValidacaoGradeA:
    """Grade A: multi-source verified, high DQ."""

    def test_high_quality_verified_gets_grade_a(self):
        output = _make_output(
            confidence=ConfidenceScore(
                data_quality=0.8, analysis_confidence=0.7, source_count=4, verified=True,
            ),
        )
        result = run_validacao(output)
        assert result.grade == "A"
        assert result.passed is True

    def test_metadata_includes_quality_info(self):
        output = _make_output()
        result = run_validacao(output)
        assert "data_quality" in result.metadata
        assert "source_count" in result.metadata
        assert "verified" in result.metadata


class TestValidacaoGradeB:
    """Grade B: single-source plausible."""

    def test_medium_quality_gets_grade_b(self):
        output = _make_output(
            confidence=ConfidenceScore(
                data_quality=0.55, analysis_confidence=0.5, source_count=2,
            ),
        )
        result = run_validacao(output)
        assert result.grade == "B"
        assert result.passed is True


class TestValidacaoGradeD:
    """Grade D: low quality, blockers."""

    def test_very_low_dq_is_blocker(self):
        output = _make_output(
            confidence=ConfidenceScore(
                data_quality=0.2, analysis_confidence=0.15, source_count=1,
            ),
        )
        result = run_validacao(output)
        assert result.grade == "D"
        assert result.passed is False
        blockers = [f for f in result.flags if f.severity == FlagSeverity.BLOCKER]
        assert len(blockers) >= 1


class TestFinancialClaimDetection:
    """Financial claims require multi-source verification."""

    def test_detects_usd_amounts(self):
        assert _detect_financial_claims("The company raised $50 million in Series A") is True

    def test_detects_brl_amounts(self):
        assert _detect_financial_claims("Faturamento de R$ 100 milhoes") is True

    def test_detects_funding_keywords(self):
        assert _detect_financial_claims("A rodada seed captou investimento") is True

    def test_detects_valuation(self):
        assert _detect_financial_claims("Company valuation reached $1 billion") is True

    def test_no_financial_in_tech_content(self):
        assert _detect_financial_claims("New Python library released for data processing") is False

    def test_financial_claim_single_source_is_blocker(self):
        output = _make_output(
            body_md="The startup raised $10 million in a Series A round. " * 5,
            confidence=ConfidenceScore(
                data_quality=0.5, analysis_confidence=0.4, source_count=1,
            ),
        )
        result = run_validacao(output)
        assert result.passed is False
        blockers = [f for f in result.flags if f.severity == FlagSeverity.BLOCKER]
        assert any("financial" in f.message.lower() for f in blockers)

    def test_financial_claim_multi_source_passes(self):
        output = _make_output(
            body_md="The startup raised $10 million in a Series A round. " * 5,
            confidence=ConfidenceScore(
                data_quality=0.7, analysis_confidence=0.6, source_count=3, verified=True,
            ),
        )
        result = run_validacao(output)
        assert result.passed is True


class TestDataFreshness:
    """Stale content should be flagged."""

    def test_fresh_content_no_stale_flag(self):
        output = _make_output()
        result = run_validacao(output)
        stale_flags = [f for f in result.flags if "stale" in f.message.lower()]
        assert len(stale_flags) == 0

    def test_old_content_gets_stale_warning(self):
        output = _make_output(
            generated_at=datetime.now(timezone.utc) - timedelta(days=100),
        )
        # Override the generated_at by creating directly
        output.generated_at = datetime.now(timezone.utc) - timedelta(days=100)
        result = run_validacao(output)
        stale_flags = [f for f in result.flags if "stale" in f.message.lower() or "potentially stale" in f.message.lower()]
        assert len(stale_flags) >= 1


class TestValidacaoLayerResult:
    def test_layer_name(self):
        output = _make_output()
        result = run_validacao(output)
        assert result.layer_name == "validacao"

    def test_financial_claims_tracked_in_metadata(self):
        output = _make_output(
            body_md="Company raised $50M in funding. " * 5,
        )
        result = run_validacao(output)
        assert result.metadata["financial_claims_detected"] is True
