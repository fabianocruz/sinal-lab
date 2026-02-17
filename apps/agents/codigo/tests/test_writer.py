"""Tests for CODIGO editorial writer (LLM-powered content generation)."""

import json
import os

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from apps.agents.codigo.analyzer import AnalyzedSignal
from apps.agents.codigo.collector import DevSignal
from apps.agents.codigo.synthesizer import ReportSection
from apps.agents.base.llm import strip_code_fences
from apps.agents.codigo.writer import CodigoWriter, SectionContent


def make_analyzed_signal(
    title: str = "test/repo",
    url: str = "https://github.com/test/repo",
    source_name: str = "github_trending_daily",
    summary: str = "A test repo for developer tooling.",
    language: str = "python",
    adoption_indicator: str = "rising",
) -> AnalyzedSignal:
    """Helper to create an AnalyzedSignal with defaults."""
    signal = DevSignal(
        title=title,
        url=url,
        source_name=source_name,
        signal_type="repo",
        summary=summary,
        language=language,
        published_at=datetime.now(timezone.utc),
    )
    return AnalyzedSignal(
        signal=signal,
        category="ai_frameworks",
        language_weight=0.9,
        momentum_score=0.5,
        community_score=0.5,
        adoption_indicator=adoption_indicator,
    )


def make_section(heading: str = "AI Frameworks & Tools", signal_count: int = 2) -> ReportSection:
    """Helper to create a ReportSection with signals."""
    signals = [
        make_analyzed_signal(
            title=f"org/repo-{i}",
            url=f"https://github.com/org/repo-{i}",
            source_name=f"source_{i}",
            summary=f"Summary for repo {i}.",
            language="python" if i % 2 == 1 else "typescript",
        )
        for i in range(1, signal_count + 1)
    ]
    return ReportSection(heading=heading, category_key="ai_frameworks", signals=signals)


class TestSectionContent:
    """Test SectionContent dataclass."""

    def test_dataclass_fields(self):
        sc = SectionContent(intro="Section intro", summaries=["s1", "s2"])
        assert sc.intro == "Section intro"
        assert sc.summaries == ["s1", "s2"]


