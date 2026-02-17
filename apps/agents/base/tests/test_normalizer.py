"""Tests for evidence normalizer.

Tests the conversion of agent-specific types (FeedItem, TrendSignal,
DevSignal, FundingEvent, CompanyProfile) into EvidenceItem.
"""

from datetime import date, datetime, timezone

import pytest

from apps.agents.base.evidence import EvidenceItem, EvidenceType
from apps.agents.base.normalizer import (
    normalize_any,
    normalize_company_profile,
    normalize_dev_signal,
    normalize_feed_item,
    normalize_funding_event,
    normalize_trend_signal,
)
from apps.agents.codigo.collector import DevSignal
from apps.agents.funding.collector import FundingEvent
from apps.agents.mercado.collector import CompanyProfile
from apps.agents.radar.collector import TrendSignal
from apps.agents.sintese.collector import FeedItem


class TestNormalizeFeedItem:
    """Test SINTESE FeedItem → EvidenceItem conversion."""

    def test_required_fields_mapped(self) -> None:
        item = FeedItem(
            title="Test Article",
            url="https://example.com/article",
            source_name="hn_best",
        )
        result = normalize_feed_item(item, "sintese")
        assert result.title == "Test Article"
        assert result.url == "https://example.com/article"
        assert result.source_name == "hn_best"
        assert result.evidence_type == EvidenceType.ARTICLE
        assert result.agent_name == "sintese"

    def test_optional_fields_mapped(self) -> None:
        now = datetime.now(timezone.utc)
        item = FeedItem(
            title="Test",
            url="https://example.com/test",
            source_name="src",
            published_at=now,
            summary="A summary",
            author="Author",
            tags=["ai", "ml"],
        )
        result = normalize_feed_item(item, "sintese")
        assert result.published_at == now
        assert result.summary == "A summary"
        assert result.author == "Author"
        assert result.tags == ["ai", "ml"]

    def test_content_hash_preserved(self) -> None:
        item = FeedItem(
            title="Test",
            url="https://example.com/test",
            source_name="src",
            content_hash="abc123",
        )
        result = normalize_feed_item(item, "sintese")
        assert result.content_hash == "abc123"

    def test_none_optional_fields(self) -> None:
        item = FeedItem(
            title="T",
            url="https://x.com",
            source_name="s",
        )
        result = normalize_feed_item(item, "sintese")
        assert result.published_at is None
        assert result.summary is None
        assert result.author is None


class TestNormalizeTrendSignal:
    """Test RADAR TrendSignal → EvidenceItem conversion."""

    def test_rss_signal_type_article(self) -> None:
        signal = TrendSignal(
            title="AI Breakthrough",
            url="https://example.com/ai",
            source_name="arxiv_cs",
            source_type="arxiv",
        )
        result = normalize_trend_signal(signal, "radar")
        assert result.evidence_type == EvidenceType.ARTICLE
        assert result.agent_name == "radar"

    def test_github_signal_type_repo(self) -> None:
        signal = TrendSignal(
            title="user/repo — A cool tool",
            url="https://github.com/user/repo",
            source_name="github_trending_daily",
            source_type="github",
            metrics={"stars": 500, "forks": 50},
        )
        result = normalize_trend_signal(signal, "radar")
        assert result.evidence_type == EvidenceType.REPO

    def test_metrics_in_raw_data(self) -> None:
        signal = TrendSignal(
            title="T",
            url="https://x.com",
            source_name="s",
            source_type="github",
            metrics={"stars": 100, "language": "Python"},
        )
        result = normalize_trend_signal(signal, "radar")
        assert result.raw_data["metrics"] == {"stars": 100, "language": "Python"}
        assert result.raw_data["source_type"] == "github"

    def test_content_hash_preserved(self) -> None:
        signal = TrendSignal(
            title="T",
            url="https://x.com",
            source_name="s",
            source_type="hn",
            content_hash="hash123",
        )
        result = normalize_trend_signal(signal, "radar")
        assert result.content_hash == "hash123"


class TestNormalizeDevSignal:
    """Test CODIGO DevSignal → EvidenceItem conversion."""

    def test_repo_type(self) -> None:
        signal = DevSignal(
            title="vercel/next.js",
            url="https://github.com/vercel/next.js",
            source_name="github_trending_weekly",
            signal_type="repo",
            language="TypeScript",
        )
        result = normalize_dev_signal(signal, "codigo")
        assert result.evidence_type == EvidenceType.REPO
        assert result.agent_name == "codigo"

    def test_package_type(self) -> None:
        signal = DevSignal(
            title="fastapi",
            url="https://pypi.org/project/fastapi/",
            source_name="pypi_recent",
            signal_type="package",
            language="python",
        )
        result = normalize_dev_signal(signal, "codigo")
        assert result.evidence_type == EvidenceType.PACKAGE

    def test_article_type(self) -> None:
        signal = DevSignal(
            title="Dev Blog Post",
            url="https://blog.example.com/post",
            source_name="dev_blog",
            signal_type="article",
        )
        result = normalize_dev_signal(signal, "codigo")
        assert result.evidence_type == EvidenceType.ARTICLE

    def test_raw_data_captures_language_and_metrics(self) -> None:
        signal = DevSignal(
            title="repo",
            url="https://github.com/x/y",
            source_name="gh",
            signal_type="repo",
            language="Rust",
            metrics={"stars": 1000},
        )
        result = normalize_dev_signal(signal, "codigo")
        assert result.raw_data["language"] == "Rust"
        assert result.raw_data["metrics"] == {"stars": 1000}
        assert result.raw_data["signal_type"] == "repo"


