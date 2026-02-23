"""Tests for SINTESE editorial writer (LLM-powered content generation)."""

import json
import os

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from apps.agents.sintese.collector import FeedItem
from apps.agents.sintese.scorer import ScoredItem
from apps.agents.sintese.synthesizer import NewsletterSection
from apps.agents.base.llm import strip_code_fences
from apps.agents.sintese.writer import SinteseWriter, SectionContent, EditorialMetadata


def make_scored_item(
    title: str = "Test Article",
    url: str = "https://example.com/test",
    source_name: str = "test_source",
    composite: float = 0.5,
    summary: str = "A test article summary.",
) -> ScoredItem:
    """Helper to create a ScoredItem with defaults."""
    item = FeedItem(
        title=title,
        url=url,
        source_name=source_name,
        summary=summary,
        published_at=datetime.now(timezone.utc),
    )
    return ScoredItem(
        item=item,
        topic_score=composite,
        recency_score=composite,
        authority_score=composite,
        latam_score=composite,
    )


def make_section(heading: str = "AI & Machine Learning", item_count: int = 2) -> NewsletterSection:
    """Helper to create a NewsletterSection with items."""
    items = [
        make_scored_item(
            title=f"Article {i}",
            url=f"https://example.com/{i}",
            source_name=f"source_{i}",
            summary=f"Summary for article {i}.",
        )
        for i in range(1, item_count + 1)
    ]
    return NewsletterSection(heading=heading, items=items)


class TestSectionContent:
    """Test SectionContent dataclass."""

    def test_dataclass_fields(self):
        sc = SectionContent(intro="Section intro", summaries=["s1", "s2"])
        assert sc.intro == "Section intro"
        assert sc.summaries == ["s1", "s2"]


