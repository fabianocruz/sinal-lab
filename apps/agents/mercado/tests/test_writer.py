"""Tests for MERCADO LLM writer (ecosystem narrative and highlight descriptions)."""

import json
import os

import pytest
from unittest.mock import MagicMock, patch

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.llm import strip_code_fences
from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.scorer import ScoredCompanyProfile
from apps.agents.mercado.writer import MercadoWriter


def make_scored_profile(
    name: str = "TestCo",
    city: str = "São Paulo",
    country: str = "Brasil",
    sector: str = "Fintech",
    description: str = "A fintech platform for SMBs.",
    github_url: str = "https://github.com/testco",
    composite: float = 0.7,
) -> ScoredCompanyProfile:
    """Helper to create a ScoredCompanyProfile with defaults."""
    profile = CompanyProfile(
        name=name,
        slug=name.lower().replace(" ", "-"),
        description=description,
        sector=sector,
        city=city,
        country=country,
        github_url=github_url,
        source_url=github_url,
        source_name="github_test",
    )
    # DQ and AC derived from composite to keep helper simple
    dq = min(composite + 0.05, 1.0)
    ac = max(composite - 0.05, 0.0)
    confidence = ConfidenceScore(data_quality=dq, analysis_confidence=ac)
    return ScoredCompanyProfile(
        profile=profile,
        confidence=confidence,
        composite_score=composite,
    )


