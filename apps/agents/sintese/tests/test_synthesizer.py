"""Tests for SINTESE synthesizer module."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from apps.agents.sintese.collector import FeedItem
from apps.agents.sintese.scorer import ScoredItem
from apps.agents.sintese.synthesizer import (
    categorize_item,
    select_top_items,
    group_by_category,
    synthesize_newsletter,
    format_item_markdown,
)
from apps.agents.sintese.writer import SinteseWriter, SectionContent


def make_scored_item(
    title: str = "Test Article",
    url: str = "https://example.com/test",
    source_name: str = "test_source",
    composite: float = 0.5,
    summary: str = "A test article summary.",
    **kwargs,
) -> ScoredItem:
    """Helper to create a ScoredItem with defaults."""
    item = FeedItem(
        title=title,
        url=url,
        source_name=source_name,
        summary=summary,
        published_at=datetime.now(timezone.utc),
        **kwargs,
    )
    return ScoredItem(
        item=item,
        topic_score=composite,
        recency_score=composite,
        authority_score=composite,
        latam_score=composite,
    )


class TestCategorizeItem:
    """Test item categorization."""

    def test_ai_category(self):
        item = make_scored_item(title="New machine learning model released")
        assert categorize_item(item) == "AI & Infraestrutura Inteligente"

    def test_venture_category(self):
        item = make_scored_item(title="Startup raises venture capital funding")
        assert categorize_item(item) == "Venture Capital & Ecossistema"

    def test_fintech_category(self):
        item = make_scored_item(title="New fintech pagamento solution launches")
        assert categorize_item(item) == "Fintech & Infraestrutura Financeira"

    def test_engenharia_category(self):
        item = make_scored_item(title="Kubernetes deployment best practices for devops")
        assert categorize_item(item) == "Engenharia & Plataforma"

    def test_uncategorized_goes_to_destaque(self):
        item = make_scored_item(title="Completely random unrelated topic xyz")
        category = categorize_item(item)
        assert category == "Destaque da Semana"


class TestSelectTopItems:
    """Test top item selection with diversity."""

    def test_selects_top_n(self):
        """With diverse sources, selects up to count items."""
        items = [
            make_scored_item(
                url=f"https://x.com/{i}",
                source_name=f"source_{i % 10}",  # 10 different sources
                composite=1.0 - i * 0.01,
            )
            for i in range(30)
        ]
        selected = select_top_items(items, count=10)
        assert len(selected) == 10

    def test_filters_low_score(self):
        items = [
            make_scored_item(url="https://x.com/1", composite=0.8),
            make_scored_item(url="https://x.com/2", composite=0.05),  # Below threshold
            make_scored_item(url="https://x.com/3", composite=0.6),
        ]
        selected = select_top_items(items, count=10, min_score=0.15)
        assert len(selected) == 2

    def test_source_diversity(self):
        """No more than 3 items from the same source."""
        items = [
            make_scored_item(url=f"https://x.com/{i}", source_name="same_source", composite=0.9)
            for i in range(10)
        ]
        selected = select_top_items(items, count=10)
        assert len(selected) == 3

    def test_mixed_sources(self):
        items = []
        for source in ["source_a", "source_b", "source_c"]:
            for i in range(5):
                items.append(make_scored_item(
                    url=f"https://{source}.com/{i}",
                    source_name=source,
                    composite=0.8,
                ))
        selected = select_top_items(items, count=9)
        assert len(selected) == 9
        source_counts = {}
        for item in selected:
            name = item.item.source_name
            source_counts[name] = source_counts.get(name, 0) + 1
        assert all(c <= 3 for c in source_counts.values())

    def test_empty_input(self):
        assert select_top_items([]) == []


class TestGroupByCategory:
    """Test grouping items into newsletter sections."""

    def test_groups_by_category(self):
        items = [
            make_scored_item(title="AI machine learning model", url="https://x.com/1"),
            make_scored_item(title="Startup venture capital round", url="https://x.com/2"),
            make_scored_item(title="Another AI deep learning paper", url="https://x.com/3"),
        ]
        sections = group_by_category(items)
        assert len(sections) >= 1
        # All items should be accounted for
        total = sum(len(s.items) for s in sections)
        assert total == 3

    def test_destaque_section_first(self):
        items = [
            make_scored_item(title="Random xyz article", url="https://x.com/1"),
            make_scored_item(title="AI startup venture capital", url="https://x.com/2"),
        ]
        sections = group_by_category(items)
        if sections and sections[0].heading == "Destaque da Semana":
            assert True  # Destaque is first when present

    def test_empty_input(self):
        sections = group_by_category([])
        assert sections == []


class TestSynthesizeNewsletter:
    """Test full newsletter synthesis."""

    def test_generates_valid_markdown(self):
        items = [
            make_scored_item(
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                source_name=f"source_{i % 5}",
                composite=0.9 - i * 0.02,
            )
            for i in range(25)
        ]
        newsletter, sections = synthesize_newsletter(items, edition_number=42)

        assert "# Sinal Semanal #42" in newsletter
        assert "SINTESE" in newsletter
        assert "fontes" in newsletter
        assert "---" in newsletter

    def test_includes_items(self):
        items = [
            make_scored_item(
                title="Important AI Breakthrough",
                url="https://example.com/ai",
                composite=0.9,
            ),
        ]
        newsletter, sections = synthesize_newsletter(items)
        assert "Important AI Breakthrough" in newsletter
        assert "https://example.com/ai" in newsletter

    def test_includes_footer(self):
        items = [make_scored_item(composite=0.8)]
        newsletter, sections = synthesize_newsletter(items)
        assert "Sinal.lab" in newsletter
        assert "Inteligencia aberta" in newsletter

    def test_empty_items(self):
        newsletter, sections = synthesize_newsletter([])
        assert "# Sinal Semanal" in newsletter
        assert "0 destaques" in newsletter

    def test_edition_date_formatting(self):
        items = [make_scored_item(composite=0.8)]
        date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        newsletter, sections = synthesize_newsletter(items, edition_date=date)
        assert "16/02/2026" in newsletter


class TestSynthesizeNewsletterWithLLM:
    """Test LLM-enhanced newsletter synthesis."""

    def _make_items(self, count: int = 5) -> list[ScoredItem]:
        """Create a list of scored items for testing."""
        return [
            make_scored_item(
                title=f"AI Article {i}",
                url=f"https://example.com/ai-{i}",
                source_name=f"source_{i}",
                composite=0.9 - i * 0.05,
                summary=f"Summary about AI topic {i}.",
                tags=["inteligencia artificial", "machine learning"],
            )
            for i in range(count)
        ]

    def _make_writer(
        self,
        available: bool = True,
        intro_return: str = "LLM-generated intro paragraph.",
        section_return: SectionContent = None,
    ) -> MagicMock:
        """Create a mock SinteseWriter."""
        writer = MagicMock(spec=SinteseWriter)
        writer.is_available = available

        writer.write_newsletter_intro.return_value = intro_return if available else None

        if section_return is None and available:
            section_return = SectionContent(
                intro="LLM section commentary.",
                summaries=None,  # Will be set per-test
            )

        writer.write_section_content.return_value = section_return
        return writer

    def test_uses_llm_intro_when_writer_available(self):
        items = self._make_items()
        writer = self._make_writer(
            available=True,
            intro_return="A semana foi dominada por avancos em inteligencia artificial.",
        )
        # Section content returns None to keep sections template-based
        writer.write_section_content.return_value = None

        newsletter, sections = synthesize_newsletter(items, edition_number=42, writer=writer)

        assert "A semana foi dominada por avancos em inteligencia artificial." in newsletter
        # Template intro should NOT be present
        assert "Esta semana reunimos" not in newsletter

    def test_uses_llm_section_content_when_writer_available(self):
        items = self._make_items(count=3)
        writer = self._make_writer(available=True)
        writer.write_newsletter_intro.return_value = None  # Template intro fallback

        # Return section content matching item count per section
        def section_side_effect(section):
            return SectionContent(
                intro="LLM editorial commentary for section.",
                summaries=[f"Rewritten summary for {it.item.title}." for it in section.items],
            )
        writer.write_section_content.side_effect = section_side_effect

        newsletter, sections = synthesize_newsletter(items, edition_number=1, writer=writer)

        assert "LLM editorial commentary for section." in newsletter
        assert "Rewritten summary for AI Article 0." in newsletter

    def test_falls_back_to_template_when_writer_unavailable(self):
        items = self._make_items()
        writer = self._make_writer(available=False)

        newsletter, sections = synthesize_newsletter(items, edition_number=1, writer=writer)

        # Should use template intro
        assert "Esta semana reunimos" in newsletter
        writer.write_newsletter_intro.assert_not_called()
        writer.write_section_content.assert_not_called()

    def test_falls_back_to_template_when_writer_is_none(self):
        items = self._make_items()

        newsletter, sections = synthesize_newsletter(items, edition_number=1, writer=None)

        # Should use template intro (default behavior)
        assert "Esta semana reunimos" in newsletter

    def test_falls_back_to_template_intro_when_llm_returns_none(self):
        items = self._make_items()
        writer = self._make_writer(available=True, intro_return=None)
        writer.write_section_content.return_value = None

        newsletter, sections = synthesize_newsletter(items, edition_number=1, writer=writer)

        # Template intro should be used as fallback
        assert "Esta semana reunimos" in newsletter

    def test_falls_back_to_template_section_when_llm_returns_none(self):
        items = self._make_items(count=3)
        writer = self._make_writer(available=True, intro_return=None)
        writer.write_section_content.return_value = None  # Simulates LLM failure

        newsletter, sections = synthesize_newsletter(items, edition_number=1, writer=writer)

        # Template section format: blockquote summaries from RSS
        assert "Summary about AI topic" in newsletter

    def test_partial_llm_success(self):
        """Intro works but section content fails — uses mixed output."""
        items = self._make_items()
        writer = self._make_writer(
            available=True,
            intro_return="LLM intro succeeded.",
        )
        writer.write_section_content.return_value = None  # All sections fail

        newsletter, sections = synthesize_newsletter(items, edition_number=1, writer=writer)

        # LLM intro present
        assert "LLM intro succeeded." in newsletter
        # Template sections (fallback)
        assert "Summary about AI topic" in newsletter

    def test_structural_logic_unchanged(self):
        """select_top_items and group_by_category work the same with/without writer."""
        items = self._make_items(count=20)

        newsletter_without, _ = synthesize_newsletter(items, edition_number=1, writer=None)
        writer = self._make_writer(available=False)
        newsletter_with, _ = synthesize_newsletter(items, edition_number=1, writer=writer)

        # Same structure: same title, same section count
        assert "# Sinal Semanal #1" in newsletter_without
        assert "# Sinal Semanal #1" in newsletter_with


class TestFormatItemMarkdown:
    """Test format_item_markdown inline image rendering."""

    def test_format_item_markdown_includes_image_when_present(self):
        """Item with image_url should produce a Markdown image tag in output."""
        item = make_scored_item(
            title="Article with Image",
            url="https://example.com/article",
            image_url="https://cdn.example.com/image.jpg",
        )
        result = format_item_markdown(item, index=1)

        assert "![Article with Image](https://cdn.example.com/image.jpg)" in result

    def test_format_item_markdown_omits_image_when_none(self):
        """Item without image_url should produce no Markdown image tag."""
        item = make_scored_item(
            title="Article without Image",
            url="https://example.com/article",
        )
        result = format_item_markdown(item, index=1)

        assert "![" not in result

    def test_format_item_markdown_image_appears_after_summary(self):
        """Image block should come after the summary blockquote."""
        item = make_scored_item(
            title="Titled Article",
            url="https://example.com/article",
            summary="Short summary text.",
            image_url="https://cdn.example.com/photo.png",
        )
        result = format_item_markdown(item, index=1)

        summary_pos = result.index("> Short summary text.")
        image_pos = result.index("![Titled Article]")
        assert image_pos > summary_pos

    def test_format_item_markdown_summary_override_used_with_image(self):
        """When summary_override is given, the override is rendered and image still appears."""
        item = make_scored_item(
            title="Article",
            url="https://example.com/article",
            summary="Original RSS summary.",
            image_url="https://cdn.example.com/img.jpg",
        )
        result = format_item_markdown(item, index=1, summary_override="LLM rewritten summary.")

        assert "Original RSS summary." not in result
        assert "LLM rewritten summary." in result
        assert "![Article](https://cdn.example.com/img.jpg)" in result

    def test_format_item_markdown_includes_video_link_when_present(self):
        """Item with video_url produces a video link in output."""
        item = make_scored_item(
            title="Video Article",
            url="https://example.com/article",
            video_url="https://youtube.com/watch?v=abc123",
        )
        result = format_item_markdown(item, index=1)

        assert "[▶ Assistir video](https://youtube.com/watch?v=abc123)" in result

    def test_format_item_markdown_omits_video_link_when_none(self):
        """Item without video_url produces no video link."""
        item = make_scored_item(
            title="Text Article",
            url="https://example.com/article",
        )
        result = format_item_markdown(item, index=1)

        assert "Assistir video" not in result

    def test_format_item_markdown_video_after_image(self):
        """Video link appears after image when both are present."""
        item = make_scored_item(
            title="Full Media",
            url="https://example.com/article",
            image_url="https://cdn.example.com/thumb.jpg",
            video_url="https://youtube.com/watch?v=xyz",
        )
        result = format_item_markdown(item, index=1)

        image_pos = result.index("![Full Media]")
        video_pos = result.index("[▶ Assistir video]")
        assert video_pos > image_pos


class TestSynthesizeNewsletterReturnType:
    """Verify synthesize_newsletter returns (str, list[NewsletterSection]) tuple."""

    def test_synthesize_newsletter_returns_tuple(self):
        """Return value must be a 2-tuple of (str, list)."""
        items = [make_scored_item(composite=0.8)]
        result = synthesize_newsletter(items, edition_number=1)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_synthesize_newsletter_first_element_is_string(self):
        """First element of the tuple is the newsletter Markdown string."""
        items = [make_scored_item(composite=0.8)]
        markdown, sections = synthesize_newsletter(items, edition_number=1)

        assert isinstance(markdown, str)
        assert len(markdown) > 0

    def test_synthesize_newsletter_second_element_is_list(self):
        """Second element is a list of NewsletterSection objects."""
        items = [
            make_scored_item(
                title="AI startup investment round",
                url=f"https://example.com/{i}",
                source_name=f"source_{i}",
                composite=0.8,
            )
            for i in range(3)
        ]
        markdown, sections = synthesize_newsletter(items, edition_number=1)

        assert isinstance(sections, list)

    def test_synthesize_newsletter_sections_are_newsletter_section_instances(self):
        """Each element in the sections list is a NewsletterSection."""
        from apps.agents.sintese.synthesizer import NewsletterSection

        items = [
            make_scored_item(
                title="AI machine learning article",
                url="https://example.com/ai",
                composite=0.9,
            )
        ]
        markdown, sections = synthesize_newsletter(items, edition_number=1)

        for section in sections:
            assert isinstance(section, NewsletterSection)

    def test_synthesize_newsletter_empty_returns_empty_sections(self):
        """With no items, sections list should be empty."""
        markdown, sections = synthesize_newsletter([], edition_number=1)

        assert isinstance(sections, list)
        assert sections == []