class TestNormalizeFundingEvent:
    """Test FUNDING FundingEvent → EvidenceItem conversion."""

    def test_required_fields(self) -> None:
        event = FundingEvent(
            company_name="Nubank",
            round_type="series_g",
            source_url="https://example.com/nubank",
            source_name="techcrunch_feed",
        )
        result = normalize_funding_event(event, "funding")
        assert result.title == "Nubank — series_g"
        assert result.url == "https://example.com/nubank"
        assert result.source_name == "techcrunch_feed"
        assert result.evidence_type == EvidenceType.FUNDING_EVENT
        assert result.agent_name == "funding"

    def test_amount_in_raw_data(self) -> None:
        event = FundingEvent(
            company_name="Stone",
            round_type="series_a",
            source_url="https://example.com/stone",
            source_name="src",
            amount_usd=50.0,
            currency="USD",
        )
        result = normalize_funding_event(event, "funding")
        assert result.raw_data["amount_usd"] == 50.0
        assert result.raw_data["currency"] == "USD"

    def test_announced_date_to_published_at(self) -> None:
        event = FundingEvent(
            company_name="Creditas",
            round_type="series_b",
            source_url="https://example.com",
            source_name="src",
            announced_date=date(2026, 2, 15),
        )
        result = normalize_funding_event(event, "funding")
        assert result.published_at is not None
        assert result.published_at.date() == date(2026, 2, 15)

    def test_investors_in_raw_data(self) -> None:
        event = FundingEvent(
            company_name="Test",
            round_type="seed",
            source_url="https://example.com",
            source_name="src",
            lead_investors=["Sequoia", "a16z"],
            participants=["YC"],
        )
        result = normalize_funding_event(event, "funding")
        assert result.raw_data["lead_investors"] == ["Sequoia", "a16z"]
        assert result.raw_data["participants"] == ["YC"]

    def test_content_hash_preserved(self) -> None:
        event = FundingEvent(
            company_name="X",
            round_type="seed",
            source_url="https://x.com",
            source_name="s",
        )
        result = normalize_funding_event(event, "funding")
        assert result.content_hash == event.content_hash


class TestNormalizeCompanyProfile:
    """Test MERCADO CompanyProfile → EvidenceItem conversion."""

    def test_required_fields(self) -> None:
        profile = CompanyProfile(
            name="Nubank",
            source_url="https://github.com/nubank",
            source_name="github_orgs",
        )
        result = normalize_company_profile(profile, "mercado")
        assert result.title == "Nubank"
        assert result.url == "https://github.com/nubank"
        assert result.source_name == "github_orgs"
        assert result.evidence_type == EvidenceType.COMPANY_PROFILE
        assert result.agent_name == "mercado"

    def test_description_as_summary(self) -> None:
        profile = CompanyProfile(
            name="Stone",
            description="Financial technology company",
            source_url="https://example.com",
            source_name="src",
        )
        result = normalize_company_profile(profile, "mercado")
        assert result.summary == "Financial technology company"

    def test_raw_data_captures_profile_fields(self) -> None:
        profile = CompanyProfile(
            name="Test",
            slug="test-co",
            website="https://test.co",
            sector="fintech",
            city="Sao Paulo",
            country="Brasil",
            tech_stack=["Python", "React"],
            tags=["fintech", "payments"],
            source_url="https://x.com",
            source_name="src",
        )
        result = normalize_company_profile(profile, "mercado")
        assert result.raw_data["slug"] == "test-co"
        assert result.raw_data["website"] == "https://test.co"
        assert result.raw_data["sector"] == "fintech"
        assert result.raw_data["city"] == "Sao Paulo"
        assert result.raw_data["country"] == "Brasil"
        assert result.raw_data["tech_stack"] == ["Python", "React"]
        assert result.tags == ["fintech", "payments"]


class TestNormalizeAny:
    """Test auto-dispatch normalizer."""

    def test_dispatches_feed_item(self) -> None:
        item = FeedItem(title="T", url="https://x.com", source_name="s")
        result = normalize_any(item, "sintese")
        assert result.evidence_type == EvidenceType.ARTICLE

    def test_dispatches_trend_signal(self) -> None:
        signal = TrendSignal(title="T", url="https://x.com", source_name="s", source_type="hn")
        result = normalize_any(signal, "radar")
        assert isinstance(result, EvidenceItem)

    def test_dispatches_dev_signal(self) -> None:
        signal = DevSignal(title="T", url="https://x.com", source_name="s", signal_type="repo")
        result = normalize_any(signal, "codigo")
        assert isinstance(result, EvidenceItem)

    def test_dispatches_funding_event(self) -> None:
        event = FundingEvent(
            company_name="X", round_type="seed",
            source_url="https://x.com", source_name="s",
        )
        result = normalize_any(event, "funding")
        assert result.evidence_type == EvidenceType.FUNDING_EVENT

    def test_dispatches_company_profile(self) -> None:
        profile = CompanyProfile(name="X", source_url="https://x.com", source_name="s")
        result = normalize_any(profile, "mercado")
        assert result.evidence_type == EvidenceType.COMPANY_PROFILE

    def test_raises_for_unknown_type(self) -> None:
        with pytest.raises(ValueError, match="Unknown item type"):
            normalize_any({"some": "dict"}, "unknown")
