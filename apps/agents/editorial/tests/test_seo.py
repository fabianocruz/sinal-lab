"""Tests for Layer 5: SEO — search optimization."""

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.seo import (
    run_seo,
    _check_title,
    _check_meta_description,
    _check_header_hierarchy,
    _generate_article_jsonld,
)
from apps.agents.editorial.models import FlagSeverity


def _make_output(**overrides) -> AgentOutput:
    defaults = {
        "title": "Sinal Semanal #42 — LATAM Tech Ecosystem Weekly Digest",
        "body_md": "# Main Title\n\nContent here.\n\n## Section 1\n\nMore content.\n\n## Section 2\n\nEven more. " * 3,
        "agent_name": "sintese",
        "run_id": "sintese-20260215-seo01",
        "confidence": ConfidenceScore(
            data_quality=0.7, analysis_confidence=0.6, source_count=5, verified=True,
        ),
        "sources": ["https://techcrunch.com/feed"],
        "summary": "Weekly digest of the most important LATAM tech ecosystem developments, curated by AI agents with verified data.",
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


class TestTitleCheck:
    def test_ideal_length_no_flags(self):
        flags, meta = _check_title("A" * 55)  # 55 chars — ideal range
        assert len(flags) == 0
        assert meta["title_in_ideal_range"] is True

    def test_too_short_gets_warning(self):
        flags, meta = _check_title("Short")
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.WARNING
        assert "[SEO]" in flags[0].message

    def test_too_long_gets_warning(self):
        flags, _ = _check_title("A" * 75)
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.WARNING

    def test_slightly_short_gets_info(self):
        flags, _ = _check_title("A" * 40)  # Between 30-50
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.INFO

    def test_slightly_long_gets_info(self):
        flags, _ = _check_title("A" * 65)  # Between 60-70
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.INFO


class TestMetaDescription:
    def test_good_summary_no_flags(self):
        summary = "A" * 155  # Ideal range
        flags, meta = _check_meta_description(summary, "body text")
        assert len(flags) == 0
        assert "suggested_meta_description" in meta

    def test_empty_summary_extracts_from_body(self):
        body = "# Title\n\nThis is a substantial paragraph with enough words to serve as a meta description for the content page."
        flags, meta = _check_meta_description("", body)
        assert "suggested_meta_description" in meta

    def test_short_summary_gets_info(self):
        flags, _ = _check_meta_description("Short summary.", "body")
        assert len(flags) == 1
        assert flags[0].severity in (FlagSeverity.INFO, FlagSeverity.WARNING)

    def test_empty_everything_gets_warning(self):
        flags, _ = _check_meta_description("", "# Title\n\nOk.")
        assert len(flags) >= 1


class TestHeaderHierarchy:
    def test_proper_hierarchy_no_flags(self):
        body = "# Title\n\n## Section\n\n### Subsection\n\n## Another Section"
        flags, meta = _check_header_hierarchy(body)
        hierarchy_flags = [f for f in flags if "hierarchy" in f.message.lower()]
        assert len(hierarchy_flags) == 0
        assert meta["hierarchy_valid"] is True

    def test_skipped_levels_flagged(self):
        body = "# Title\n\n### Skipped H2\n\nContent."
        flags, meta = _check_header_hierarchy(body)
        skip_flags = [f for f in flags if "skip" in f.message.lower()]
        assert len(skip_flags) == 1
        assert meta["hierarchy_valid"] is False

    def test_multiple_h1_flagged(self):
        body = "# Title 1\n\n# Title 2\n\nContent."
        flags, meta = _check_header_hierarchy(body)
        h1_flags = [f for f in flags if "h1" in f.message.lower()]
        assert len(h1_flags) == 1

    def test_no_headers_gets_info(self):
        body = "Just plain text with no headers at all."
        flags, _ = _check_header_hierarchy(body)
        assert len(flags) == 1
        assert flags[0].severity == FlagSeverity.INFO


class TestJsonLdGeneration:
    def test_generates_article_schema(self):
        output = _make_output()
        jsonld = _generate_article_jsonld(output)
        assert jsonld["@type"] == "Article"
        assert jsonld["@context"] == "https://schema.org"
        assert jsonld["headline"] == output.title
        assert "author" in jsonld
        assert jsonld["author"]["name"] == "Sinal.lab"

    def test_includes_rating(self):
        output = _make_output()
        jsonld = _generate_article_jsonld(output)
        assert "reviewRating" in jsonld
        assert jsonld["reviewRating"]["bestRating"] == 5


class TestSeoIntegration:
    def test_layer_name(self):
        output = _make_output()
        result = run_seo(output)
        assert result.layer_name == "seo"

    def test_never_blocks(self):
        output = _make_output(title="X", summary="")
        result = run_seo(output)
        assert result.passed is True

    def test_modifications_include_jsonld(self):
        output = _make_output()
        result = run_seo(output)
        assert "jsonld" in result.modifications
        assert result.modifications["jsonld"]["@type"] == "Article"

    def test_seo_tags_in_messages(self):
        output = _make_output(title="Short")
        result = run_seo(output)
        seo_flags = [f for f in result.flags if "[SEO]" in f.message]
        assert len(seo_flags) >= 1

    def test_grade_a_for_well_optimized(self):
        output = _make_output(
            title="Sinal Semanal 42 - LATAM Tech Ecosystem Weekly Digest",
            summary="Weekly digest of the most important LATAM tech ecosystem developments curated by AI agents with full data verification and transparency.",
        )
        result = run_seo(output)
        assert result.grade in ("A", "B")

    def test_serializable(self):
        output = _make_output()
        result = run_seo(output)
        d = result.to_dict()
        assert "metadata" in d