class TestSinteseWriterAvailability:
    """Test SinteseWriter.is_available property."""

    def test_is_available_delegates_to_client_true(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        writer = SinteseWriter(client=mock_client)
        assert writer.is_available is True

    def test_is_available_delegates_to_client_false(self):
        mock_client = MagicMock()
        mock_client.is_available = False
        writer = SinteseWriter(client=mock_client)
        assert writer.is_available is False

    def test_is_available_false_when_no_client(self):
        with patch.dict(os.environ, {}, clear=True):
            writer = SinteseWriter(client=None)
            assert writer.is_available is False


class TestWriteNewsletterIntro:
    """Test write_newsletter_intro()."""

    def test_returns_string_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Esta semana, o ecossistema tech foi marcado por avancos em AI."

        writer = SinteseWriter(client=mock_client)
        sections = [make_section("AI & Machine Learning"), make_section("Startups & Funding")]
        result = writer.write_newsletter_intro(sections, edition_number=42)

        assert result == "Esta semana, o ecossistema tech foi marcado por avancos em AI."

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = SinteseWriter(client=mock_client)
        result = writer.write_newsletter_intro([make_section()], edition_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = SinteseWriter(client=mock_client)
        result = writer.write_newsletter_intro([make_section()], edition_number=1)

        assert result is None

    def test_prompt_contains_section_headings(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text"

        writer = SinteseWriter(client=mock_client)
        sections = [
            make_section("AI & Machine Learning"),
            make_section("Startups & Funding"),
        ]
        writer.write_newsletter_intro(sections, edition_number=1)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "AI & Machine Learning" in user_prompt
        assert "Startups & Funding" in user_prompt

    def test_prompt_contains_item_titles(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro text"

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI", item_count=2)
        writer.write_newsletter_intro([section], edition_number=1)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "Article 1" in user_prompt
        assert "Article 2" in user_prompt

    def test_prompt_is_in_portuguese(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro"

        writer = SinteseWriter(client=mock_client)
        writer.write_newsletter_intro([make_section()], edition_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        assert "portugues" in system_prompt.lower() or "pt-br" in system_prompt.lower() or "editorial" in system_prompt.lower()

    def test_system_prompt_contains_editorial_voice(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "Intro"

        writer = SinteseWriter(client=mock_client)
        writer.write_newsletter_intro([make_section()], edition_number=1)

        call_kwargs = mock_client.generate.call_args[1]
        system_prompt = call_kwargs.get("system_prompt", "")
        # Should reference anti-hype and LATAM focus
        assert "LATAM" in system_prompt or "latam" in system_prompt.lower()

    def test_returns_none_on_empty_sections(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = SinteseWriter(client=mock_client)
        result = writer.write_newsletter_intro([], edition_number=1)

        assert result is None


class TestWriteSectionContent:
    """Test write_section_content()."""

    def test_returns_section_content_on_success(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "O setor de AI teve uma semana intensa.",
            "summaries": [
                "Resumo contextualizado do artigo 1.",
                "Resumo contextualizado do artigo 2.",
            ],
        })

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI & Machine Learning", item_count=2)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "O setor de AI teve uma semana intensa."
        assert len(result.summaries) == 2
        assert result.summaries[0] == "Resumo contextualizado do artigo 1."

    def test_returns_none_when_client_unavailable(self):
        mock_client = MagicMock()
        mock_client.is_available = False

        writer = SinteseWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None
        mock_client.generate.assert_not_called()

    def test_returns_none_when_generate_fails(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = None

        writer = SinteseWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = "This is not JSON at all"

        writer = SinteseWriter(client=mock_client)
        result = writer.write_section_content(make_section())

        assert result is None

    def test_returns_none_on_mismatched_summary_count(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro text",
            "summaries": ["Only one summary"],  # Section has 2 items
        })

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI", item_count=2)
        result = writer.write_section_content(section)

        assert result is None

    def test_prompt_contains_item_titles_and_urls(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1", "s2"],
        })

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI", item_count=2)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "Article 1" in user_prompt
        assert "Article 2" in user_prompt
        assert "https://example.com/1" in user_prompt
        assert "https://example.com/2" in user_prompt

    def test_prompt_contains_item_summaries(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1", "s2"],
        })

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI", item_count=2)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "Summary for article 1" in user_prompt
        assert "Summary for article 2" in user_prompt

    def test_prompt_requests_json_output(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Intro", "summaries": ["s1"],
        })

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI", item_count=1)
        writer.write_section_content(section)

        user_prompt = mock_client.generate.call_args[1].get("user_prompt") or mock_client.generate.call_args[0][0]
        assert "JSON" in user_prompt or "json" in user_prompt

    def test_single_item_section(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = json.dumps({
            "intro": "Single item intro",
            "summaries": ["Single summary"],
        })

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI", item_count=1)
        result = writer.write_section_content(section)

        assert result is not None
        assert len(result.summaries) == 1

    def test_returns_none_on_empty_section(self):
        mock_client = MagicMock()
        mock_client.is_available = True

        writer = SinteseWriter(client=mock_client)
        section = NewsletterSection(heading="Empty", items=[])
        result = writer.write_section_content(section)

        assert result is None

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

        writer = SinteseWriter(client=mock_client)
        section = make_section("AI & ML", item_count=2)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "Semana intensa para AI."
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

        writer = SinteseWriter(client=mock_client)
        section = make_section("Test", item_count=1)
        result = writer.write_section_content(section)

        assert result is not None
        assert result.intro == "Intro text."


class TestStripCodeFences:
    """Test strip_code_fences() shared utility."""

    def test_strips_json_code_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        assert strip_code_fences(raw) == '{"key": "value"}'

    def test_strips_plain_code_fence(self):
        raw = '```\n{"key": "value"}\n```'
        assert strip_code_fences(raw) == '{"key": "value"}'

    def test_returns_plain_json_unchanged(self):
        raw = '{"key": "value"}'
        assert strip_code_fences(raw) == '{"key": "value"}'

    def test_handles_whitespace_around_fences(self):
        raw = '  ```json\n{"key": "value"}\n```  '
        assert strip_code_fences(raw) == '{"key": "value"}'

    def test_handles_multiline_json(self):
        raw = '```json\n{\n  "intro": "text",\n  "summaries": ["a", "b"]\n}\n```'
        result = strip_code_fences(raw)
        data = json.loads(result)
        assert data["intro"] == "text"
        assert len(data["summaries"]) == 2


class TestWriteEditorialMetadata:
    """Test write_editorial_metadata() on SinteseWriter."""

    def _make_writer_with_response(self, response: str) -> SinteseWriter:
        """Create a SinteseWriter whose LLM client returns a fixed response."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.generate.return_value = response
        return SinteseWriter(client=mock_client)

    def test_write_editorial_metadata_returns_metadata_on_valid_json(self):
        """Valid JSON response returns an EditorialMetadata instance."""
        payload = json.dumps({
            "callouts": [
                {"type": "highlight", "content": "Nubank atingiu 100M de clientes.", "position": "after_intro"},
            ],
            "companies_mentioned": ["Nubank", "Rappi", "Totvs"],
            "topics": ["fintech", "AI", "open finance"],
            "featured_video_url": None,
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("Fintech & Pagamentos", item_count=2)]

        result = writer.write_editorial_metadata(sections, edition_number=5)

        assert result is not None
        assert isinstance(result, EditorialMetadata)
        assert len(result.callouts) == 1
        assert result.callouts[0]["content"] == "Nubank atingiu 100M de clientes."
        assert "Nubank" in result.companies_mentioned
        assert "fintech" in result.topics

    def test_write_editorial_metadata_returns_none_when_client_unavailable(self):
        """Returns None when the LLM client is not available."""
        mock_client = MagicMock()
        mock_client.is_available = False
        writer = SinteseWriter(client=mock_client)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_write_editorial_metadata_returns_none_on_invalid_json(self):
        """Garbage response that is not valid JSON returns None."""
        writer = self._make_writer_with_response("This is definitely not JSON!")
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is None

    def test_write_editorial_metadata_handles_code_fences(self):
        """JSON wrapped in ```json...``` fences is parsed correctly."""
        payload = (
            "```json\n"
            + json.dumps({
                "callouts": [{"type": "highlight", "content": "Insight importante.", "position": "after_intro"}],
                "companies_mentioned": ["Startup X"],
                "topics": ["AI", "cloud"],
                "featured_video_url": None,
            })
            + "\n```"
        )
        writer = self._make_writer_with_response(payload)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is not None
        assert isinstance(result, EditorialMetadata)
        assert result.callouts[0]["content"] == "Insight importante."

    def test_write_editorial_metadata_validates_callout_structure(self):
        """Callouts missing the 'content' key are filtered out."""
        payload = json.dumps({
            "callouts": [
                {"type": "highlight", "content": "Valid callout.", "position": "after_intro"},
                {"type": "highlight"},  # No 'content' key — invalid
                {"type": "highlight", "content": "Another valid callout."},
            ],
            "companies_mentioned": [],
            "topics": [],
            "featured_video_url": None,
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is not None
        # The callout without 'content' was filtered out
        assert len(result.callouts) == 2
        contents = [c["content"] for c in result.callouts]
        assert "Valid callout." in contents
        assert "Another valid callout." in contents

    def test_write_editorial_metadata_limits_companies_to_20(self):
        """companies_mentioned list is capped at 20 entries."""
        payload = json.dumps({
            "callouts": [],
            "companies_mentioned": [f"Company {i}" for i in range(30)],
            "topics": ["AI"],
            "featured_video_url": None,
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is not None
        assert len(result.companies_mentioned) == 20

    def test_write_editorial_metadata_limits_topics_to_10(self):
        """topics list is capped at 10 entries."""
        payload = json.dumps({
            "callouts": [],
            "companies_mentioned": [],
            "topics": [f"topic_{i}" for i in range(15)],
            "featured_video_url": None,
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is not None
        assert len(result.topics) == 10

    def test_write_editorial_metadata_returns_none_on_empty_sections(self):
        """Empty sections list returns None without calling LLM."""
        mock_client = MagicMock()
        mock_client.is_available = True
        writer = SinteseWriter(client=mock_client)

        result = writer.write_editorial_metadata([], edition_number=1)

        assert result is None
        mock_client.generate.assert_not_called()

    def test_write_editorial_metadata_featured_video_url_set_from_item(self):
        """featured_video_url is returned when LLM includes it."""
        payload = json.dumps({
            "callouts": [],
            "companies_mentioned": [],
            "topics": ["AI"],
            "featured_video_url": "https://youtube.com/watch?v=abc123",
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is not None
        assert result.featured_video_url == "https://youtube.com/watch?v=abc123"

    def test_write_editorial_metadata_featured_video_url_none_when_not_string(self):
        """featured_video_url is None when LLM returns a non-string value."""
        payload = json.dumps({
            "callouts": [],
            "companies_mentioned": [],
            "topics": ["AI"],
            "featured_video_url": 42,  # Not a string
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is not None
        assert result.featured_video_url is None

    def test_write_editorial_metadata_returns_none_on_invalid_structure(self):
        """JSON where callouts/companies/topics are not lists returns None."""
        payload = json.dumps({
            "callouts": "not a list",
            "companies_mentioned": ["ok"],
            "topics": ["ok"],
            "featured_video_url": None,
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("AI", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is None

    def test_write_editorial_metadata_empty_callouts_are_valid(self):
        """JSON with empty callouts list is still valid."""
        payload = json.dumps({
            "callouts": [],
            "companies_mentioned": ["Nubank"],
            "topics": ["fintech"],
            "featured_video_url": None,
        })
        writer = self._make_writer_with_response(payload)
        sections = [make_section("Fintech", item_count=1)]

        result = writer.write_editorial_metadata(sections, edition_number=1)

        assert result is not None
        assert isinstance(result, EditorialMetadata)
        assert result.callouts == []
        assert result.companies_mentioned == ["Nubank"]
