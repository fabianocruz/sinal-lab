"""Tests for EvidenceItem unified data model.

EvidenceItem is the shared contract for cross-agent operations:
deduplication, editorial review, entity resolution, and publishing.
All agent-specific types (FeedItem, TrendSignal, DevSignal, etc.)
can be converted to EvidenceItem via the normalizer.
"""

from datetime import datetime, timezone

import pytest

from apps.agents.base.evidence import EvidenceItem, EvidenceType


class TestEvidenceType:
    """Test EvidenceType enum values."""

    def test_article_value(self) -> None:
        assert EvidenceType.ARTICLE == "article"

    def test_repo_value(self) -> None:
        assert EvidenceType.REPO == "repo"

    def test_package_value(self) -> None:
        assert EvidenceType.PACKAGE == "package"

    def test_funding_event_value(self) -> None:
        assert EvidenceType.FUNDING_EVENT == "funding_event"

    def test_company_profile_value(self) -> None:
        assert EvidenceType.COMPANY_PROFILE == "company_profile"

    def test_tweet_value(self) -> None:
        assert EvidenceType.TWEET == "tweet"

    def test_string_conversion(self) -> None:
        assert str(EvidenceType.ARTICLE) == "EvidenceType.ARTICLE"
        assert EvidenceType.ARTICLE.value == "article"

    def test_all_types_exist(self) -> None:
        expected = {"article", "repo", "package", "funding_event", "company_profile", "tweet"}
        actual = {t.value for t in EvidenceType}
        assert actual == expected


class TestEvidenceItem:
    """Test EvidenceItem dataclass."""

    def test_create_with_required_fields(self) -> None:
        item = EvidenceItem(
            title="Test Article",
            url="https://example.com/article",
            source_name="hn_best",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="sintese",
        )
        assert item.title == "Test Article"
        assert item.url == "https://example.com/article"
        assert item.source_name == "hn_best"
        assert item.evidence_type == EvidenceType.ARTICLE
        assert item.agent_name == "sintese"

    def test_auto_content_hash_from_url(self) -> None:
        item = EvidenceItem(
            title="Test",
            url="https://example.com/test",
            source_name="src",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="radar",
        )
        assert item.content_hash != ""
        assert len(item.content_hash) == 32
        assert all(c in "0123456789abcdef" for c in item.content_hash)

    def test_manual_content_hash_preserved(self) -> None:
        item = EvidenceItem(
            title="Test",
            url="https://example.com/test",
            source_name="src",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="radar",
            content_hash="custom_hash_value",
        )
        assert item.content_hash == "custom_hash_value"

    def test_same_url_same_hash(self) -> None:
        item1 = EvidenceItem(
            title="A",
            url="https://example.com/same",
            source_name="s1",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="a1",
        )
        item2 = EvidenceItem(
            title="B",
            url="https://example.com/same",
            source_name="s2",
            evidence_type=EvidenceType.REPO,
            agent_name="a2",
        )
        assert item1.content_hash == item2.content_hash

    def test_different_url_different_hash(self) -> None:
        item1 = EvidenceItem(
            title="A",
            url="https://example.com/1",
            source_name="s",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="a",
        )
        item2 = EvidenceItem(
            title="A",
            url="https://example.com/2",
            source_name="s",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="a",
        )
        assert item1.content_hash != item2.content_hash

    def test_default_values(self) -> None:
        item = EvidenceItem(
            title="T",
            url="https://x.com",
            source_name="s",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="a",
        )
        assert item.published_at is None
        assert item.summary is None
        assert item.author is None
        assert item.tags == []
        assert item.confidence == 0.5
        assert item.territory is None
        assert item.metrics == {}
        assert item.raw_data == {}
        assert item.provenance is None

    def test_full_item(self) -> None:
        now = datetime.now(timezone.utc)
        item = EvidenceItem(
            title="Nubank raises $500M",
            url="https://example.com/nubank",
            source_name="techcrunch_feed",
            evidence_type=EvidenceType.FUNDING_EVENT,
            agent_name="funding",
            published_at=now,
            summary="Nubank announced a $500M Series G round",
            author="John Doe",
            tags=["fintech", "latam"],
            confidence=0.85,
            territory="financas",
            metrics={"amount_usd": 500000000},
            raw_data={"round_type": "series_g", "lead_investors": ["Sequoia"]},
        )
        assert item.published_at == now
        assert item.confidence == 0.85
        assert item.territory == "financas"
        assert item.metrics["amount_usd"] == 500000000
        assert item.raw_data["round_type"] == "series_g"

    def test_confidence_default(self) -> None:
        item = EvidenceItem(
            title="T",
            url="https://x.com",
            source_name="s",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="a",
        )
        assert item.confidence == 0.5

    def test_confidence_custom(self) -> None:
        item = EvidenceItem(
            title="T",
            url="https://x.com",
            source_name="s",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="a",
            confidence=0.9,
        )
        assert item.confidence == 0.9

    def test_to_dict_serialization(self) -> None:
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        item = EvidenceItem(
            title="Test Article",
            url="https://example.com/test",
            source_name="hn_best",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="sintese",
            published_at=now,
            summary="A summary",
            tags=["ai", "ml"],
            confidence=0.7,
            territory="codigo",
        )
        d = item.to_dict()

        assert d["title"] == "Test Article"
        assert d["url"] == "https://example.com/test"
        assert d["source_name"] == "hn_best"
        assert d["evidence_type"] == "article"
        assert d["agent_name"] == "sintese"
        assert d["published_at"] == "2026-02-17T12:00:00+00:00"
        assert d["summary"] == "A summary"
        assert d["tags"] == ["ai", "ml"]
        assert d["confidence"] == 0.7
        assert d["territory"] == "codigo"
        assert d["content_hash"] != ""

    def test_to_dict_none_published_at(self) -> None:
        item = EvidenceItem(
            title="T",
            url="https://x.com",
            source_name="s",
            evidence_type=EvidenceType.ARTICLE,
            agent_name="a",
        )
        d = item.to_dict()
        assert d["published_at"] is None

    def test_evidence_type_from_string(self) -> None:
        assert EvidenceType("article") == EvidenceType.ARTICLE
        assert EvidenceType("repo") == EvidenceType.REPO
        assert EvidenceType("funding_event") == EvidenceType.FUNDING_EVENT
