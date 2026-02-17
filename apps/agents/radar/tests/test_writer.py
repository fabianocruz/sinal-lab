"""Tests for RADAR editorial writer (LLM-powered content generation)."""

import json
import os

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from apps.agents.radar.collector import TrendSignal
from apps.agents.radar.classifier import ClassifiedSignal
from apps.agents.radar.synthesizer import TrendSection
from apps.agents.base.llm import strip_code_fences
from apps.agents.radar.writer import RadarWriter, SectionContent


def make_classified_signal(
    title: str = "Test Signal",
    url: str = "https://example.com/test",
    source_name: str = "test_source",
    summary: str = "A test signal summary.",
    composite: float = 0.5,
) -> ClassifiedSignal:
    """Helper to create a ClassifiedSignal with defaults."""
    signal = TrendSignal(
        title=title,
        url=url,
        source_name=source_name,
        source_type="hn",
        summary=summary,
        published_at=datetime.now(timezone.utc),
    )
    return ClassifiedSignal(
        signal=signal,
        topics=["ai_ml"],
        primary_topic="ai_ml",
        topic_confidence=composite,
        momentum_score=composite,
        latam_relevance=composite,
    )


def make_section(heading: str = "AI & Machine Learning", signal_count: int = 2) -> TrendSection:
    """Helper to create a TrendSection with signals."""
    signals = [
        make_classified_signal(
            title=f"Signal {i}",
            url=f"https://example.com/{i}",
            source_name=f"source_{i}",
            summary=f"Summary for signal {i}.",
        )
        for i in range(1, signal_count + 1)
    ]
    return TrendSection(heading=heading, topic_key="ai_ml", signals=signals)


class TestSectionContent:
    """Test SectionContent dataclass."""

    def test_dataclass_fields(self):
        sc = SectionContent(intro="Section intro", summaries=["s1", "s2"])
        assert sc.intro == "Section intro"
        assert sc.summaries == ["s1", "s2"]


class TestRadarWriterAvailability:
    """Test RadarWriter.is_available property."""

    def test_is_available_delegates_to_client_true(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        writer = RadarWriter(client=mock_client)
        assert writer.is_available is True

    def test_is_available_delegates_to_client_false(self):
        mock_client = MagicMock()
        mock_client.is_available = False
        writer = RadarWriter(client=mock_client)
        assert writer.is_available is False

    def test_is_available_false_when_no_client(self):
        with patch.dict(os.environ, {}, clear=True):
            writer = RadarWriter(client=None)
            assert writer.is_available is False


class TestWriteReportIntro:
    """Test write_report_intro()."""

    def test_returns_string_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Esta semana, os sinais apontam para avanco em AI."

        writer = RadarWriter(client=mock_client)
        sections = [make_section("AI & Machine Learning"), make_section("Startups & Ecossistema")]
        result = writer.write_report_intro(sections, week_number=42)

        assert result == "Esta semana, os sinais apontam para avanco em AI."

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = RadarWriter(client=mock_client)
        result = writer.write_report_intro([make_section()], week_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = RadarWriter(client=mock_client)
        result = writer.write_report_intro([make_section()], week_number=1)

        assert result is None

    def test_prompt_contains_section_headings(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text"

        writer = RadarWriter(client=mock_client)
        sections = [
            make_section("AI & Machine Learning"),
            make_section("Startups & Ecossistema"),
        ]
        writer.write_report_intro(sections, week_number=1)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "AI & Machine Learning" in user_prompt
        assert "Startups & Ecossistema" in user_prompt

    def test_prompt_contains_signal_titles(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text"

        writer = RadarWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        writer.write_report_intro([section], week_number=1)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "Signal 1" in user_prompt
        assert "Signal 2" in user_prompt

    def test_prompt_is_in_portuguese(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro"

        writer = RadarWriter(client=mock_client)
        writer.write_report_intro([make_section()], week_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        assert "portugues" in system_prompt.lower() or "pt-br" in system_prompt.lower()

    def test_returns_none_on_empty_sections(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = RadarWriter(client=mock_client)
        result = writer.write_report_intro([], week_number=1)

        assert result is None


class TestWriteSectionContent:
    """Test write_section_content()."""

    def test_returns_section_content_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "O setor de AI teve uma semana intensa.",
            "summaries": [
                "Analise contextualizada do sinal 1.",
                "Analise contextualizada do sinal 2.",
            ],
        })

        writer = RadarWriter(client=mock_client)
        section = make_section("AI & Machine Learning", signal_count=2)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "O setor de AI teve uma semana intensa."
        assert len(result.summaries) == 2
        assert result.summaries[0] == "Analise contextualizada do sinal 1."

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = RadarWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = RadarWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "This is not JSON at all"

        writer = RadarWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None

    def test_returns_none_on_mismatched_summary_count(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro text",
            "summaries": ["Only one summary"],  # Section has 2 signals
        })

        writer = RadarWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        result = writer.write_section_content(section)

        assert result is None

    def test_prompt_contains_signal_titles_and_urls(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1", "s2"],
        })

        writer = RadarWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "Signal 1" in user_prompt
        assert "Signal 2" in user_prompt
        assert "https://example.com/1" in user_prompt
        assert "https://example.com/2" in user_prompt

    def test_prompt_contains_signal_summaries(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1", "s2"],
        })

        writer = RadarWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "Summary for signal 1" in user_prompt
        assert "Summary for signal 2" in user_prompt

    def test_parses_json_wrapped_in_code_fences(self):
        """LLMs often wrap JSON in ```json ... ``` fences."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            '```json\n'
            '{\n'
            '  "intro": "Semana intensa para AI.",\n'
            '  "summaries": ["Resumo 1.", "Resumo 2."]\n'
            '}\n'
            '```'
        )

        writer = RadarWriter(client=mock_client)
        section = make_section("AI & ML", signal_count=2)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "Semana intensa para AI."
        assert len(result.summaries) == 2

    def test_single_item_section(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Single signal intro",
            "summaries": ["Single summary"],
        })

        writer = RadarWriter(client=mock_client)
        section = make_section("AI", signal_count=1)
        result = writer.write_section_content(section)

        assert result is not None
        assert len(result.summaries) == 1

    def test_returns_none_on_empty_section(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = RadarWriter(client=mock_client)
        section = TrendSection(heading="Empty", topic_key="ai_ml", signals=[])
        result = writer.write_section_content(section)

        assert result is None
