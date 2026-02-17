"""Tests for FUNDING editorial writer (LLM-powered content generation)."""

import json
import os
from datetime import date
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.llm import strip_code_fences
from apps.agents.funding.collector import FundingEvent
from apps.agents.funding.scorer import ScoredFundingEvent
from apps.agents.funding.writer import FundingWriter, SectionContent


def make_scored_event(
    company_name: str = "TestCo",
    round_type: str = "series_a",
    amount_usd: float = 10.0,
    source_name: str = "test_source",
    lead_investors: Optional[List[str]] = None,
    composite: float = 0.5,
) -> ScoredFundingEvent:
    """Helper to create a ScoredFundingEvent with defaults."""
    if lead_investors is None:
        lead_investors = ["Sequoia Capital"]

    event = FundingEvent(
        company_name=company_name,
        round_type=round_type,
        amount_usd=amount_usd,
        source_url=f"https://example.com/{company_name.lower()}",
        source_name=source_name,
        lead_investors=lead_investors,
        announced_date=date(2026, 2, 10),
    )
    confidence = ConfidenceScore(
        data_quality=composite,
        analysis_confidence=composite * 0.9,
    )
    return ScoredFundingEvent(
        event=event,
        confidence=confidence,
        composite_score=confidence.composite,
    )


class TestSectionContent:
    """Test SectionContent dataclass."""

    def test_dataclass_fields(self):
        sc = SectionContent(intro="Market intro", highlights=["h1", "h2"])
        assert sc.intro == "Market intro"
        assert sc.highlights == ["h1", "h2"]


class TestFundingWriterAvailability:
    """Test FundingWriter.is_available property."""

    def test_is_available_delegates_to_client_true(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        writer = FundingWriter(client=mock_client)
        assert writer.is_available is True

    def test_is_available_delegates_to_client_false(self):
        mock_client = MagicMock()
        mock_client.is_available = False
        writer = FundingWriter(client=mock_client)
        assert writer.is_available is False


class TestWriteReportIntro:
    """Test write_report_intro()."""

    def test_returns_string_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            "Esta semana o mercado LATAM registrou US$ 120M em rodadas."
        )

        writer = FundingWriter(client=mock_client)
        events = [
            make_scored_event("Nubank", "series_b", 50.0),
            make_scored_event("Creditas", "series_a", 30.0),
            make_scored_event("Loft", "seed", 5.0),
        ]
        result = writer.write_report_intro(events, week_number=7)

        assert result == "Esta semana o mercado LATAM registrou US$ 120M em rodadas."

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = FundingWriter(client=mock_client)
        events = [make_scored_event()]
        result = writer.write_report_intro(events, week_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = FundingWriter(client=mock_client)
        events = [make_scored_event()]
        result = writer.write_report_intro(events, week_number=1)

        assert result is None

    def test_prompt_contains_event_details(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text"

        writer = FundingWriter(client=mock_client)
        events = [
            make_scored_event("Nubank", "series_b", 50.0),
            make_scored_event("Creditas", "series_a", 30.0),
        ]
        writer.write_report_intro(events, week_number=7)

        user_prompt = (
            mock_client.generate.call_args[1].get("user_prompt")
            or mock_client.generate.call_args[0][0]
        )
        assert "Nubank" in user_prompt
        assert "Creditas" in user_prompt
        assert "50.0" in user_prompt or "$50" in user_prompt
        assert "30.0" in user_prompt or "$30" in user_prompt
        assert "series_b" in user_prompt or "Series B" in user_prompt or "Série B" in user_prompt

    def test_prompt_is_in_portuguese(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro"

        writer = FundingWriter(client=mock_client)
        writer.write_report_intro([make_scored_event()], week_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        assert (
            "portugues" in system_prompt.lower()
            or "pt-br" in system_prompt.lower()
        )

    def test_returns_none_on_empty_events(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = FundingWriter(client=mock_client)
        result = writer.write_report_intro([], week_number=1)

        assert result is None


class TestWriteDealHighlights:
    """Test write_deal_highlights()."""

    def test_returns_list_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "highlights": [
                "A rodada da Nubank sinaliza maturidade do mercado.",
                "Creditas avanca em credito imobiliario com novo aporte.",
                "A Loft continua captando apesar da correcao do mercado.",
            ],
        })

        writer = FundingWriter(client=mock_client)
        events = [
            make_scored_event("Nubank", "series_b", 50.0),
            make_scored_event("Creditas", "series_a", 30.0),
            make_scored_event("Loft", "seed", 5.0),
        ]
        result = writer.write_deal_highlights(events)

        assert result is not None
        assert len(result) == 3
        assert "Nubank" in result[0]
        assert "Creditas" in result[1]

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = FundingWriter(client=mock_client)
        result = writer.write_deal_highlights([make_scored_event()])

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = FundingWriter(client=mock_client)
        result = writer.write_deal_highlights([make_scored_event()])

        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "This is not JSON at all"

        writer = FundingWriter(client=mock_client)
        result = writer.write_deal_highlights([make_scored_event()])

        assert result is None

    def test_returns_none_on_mismatched_count(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "highlights": ["Only one highlight"],  # But 2 events passed
        })

        writer = FundingWriter(client=mock_client)
        events = [
            make_scored_event("Nubank", "series_b", 50.0),
            make_scored_event("Creditas", "series_a", 30.0),
        ]
        result = writer.write_deal_highlights(events)

        assert result is None

    def test_prompt_contains_company_details(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "highlights": ["h1", "h2"],
        })

        writer = FundingWriter(client=mock_client)
        events = [
            make_scored_event(
                "Nubank", "series_b", 50.0,
                lead_investors=["SoftBank", "Sequoia"],
            ),
            make_scored_event(
                "Creditas", "series_a", 30.0,
                lead_investors=["Kaszek"],
            ),
        ]
        writer.write_deal_highlights(events)

        user_prompt = (
            mock_client.generate.call_args[1].get("user_prompt")
            or mock_client.generate.call_args[0][0]
        )
        assert "Nubank" in user_prompt
        assert "Creditas" in user_prompt
        assert "50.0" in user_prompt or "$50" in user_prompt
        assert "SoftBank" in user_prompt
        assert "Kaszek" in user_prompt

    def test_parses_json_with_code_fences(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            '```json\n'
            '{\n'
            '  "highlights": ["Highlight 1.", "Highlight 2."]\n'
            '}\n'
            '```'
        )

        writer = FundingWriter(client=mock_client)
        events = [
            make_scored_event("CompanyA"),
            make_scored_event("CompanyB"),
        ]
        result = writer.write_deal_highlights(events)

        assert result is not None
        assert len(result) == 2
        assert result[0] == "Highlight 1."

    def test_handles_single_event(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "highlights": ["Unico destaque da semana."],
        })

        writer = FundingWriter(client=mock_client)
        events = [make_scored_event("SoloCompany")]
        result = writer.write_deal_highlights(events)

        assert result is not None
        assert len(result) == 1
        assert result[0] == "Unico destaque da semana."
