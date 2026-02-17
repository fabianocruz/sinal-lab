"""Tests for Layer 4: VIES — bias detection."""

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.vies import (
    run_vies,
    _compute_geographic_distribution,
    _compute_sector_distribution,
    _compute_source_distribution,
)
from apps.agents.editorial.models import FlagSeverity


def _make_output(**overrides) -> AgentOutput:
    defaults = {
        "title": "LATAM Tech Weekly",
        "body_md": "Diverse content covering multiple regions and sectors. " * 10,
        "agent_name": "sintese",
        "run_id": "sintese-20260215-vies01",
        "confidence": ConfidenceScore(
            data_quality=0.7, analysis_confidence=0.6, source_count=5, verified=True,
        ),
        "sources": [
            "https://techcrunch.com/feed",
            "https://github.com/trending",
            "https://news.ycombinator.com/rss",
        ],
    }
    defaults.update(overrides)
    return AgentOutput(**defaults)


class TestGeographicBias:
    def test_balanced_geography_no_flag(self):
        body = (
            "Startups in Sao Paulo are growing. "
            "Florianopolis also has a vibrant scene. "
            "Rio de Janeiro is expanding. "
            "Curitiba innovates in agritech. "
        ) * 3
        output = _make_output(body_md=body)
        result = run_vies(output)
        geo_flags = [f for f in result.flags if "geographic" in f.message.lower()]
        assert len(geo_flags) == 0

    def test_sao_paulo_dominance_flagged(self):
        body = (
            "Sao Paulo leads in fintech. SP startups raised more. "
            "São Paulo ecosystem is the largest. Sao Paulo attracts talent. "
        ) * 5
        output = _make_output(body_md=body)
        result = run_vies(output)
        geo_flags = [f for f in result.flags if "geographic" in f.message.lower()]
        assert len(geo_flags) >= 1
        assert geo_flags[0].severity == FlagSeverity.WARNING

    def test_geo_distribution_computed(self):
        dist = _compute_geographic_distribution("sao paulo and rio de janeiro and curitiba")
        assert "Sao Paulo" in dist
        assert "Rio de Janeiro" in dist
        assert "Curitiba" in dist


class TestSectorBias:
    def test_diverse_sectors_no_flag(self):
        body = "Fintech grows. AI innovates. SaaS scales. Agritech feeds. Edtech educates."
        output = _make_output(body_md=body)
        result = run_vies(output)
        sector_flags = [f for f in result.flags if "sector" in f.message.lower()]
        assert len(sector_flags) == 0

    def test_fintech_dominance_flagged(self):
        body = (
            "Fintech leads the way. Pagamento digital grows. "
            "Banco digital expands. Pix adoption rises. "
            "Open finance is the future. Credito tech innovates. "
        ) * 5
        output = _make_output(body_md=body)
        result = run_vies(output)
        sector_flags = [f for f in result.flags if "sector" in f.message.lower()]
        assert len(sector_flags) >= 1

    def test_sector_distribution_computed(self):
        dist = _compute_sector_distribution("fintech and machine learning and saas")
        assert "Fintech" in dist
        assert "AI/ML" in dist
        assert "SaaS" in dist


class TestSourceBias:
    def test_diverse_sources_no_flag(self):
        sources = [
            "https://techcrunch.com/feed",
            "https://github.com/trending",
            "https://news.ycombinator.com/rss",
            "https://dev.to/feed",
        ]
        output = _make_output(sources=sources)
        result = run_vies(output)
        source_flags = [f for f in result.flags if "source bias" in f.message.lower()]
        assert len(source_flags) == 0

    def test_single_source_dominance_flagged(self):
        sources = [
            "https://techcrunch.com/feed1",
            "https://techcrunch.com/feed2",
            "https://techcrunch.com/feed3",
            "https://github.com/trending",
        ]
        output = _make_output(sources=sources)
        result = run_vies(output)
        source_flags = [f for f in result.flags if "source bias" in f.message.lower()]
        assert len(source_flags) >= 1

    def test_source_distribution_extracts_domains(self):
        dist = _compute_source_distribution([
            "https://techcrunch.com/feed",
            "https://github.com/trending",
        ])
        assert "techcrunch.com" in dist
        assert "github.com" in dist


class TestViesIntegration:
    def test_layer_name(self):
        output = _make_output()
        result = run_vies(output)
        assert result.layer_name == "vies"

    def test_never_blocks(self):
        body = "Sao Paulo " * 100
        output = _make_output(body_md=body)
        result = run_vies(output)
        assert result.passed is True

    def test_grade_a_for_diverse_content(self):
        body = "Various cities and sectors are represented equally in this content."
        output = _make_output(body_md=body)
        result = run_vies(output)
        assert result.grade == "A"

    def test_metadata_includes_distributions(self):
        output = _make_output()
        result = run_vies(output)
        assert "geographic_distribution" in result.metadata
        assert "sector_distribution" in result.metadata
        assert "source_distribution" in result.metadata

    def test_serializable(self):
        output = _make_output()
        result = run_vies(output)
        d = result.to_dict()
        assert "metadata" in d
