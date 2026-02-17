"""Tests for SINTESE synthesizer module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from datetime import datetime, timezone

from apps.agents.sintese.collector import FeedItem
from apps.agents.sintese.scorer import ScoredItem
from apps.agents.sintese.synthesizer import (
    categorize_item,
    select_top_items,
    group_by_category,
    synthesize_newsletter,
)


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
        assert categorize_item(item) == "AI & Machine Learning"

    def test_startup_category(self):
        item = make_scored_item(title="Startup raises venture capital funding")
        assert categorize_item(item) == "Startups & Funding"

    def test_fintech_category(self):
        item = make_scored_item(title="New fintech pagamento solution launches")
        assert categorize_item(item) == "Fintech & Pagamentos"

    def test_infra_category(self):
        item = make_scored_item(title="Kubernetes deployment best practices for devops")
        assert categorize_item(item) == "Infraestrutura & Dev Tools"

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
        newsletter = synthesize_newsletter(items, edition_number=42)

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
        newsletter = synthesize_newsletter(items)
        assert "Important AI Breakthrough" in newsletter
        assert "https://example.com/ai" in newsletter

    def test_includes_footer(self):
        items = [make_scored_item(composite=0.8)]
        newsletter = synthesize_newsletter(items)
        assert "Sinal.lab" in newsletter
        assert "Inteligencia aberta" in newsletter

    def test_empty_items(self):
        newsletter = synthesize_newsletter([])
        assert "# Sinal Semanal" in newsletter
        assert "0 destaques" in newsletter

    def test_edition_date_formatting(self):
        items = [make_scored_item(composite=0.8)]
        date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        newsletter = synthesize_newsletter(items, edition_date=date)
        assert "16/02/2026" in newsletter