class TestMercadoWriterAvailability:
    """Test MercadoWriter.is_available property."""

    def test_is_available_delegates_to_client_true(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        writer = MercadoWriter(client=mock_client)
        assert writer.is_available is True

    def test_is_available_delegates_to_client_false(self):
        mock_client = MagicMock()
        mock_client.is_available = False
        writer = MercadoWriter(client=mock_client)
        assert writer.is_available is False


class TestWriteSnapshotIntro:
    """Test write_snapshot_intro()."""

    def test_returns_string_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            "Nesta semana, o ecossistema LATAM revelou novas empresas em fintech e healthtech."
        )

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("NuPay", "São Paulo", "Brasil", "Fintech"),
            make_scored_profile("MedApp", "Rio de Janeiro", "Brasil", "HealthTech"),
        ]
        result = writer.write_snapshot_intro(profiles, week_number=7)

        assert isinstance(result, str)
        assert "ecossistema LATAM" in result

    def test_returns_none_when_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = MercadoWriter(client=mock_client)
        result = writer.write_snapshot_intro([make_scored_profile()], week_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = MercadoWriter(client=mock_client)
        result = writer.write_snapshot_intro([make_scored_profile()], week_number=1)

        assert result is None

    def test_prompt_contains_aggregate_stats(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text."

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("Co1", "São Paulo", "Brasil", "Fintech"),
            make_scored_profile("Co2", "São Paulo", "Brasil", "Fintech"),
            make_scored_profile("Co3", "Rio de Janeiro", "Brasil", "HealthTech"),
        ]
        writer.write_snapshot_intro(profiles, week_number=7)

        user_prompt = (
            mock_client.generate.call_args[1].get("user_prompt")
            or mock_client.generate.call_args[0][0]
        )
        # Should contain profile count
        assert "3" in user_prompt
        # Should contain city names
        assert "São Paulo" in user_prompt
        assert "Rio de Janeiro" in user_prompt
        # Should contain sector names
        assert "Fintech" in user_prompt
        assert "HealthTech" in user_prompt

    def test_prompt_is_in_portuguese(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro."

        writer = MercadoWriter(client=mock_client)
        writer.write_snapshot_intro([make_scored_profile()], week_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        assert "portugues" in system_prompt.lower() or "pt-br" in system_prompt.lower()

    def test_returns_none_on_empty_profiles(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = MercadoWriter(client=mock_client)
        result = writer.write_snapshot_intro([], week_number=1)

        assert result is None


class TestWriteHighlightDescriptions:
    """Test write_highlight_descriptions()."""

    def test_returns_list_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "descriptions": [
                "NuPay se destaca como plataforma de pagamentos digitais.",
                "MedApp inova em telemedicina na America Latina.",
            ],
        })

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("NuPay", "São Paulo", "Brasil", "Fintech"),
            make_scored_profile("MedApp", "Rio de Janeiro", "Brasil", "HealthTech"),
        ]
        result = writer.write_highlight_descriptions(profiles)

        assert result is not None
        assert len(result) == 2
        assert "NuPay" in result[0]
        assert "MedApp" in result[1]

    def test_returns_none_when_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = MercadoWriter(client=mock_client)
        result = writer.write_highlight_descriptions([make_scored_profile()])

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = MercadoWriter(client=mock_client)
        result = writer.write_highlight_descriptions([make_scored_profile()])

        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "This is not valid JSON at all"

        writer = MercadoWriter(client=mock_client)
        result = writer.write_highlight_descriptions([make_scored_profile()])

        assert result is None

    def test_returns_none_on_mismatched_count(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "descriptions": ["Only one description"],
        })

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("Co1"),
            make_scored_profile("Co2"),
        ]
        result = writer.write_highlight_descriptions(profiles)

        assert result is None

    def test_prompt_contains_company_names_and_details(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "descriptions": ["Desc 1", "Desc 2"],
        })

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("NuPay", "São Paulo", "Brasil", "Fintech",
                                github_url="https://github.com/nupay"),
            make_scored_profile("MedApp", "Rio de Janeiro", "Brasil", "HealthTech",
                                github_url="https://github.com/medapp"),
        ]
        writer.write_highlight_descriptions(profiles)

        user_prompt = (
            mock_client.generate.call_args[1].get("user_prompt")
            or mock_client.generate.call_args[0][0]
        )
        assert "NuPay" in user_prompt
        assert "MedApp" in user_prompt
        assert "São Paulo" in user_prompt
        assert "Rio de Janeiro" in user_prompt
        assert "https://github.com/nupay" in user_prompt
        assert "https://github.com/medapp" in user_prompt

    def test_parses_json_with_code_fences(self):
        """LLMs often wrap JSON in ```json ... ``` fences."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            '```json\n'
            '{\n'
            '  "descriptions": ["Descricao da empresa 1.", "Descricao da empresa 2."]\n'
            '}\n'
            '```'
        )

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("Co1"),
            make_scored_profile("Co2"),
        ]
        result = writer.write_highlight_descriptions(profiles)

        assert result is not None
        assert len(result) == 2
        assert result[0] == "Descricao da empresa 1."
        assert result[1] == "Descricao da empresa 2."

    def test_handles_single_profile(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "descriptions": ["Unica empresa destaque da semana."],
        })

        writer = MercadoWriter(client=mock_client)
        result = writer.write_highlight_descriptions([make_scored_profile()])

        assert result is not None
        assert len(result) == 1
        assert result[0] == "Unica empresa destaque da semana."


class TestWriteHeadline:
    """Test write_headline()."""

    def test_returns_string_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Sao Paulo domina com 88% das startups mapeadas"

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("NuPay", "São Paulo", "Brasil", "Fintech"),
            make_scored_profile("MedApp", "Rio de Janeiro", "Brasil", "HealthTech"),
        ]
        result = writer.write_headline(profiles, week_number=10)

        assert result == "Sao Paulo domina com 88% das startups mapeadas"

    def test_strips_surrounding_quotes(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = '"Fintech lidera ecossistema LATAM"'

        writer = MercadoWriter(client=mock_client)
        result = writer.write_headline([make_scored_profile()], week_number=1)

        assert result == "Fintech lidera ecossistema LATAM"

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = MercadoWriter(client=mock_client)
        result = writer.write_headline([make_scored_profile()], week_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = MercadoWriter(client=mock_client)
        result = writer.write_headline([make_scored_profile()], week_number=1)

        assert result is None

    def test_returns_none_on_empty_string(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "   "

        writer = MercadoWriter(client=mock_client)
        result = writer.write_headline([make_scored_profile()], week_number=1)

        assert result is None

    def test_returns_none_on_empty_profiles(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = MercadoWriter(client=mock_client)
        result = writer.write_headline([], week_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_prompt_contains_aggregate_data(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Titulo"

        writer = MercadoWriter(client=mock_client)
        profiles = [
            make_scored_profile("Co1", "São Paulo", "Brasil", "Fintech"),
            make_scored_profile("Co2", "Rio de Janeiro", "Brasil", "HealthTech"),
        ]
        writer.write_headline(profiles, week_number=7)

        user_prompt = (
            mock_client.generate.call_args[1].get("user_prompt")
            or mock_client.generate.call_args[0][0]
        )
        assert "São Paulo" in user_prompt or "Sao Paulo" in user_prompt
        assert "Fintech" in user_prompt

    def test_uses_max_tokens_64(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Titulo"

        writer = MercadoWriter(client=mock_client)
        writer.write_headline([make_scored_profile()], week_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        assert call_kwargs.get("max_tokens") == 64


class TestWriteSectorAnalysis:
    """Test write_sector_analysis()."""

    def test_returns_sector_content_on_success(self):
        from apps.agents.mercado.writer import SectorContent

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "O setor de fintech segue em expansão na América Latina.",
            "descriptions": [
                "NuPay se destaca como plataforma de pagamentos digitais.",
                "PayCo inova em crédito para PMEs.",
            ],
        })

        writer = MercadoWriter(client=mock_client)
        from apps.agents.mercado.synthesizer import SectorSection

        section = SectorSection(
            heading="Fintech",
            profiles=[
                make_scored_profile("NuPay", sector="Fintech"),
                make_scored_profile("PayCo", sector="Fintech"),
            ],
        )
        result = writer.write_sector_analysis(section, aggregate_context="100 total companies")

        assert result is not None
        assert isinstance(result, SectorContent)
        assert "fintech" in result.intro.lower()
        assert len(result.descriptions) == 2
        assert "NuPay" in result.descriptions[0]

    def test_returns_none_when_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = MercadoWriter(client=mock_client)
        from apps.agents.mercado.synthesizer import SectorSection

        section = SectorSection(
            heading="Fintech",
            profiles=[make_scored_profile()],
        )
        result = writer.write_sector_analysis(section, aggregate_context="")

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = MercadoWriter(client=mock_client)
        from apps.agents.mercado.synthesizer import SectorSection

        section = SectorSection(
            heading="Fintech",
            profiles=[make_scored_profile()],
        )
        result = writer.write_sector_analysis(section, aggregate_context="")

        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Not valid JSON"

        writer = MercadoWriter(client=mock_client)
        from apps.agents.mercado.synthesizer import SectorSection

        section = SectorSection(
            heading="Fintech",
            profiles=[make_scored_profile()],
        )
        result = writer.write_sector_analysis(section, aggregate_context="")

        assert result is None

    def test_returns_none_on_description_count_mismatch(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro text.",
            "descriptions": ["Only one"],
        })

        writer = MercadoWriter(client=mock_client)
        from apps.agents.mercado.synthesizer import SectorSection

        section = SectorSection(
            heading="Fintech",
            profiles=[
                make_scored_profile("Co1"),
                make_scored_profile("Co2"),
            ],
        )
        result = writer.write_sector_analysis(section, aggregate_context="")

        assert result is None

    def test_parses_json_with_code_fences(self):
        from apps.agents.mercado.writer import SectorContent

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            '```json\n'
            '{\n'
            '  "intro": "Sector intro.",\n'
            '  "descriptions": ["Desc 1."]\n'
            '}\n'
            '```'
        )

        writer = MercadoWriter(client=mock_client)
        from apps.agents.mercado.synthesizer import SectorSection

        section = SectorSection(
            heading="Fintech",
            profiles=[make_scored_profile()],
        )
        result = writer.write_sector_analysis(section, aggregate_context="")

        assert result is not None
        assert result.intro == "Sector intro."
        assert result.descriptions == ["Desc 1."]

    def test_prompt_contains_sector_and_profiles(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro.",
            "descriptions": ["Desc."],
        })

        writer = MercadoWriter(client=mock_client)
        from apps.agents.mercado.synthesizer import SectorSection

        section = SectorSection(
            heading="HealthTech",
            profiles=[
                make_scored_profile("MedApp", city="Rio de Janeiro", sector="HealthTech"),
            ],
        )
        writer.write_sector_analysis(section, aggregate_context="500 companies total")

        user_prompt = (
            mock_client.generate.call_args[1].get("user_prompt")
            or mock_client.generate.call_args[0][0]
        )
        assert "HealthTech" in user_prompt
        assert "MedApp" in user_prompt
        assert "Rio de Janeiro" in user_prompt
        assert "500 companies total" in user_prompt
