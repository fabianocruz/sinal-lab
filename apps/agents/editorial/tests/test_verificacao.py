"""Tests for Layer 3: VERIFICACAO — structural fact-checking."""

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.verificacao import (
    run_verificacao,
    _check_percentages,
    _check_temporal_consistency,
    _check_urls,
    _check_duplicates,
)
from apps.agents.editorial.models import FlagSeverity


def _make_output(**overrides) -> AgentOutput:
    """Create a valid AgentOutput for fact-checking."""
    defaults = {
        "title": "Weekly Tech Report",
        "body_md": "This is clean content with no issues. " * 10,
        "agent_name": "sintese",
        "run_id": "sintese-20260215-xyz789",
        "confidence": ConfidenceScore(
            data_quality=0.7,
            analysis_confidence=0.6,
            source_count=5,
            verified=True,
        ),
        "sources": ["https://example.com"],
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


class TestPercentageSanity:
    """Check 1: Percentage values should be 0-100 (with growth rate exceptions)."""

    def test_normal_percentages_no_flags(self):
        flags = _check_percentages("Growth was 50% year over year, with 30% market share.")
        assert len(flags) == 0

    def test_over_100_percent_gets_warning(self):
        flags = _check_percentages("Revenue grew 250% in 2025.")
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.WARNING
        assert "250" in flags[0].message

    def test_multiple_high_percentages(self):
        flags = _check_percentages("Growth of 150% and 300% reported.")
        assert len(flags) == 2

    def test_zero_percent_is_fine(self):
        flags = _check_percentages("0% change from last quarter.")
        assert len(flags) == 0

    def test_100_percent_is_fine(self):
        flags = _check_percentages("Achieved 100% uptime.")
        assert len(flags) == 0


class TestTemporalConsistency:
    """Check 2: Date and year references should be consistent."""

    def test_current_year_no_flags(self):
        flags = _check_temporal_consistency("Founded in 2024, the company grew rapidly in 2025.")
        assert len(flags) == 0

    def test_future_year_gets_warning(self):
        flags = _check_temporal_consistency("Expected to reach $1B by 2030.")
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.WARNING
        assert "2030" in str(flags[0].message)

    def test_pre_2000_year_gets_info(self):
        flags = _check_temporal_consistency("The internet boom started in 1998.")
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.INFO

    def test_years_ago_reasonable_no_flag(self):
        flags = _check_temporal_consistency("Founded 3 years ago.")
        assert len(flags) == 0

    def test_years_ago_extreme_gets_warning(self):
        flags = _check_temporal_consistency("Established 100 years ago.")
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.WARNING

    def test_anos_atras_portuguese(self):
        flags = _check_temporal_consistency("Fundada 60 anos atras na regiao.")
        assert len(flags) == 1


class TestURLWellFormedness:
    """Check 3: All URLs should be well-formed."""

    def test_valid_markdown_links(self):
        body = "Check [this link](https://example.com/page) and [another](https://github.com/repo)."
        flags = _check_urls(body)
        assert len(flags) == 0

    def test_malformed_url_gets_warning(self):
        body = "See [broken link](not-a-url) for details."
        flags = _check_urls(body)
        assert len(flags) == 1
        assert "malformed" in flags[0].message.lower()

    def test_multiple_malformed_urls_gets_error(self):
        body = "[a](bad1) [b](bad2) [c](bad3) [d](bad4)"
        flags = _check_urls(body)
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.ERROR

    def test_raw_urls_also_checked(self):
        body = "Visit https://valid.com or also https://also-valid.com/path for info."
        flags = _check_urls(body)
        assert len(flags) == 0


class TestDuplicateDetection:
    """Check 4: Repeated paragraphs should be flagged."""

    def test_no_duplicates_clean(self):
        body = "First paragraph with enough content.\n\nSecond paragraph is different and unique."
        flags = _check_duplicates(body)
        assert len(flags) == 0

    def test_duplicate_paragraph_flagged(self):
        para = "This is a substantial paragraph with enough content to be considered meaningful for duplicate detection purposes."
        body = f"{para}\n\n{para}"
        flags = _check_duplicates(body)
        assert len(flags) == 1
        assert "duplicate" in flags[0].message.lower()

    def test_short_paragraphs_ignored(self):
        body = "---\n\n---\n\n---"
        flags = _check_duplicates(body)
        assert len(flags) == 0

    def test_case_insensitive_detection(self):
        para = "This is a substantial paragraph with enough content for detection."
        body = f"{para}\n\n{para.upper()}"
        flags = _check_duplicates(body)
        assert len(flags) == 1


class TestVerificacaoIntegration:
    """Full layer integration tests."""

    def test_clean_content_passes(self):
        output = _make_output()
        result = run_verificacao(output)
        assert result.passed is True
        assert result.grade in ("A", "B")
        assert result.layer_name == "verificacao"

    def test_content_with_red_flag_gets_blocker(self):
        body = (
            "Revenue grew 250% and market share hit 300% while "
            "efficiency improved 400%. "
        )
        body += "Additional filler content. " * 10
        output = _make_output(body_md=body)
        result = run_verificacao(output)
        # 3 yellow flags (percentages > 100) exceeds threshold of 2
        assert result.passed is False
        assert result.grade in ("C", "D")

    def test_metadata_tracks_checks(self):
        output = _make_output()
        result = run_verificacao(output)
        assert "checks_run" in result.metadata
        assert "percentage_sanity" in result.metadata["checks_run"]
        assert "temporal_consistency" in result.metadata["checks_run"]
        assert "url_wellformedness" in result.metadata["checks_run"]
        assert "duplicate_detection" in result.metadata["checks_run"]

    def test_grade_a_for_clean_content(self):
        output = _make_output(
            body_md="Clean content with [valid links](https://example.com) and reasonable 45% growth in 2025. " * 5,
        )
        result = run_verificacao(output)
        assert result.grade == "A"

    def test_grade_b_for_minor_issues(self):
        output = _make_output(
            body_md="Revenue grew 150% in 2025. The rest of the content is clean and has no issues. " + ("Additional filler content for length. " * 8),
        )
        result = run_verificacao(output)
        assert result.grade == "B"

    def test_serializable(self):
        output = _make_output()
        result = run_verificacao(output)
        d = result.to_dict()
        assert "metadata" in d
        assert d["layer_name"] == "verificacao"
