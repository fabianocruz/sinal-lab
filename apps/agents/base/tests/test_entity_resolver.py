"""Tests for cross-agent entity resolution.

Tests deduplication and merging of EvidenceItems collected by multiple
agents, using URL matching and fuzzy title similarity.
"""

import pytest

from apps.agents.base.entity_resolver import ResolvedEntity, resolve_entities
from apps.agents.base.evidence import EvidenceItem, EvidenceType


def _make_item(
    title: str = "Test Article",
    url: str = "https://example.com/1",
    agent_name: str = "sintese",
    evidence_type: EvidenceType = EvidenceType.ARTICLE,
    confidence: float = 0.5,
    **kwargs: object,
) -> EvidenceItem:
    return EvidenceItem(
        title=title,
        url=url,
        source_name="test_source",
        evidence_type=evidence_type,
        agent_name=agent_name,
        confidence=confidence,
        **kwargs,
    )


class TestResolveEntities:
    """Test entity resolution across agents."""

    def test_exact_url_match_merges(self) -> None:
        items = [
            _make_item(title="AI Breakthrough", url="https://x.com/1", agent_name="sintese"),
            _make_item(title="AI Breakthrough", url="https://x.com/1", agent_name="radar"),
        ]
        result = resolve_entities(items)
        assert len(result) == 1
        assert len(result[0].source_agents) == 2
        assert "sintese" in result[0].source_agents
        assert "radar" in result[0].source_agents

    def test_different_urls_stay_separate(self) -> None:
        items = [
            _make_item(title="Article A", url="https://x.com/1"),
            _make_item(title="Article B", url="https://x.com/2"),
        ]
        result = resolve_entities(items)
        assert len(result) == 2

    def test_highest_confidence_becomes_canonical(self) -> None:
        items = [
            _make_item(url="https://x.com/1", agent_name="radar", confidence=0.3),
            _make_item(url="https://x.com/1", agent_name="sintese", confidence=0.8),
        ]
        result = resolve_entities(items)
        assert len(result) == 1
        assert result[0].canonical.agent_name == "sintese"
        assert result[0].canonical.confidence == 0.8

    def test_combined_confidence_boosted(self) -> None:
        items = [
            _make_item(url="https://x.com/1", agent_name="a1", confidence=0.6),
            _make_item(url="https://x.com/1", agent_name="a2", confidence=0.5),
        ]
        result = resolve_entities(items)
        assert len(result) == 1
        # max_conf=0.6 + 0.1*(2-1) = 0.7
        assert result[0].combined_confidence == pytest.approx(0.7, abs=0.01)

    def test_combined_confidence_capped_at_one(self) -> None:
        items = [
            _make_item(url="https://x.com/1", agent_name="a1", confidence=0.95),
            _make_item(url="https://x.com/1", agent_name="a2", confidence=0.9),
            _make_item(url="https://x.com/1", agent_name="a3", confidence=0.8),
        ]
        result = resolve_entities(items)
        assert result[0].combined_confidence <= 1.0

    def test_empty_list(self) -> None:
        result = resolve_entities([])
        assert result == []

    def test_single_item(self) -> None:
        items = [_make_item(confidence=0.7)]
        result = resolve_entities(items)
        assert len(result) == 1
        assert result[0].canonical.confidence == 0.7
        assert result[0].combined_confidence == 0.7
        assert result[0].duplicates == []
        assert len(result[0].source_agents) == 1

    def test_duplicates_list_excludes_canonical(self) -> None:
        items = [
            _make_item(url="https://x.com/1", agent_name="a1", confidence=0.8),
            _make_item(url="https://x.com/1", agent_name="a2", confidence=0.3),
        ]
        result = resolve_entities(items)
        assert len(result[0].duplicates) == 1
        assert result[0].duplicates[0].agent_name == "a2"

    def test_title_similarity_merges(self) -> None:
        """Fuzzy title match should merge items with different URLs."""
        items = [
            _make_item(
                title="Nubank raises $500M in Series G funding round",
                url="https://techcrunch.com/nubank",
                agent_name="sintese",
            ),
            _make_item(
                title="Nubank raises $500M in Series G funding round",
                url="https://reuters.com/nubank-funding",
                agent_name="funding",
            ),
        ]
        result = resolve_entities(items, title_similarity_threshold=0.85)
        assert len(result) == 1

    def test_low_similarity_stays_separate(self) -> None:
        items = [
            _make_item(title="Nubank funding round", url="https://x.com/1"),
            _make_item(title="Stone acquires new company", url="https://x.com/2"),
        ]
        result = resolve_entities(items, title_similarity_threshold=0.85)
        assert len(result) == 2

    def test_url_matching_disabled(self) -> None:
        """When url_exact=False, only title similarity is used."""
        items = [
            _make_item(title="Same Title Here", url="https://x.com/1", agent_name="a1"),
            _make_item(title="Same Title Here", url="https://x.com/1", agent_name="a2"),
        ]
        result = resolve_entities(items, url_exact=False, title_similarity_threshold=0.85)
        assert len(result) == 1

    def test_three_agents_same_url(self) -> None:
        items = [
            _make_item(url="https://x.com/1", agent_name="a1", confidence=0.5),
            _make_item(url="https://x.com/1", agent_name="a2", confidence=0.7),
            _make_item(url="https://x.com/1", agent_name="a3", confidence=0.6),
        ]
        result = resolve_entities(items)
        assert len(result) == 1
        assert len(result[0].source_agents) == 3
        # max_conf=0.7 + 0.1*(3-1) = 0.9
        assert result[0].combined_confidence == pytest.approx(0.9, abs=0.01)