class TestCodigoWriterAvailability:
    """Test CodigoWriter.is_available property."""

    def test_is_available_delegates_to_client_true(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        writer = CodigoWriter(client=mock_client)
        assert writer.is_available is True

    def test_is_available_delegates_to_client_false(self):
        mock_client = MagicMock()
        mock_client.is_available = False
        writer = CodigoWriter(client=mock_client)
        assert writer.is_available is False

    def test_is_available_false_when_no_client(self):
        with patch.dict(os.environ, {}, clear=True):
            writer = CodigoWriter(client=None)
            assert writer.is_available is False


class TestWriteReportIntro:
    """Test write_report_intro()."""

    def test_returns_string_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Esta semana, o ecossistema dev foi marcado por avancos em AI frameworks."

        writer = CodigoWriter(client=mock_client)
        sections = [make_section("AI Frameworks & Tools"), make_section("Web Frameworks")]
        result = writer.write_report_intro(sections, week_number=42)

        assert result == "Esta semana, o ecossistema dev foi marcado por avancos em AI frameworks."

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = CodigoWriter(client=mock_client)
        result = writer.write_report_intro([make_section()], week_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = CodigoWriter(client=mock_client)
        result = writer.write_report_intro([make_section()], week_number=1)

        assert result is None

    def test_prompt_contains_section_headings(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text"

        writer = CodigoWriter(client=mock_client)
        sections = [
            make_section("AI Frameworks & Tools"),
            make_section("Web Frameworks"),
        ]
        writer.write_report_intro(sections, week_number=1)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "AI Frameworks & Tools" in user_prompt
        assert "Web Frameworks" in user_prompt

    def test_prompt_contains_signal_titles(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text"

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        writer.write_report_intro([section], week_number=1)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "org/repo-1" in user_prompt
        assert "org/repo-2" in user_prompt

    def test_prompt_is_in_portuguese(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro"

        writer = CodigoWriter(client=mock_client)
        writer.write_report_intro([make_section()], week_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        assert "portugues" in system_prompt.lower() or "pt-br" in system_prompt.lower() or "editorial" in system_prompt.lower()

    def test_system_prompt_contains_dev_ecosystem_focus(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro"

        writer = CodigoWriter(client=mock_client)
        writer.write_report_intro([make_section()], week_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        # Should reference LATAM and developer ecosystem
        assert "LATAM" in system_prompt or "latam" in system_prompt.lower()

    def test_returns_none_on_empty_sections(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = CodigoWriter(client=mock_client)
        result = writer.write_report_intro([], week_number=1)

        assert result is None


class TestWriteSectionContent:
    """Test write_section_content()."""

    def test_returns_section_content_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "O setor de AI frameworks teve uma semana intensa.",
            "summaries": [
                "Resumo contextualizado do repo 1.",
                "Resumo contextualizado do repo 2.",
            ],
        })

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI Frameworks & Tools", signal_count=2)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "O setor de AI frameworks teve uma semana intensa."
        assert len(result.summaries) == 2
        assert result.summaries[0] == "Resumo contextualizado do repo 1."

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = CodigoWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = CodigoWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "This is not JSON at all"

        writer = CodigoWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None

    def test_returns_none_on_mismatched_summary_count(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro text",
            "summaries": ["Only one summary"],  # Section has 2 signals
        })

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        result = writer.write_section_content(section)

        assert result is None

    def test_prompt_contains_signal_titles_and_urls(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1", "s2"],
        })

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "org/repo-1" in user_prompt
        assert "org/repo-2" in user_prompt
        assert "https://github.com/org/repo-1" in user_prompt
        assert "https://github.com/org/repo-2" in user_prompt

    def test_prompt_contains_signal_summaries(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1", "s2"],
        })

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI", signal_count=2)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "Summary for repo 1" in user_prompt
        assert "Summary for repo 2" in user_prompt

    def test_prompt_requests_json_output(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1"],
        })

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI", signal_count=1)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "JSON" in user_prompt or "json" in user_prompt

    def test_single_signal_section(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Single signal intro",
            "summaries": ["Single summary"],
        })

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI", signal_count=1)
        result = writer.write_section_content(section)

        assert result is not None
        assert len(result.summaries) == 1

    def test_returns_none_on_empty_section(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = CodigoWriter(client=mock_client)
        section = ReportSection(heading="Empty", category_key="general", signals=[])
        result = writer.write_section_content(section)

        assert result is None

    def test_parses_json_wrapped_in_code_fences(self):
        """LLMs often wrap JSON in ```json ... ``` fences."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            '```json\n'
            '{\n'
            '  "intro": "Semana intensa para AI frameworks.",\n'
            '  "summaries": ["Resumo 1.", "Resumo 2."]\n'
            '}\n'
            '```'
        )

        writer = CodigoWriter(client=mock_client)
        section = make_section("AI & ML", signal_count=2)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "Semana intensa para AI frameworks."
        assert len(result.summaries) == 2

    def test_parses_json_wrapped_in_plain_code_fences(self):
        """Handle ``` without json language tag."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = (
            '```\n'
            '{"intro": "Intro text.", "summaries": ["s1"]}\n'
            '```'
        )

        writer = CodigoWriter(client=mock_client)
        section = make_section("Test", signal_count=1)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "Intro text."

    def test_prompt_includes_language_info(self):
        """Writer should include language in signal details."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1"],
        })

        writer = CodigoWriter(client=mock_client)
        section = ReportSection(
            heading="Test",
            category_key="ai_frameworks",
            signals=[make_analyzed_signal(language="rust")],
        )
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "rust" in user_prompt.lower()

    def test_prompt_includes_adoption_indicator(self):
        """Writer should include adoption indicator in signal details."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1"],
        })

        writer = CodigoWriter(client=mock_client)
        section = ReportSection(
            heading="Test",
            category_key="ai_frameworks",
            signals=[make_analyzed_signal(adoption_indicator="rising")],
        )
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "rising" in user_prompt.lower()
