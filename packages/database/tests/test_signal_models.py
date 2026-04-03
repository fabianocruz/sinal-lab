"""Tests for Social Signal Intelligence models.

Validates schema, defaults, constraints, and JSON field behaviour for:
- MonitoredAccount
- SocialSignal
- SignalCluster
- WeeklyPulse

Uses an in-memory SQLite database — no PostgreSQL required.
"""

import sys
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from packages.database.models.base import Base
from packages.database.models.monitored_account import MonitoredAccount
from packages.database.models.social_signal import SocialSignal
from packages.database.models.signal_cluster import SignalCluster
from packages.database.models.weekly_pulse import WeeklyPulse


@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine with all tables created once per module."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Transactional session — rolls back after each test."""
    session_factory = sessionmaker(bind=engine)
    s = session_factory()
    yield s
    s.rollback()
    s.close()


# ---------------------------------------------------------------------------
# Schema sanity
# ---------------------------------------------------------------------------

class TestTablesCreated:
    def test_signal_tables_exist(self, engine):
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "monitored_accounts" in table_names
        assert "social_signals" in table_names
        assert "signal_clusters" in table_names
        assert "weekly_pulses" in table_names


# ---------------------------------------------------------------------------
# MonitoredAccount
# ---------------------------------------------------------------------------

class TestMonitoredAccount:
    def test_create_minimal(self, session: Session):
        account = MonitoredAccount(
            id=uuid.uuid4(),
            platform="twitter",
            handle="pedrofranceschi",
        )
        session.add(account)
        session.flush()

        assert account.platform == "twitter"
        assert account.handle == "pedrofranceschi"
        assert account.authority_score == 0.5
        assert account.is_active is True
        assert account.display_name is None
        assert account.follower_count is None
        assert account.last_fetched_at is None

    def test_create_full(self, session: Session):
        now = datetime.now(timezone.utc)
        account = MonitoredAccount(
            id=uuid.uuid4(),
            platform="linkedin",
            handle="david-velez",
            display_name="David Velez",
            account_type="founder",
            sector_tags=["fintech", "banking"],
            authority_score=0.95,
            follower_count=250_000,
            bio="Founder & CEO at Nubank",
            profile_url="https://linkedin.com/in/david-velez",
            is_active=True,
            last_fetched_at=now,
            metadata_={"source": "manual", "verified": True},
        )
        session.add(account)
        session.flush()

        assert account.display_name == "David Velez"
        assert account.account_type == "founder"
        assert account.sector_tags == ["fintech", "banking"]
        assert account.authority_score == 0.95
        assert account.follower_count == 250_000
        assert account.metadata_["verified"] is True

    def test_platform_handle_unique_constraint(self, session: Session):
        a1 = MonitoredAccount(id=uuid.uuid4(), platform="twitter", handle="same_handle")
        a2 = MonitoredAccount(id=uuid.uuid4(), platform="twitter", handle="same_handle")
        session.add(a1)
        session.flush()
        session.add(a2)
        with pytest.raises(Exception):
            session.flush()

    def test_same_handle_different_platforms_allowed(self, session: Session):
        """The unique constraint is (platform, handle) — same handle on different
        platforms must be allowed."""
        a1 = MonitoredAccount(id=uuid.uuid4(), platform="twitter", handle="nubank")
        a2 = MonitoredAccount(id=uuid.uuid4(), platform="bluesky", handle="nubank")
        session.add(a1)
        session.flush()
        session.add(a2)
        session.flush()  # must not raise

        assert a1.platform != a2.platform

    def test_default_authority_score(self, session: Session):
        account = MonitoredAccount(id=uuid.uuid4(), platform="reddit", handle="u/techbr")
        session.add(account)
        session.flush()
        assert account.authority_score == 0.5

    def test_sector_tags_json_round_trip(self, session: Session):
        tags = ["ai", "saas", "devtools"]
        account = MonitoredAccount(
            id=uuid.uuid4(),
            platform="bluesky",
            handle="founder.bsky.social",
            sector_tags=tags,
        )
        session.add(account)
        session.flush()
        session.expire(account)
        session.refresh(account)
        assert account.sector_tags == tags

    def test_repr(self, session: Session):
        account = MonitoredAccount(
            id=uuid.uuid4(), platform="twitter", handle="test_repr", account_type="vc"
        )
        r = repr(account)
        assert "twitter" in r
        assert "test_repr" in r
        assert "vc" in r


# ---------------------------------------------------------------------------
# SocialSignal
# ---------------------------------------------------------------------------

class TestSocialSignal:
    def _make_signal(self, **kwargs) -> SocialSignal:
        defaults = dict(
            id=uuid.uuid4(),
            platform="twitter",
            post_url="https://x.com/user/status/123",
            content_hash="abc123def456abc123def456abc12345",
        )
        defaults.update(kwargs)
        return SocialSignal(**defaults)

    def test_create_minimal(self, session: Session):
        signal = self._make_signal()
        session.add(signal)
        session.flush()

        assert signal.platform == "twitter"
        assert signal.content_hash == "abc123def456abc123def456abc12345"
        assert signal.theme is None
        assert signal.sentiment is None
        assert signal.cluster_id is None

    def test_create_full(self, session: Session):
        now = datetime.now(timezone.utc)
        signal = SocialSignal(
            id=uuid.uuid4(),
            platform="twitter",
            post_url="https://x.com/pedrofranceschi/status/456",
            author_handle="pedrofranceschi",
            author_display_name="Pedro Franceschi",
            text="Open banking is reshaping how Brazilians interact with money.",
            content_hash="fullhash00000000000000000000000a",
            published_at=now,
            collected_at=now,
            metrics={"likes": 420, "replies": 38, "reposts": 110, "quotes": 22, "views": 15000},
            theme="open-banking",
            sub_theme="regulation",
            entities=[{"name": "Banco Central", "type": "organization"}],
            sentiment=0.7,
            authority_score=0.88,
            signal_dimensions={"volume": 0.6, "velocity": 0.8, "authority_concentration": 0.9},
            cluster_id=str(uuid.uuid4()),
            agent_run_id="social-2026-04-03-001",
        )
        session.add(signal)
        session.flush()

        assert signal.author_handle == "pedrofranceschi"
        assert signal.metrics["likes"] == 420
        assert signal.entities[0]["name"] == "Banco Central"
        assert signal.sentiment == 0.7
        assert signal.signal_dimensions["velocity"] == 0.8

    def test_content_hash_unique(self, session: Session):
        s1 = self._make_signal(content_hash="uniquehash0000000000000000000001")
        s2 = self._make_signal(
            post_url="https://x.com/other/status/999",
            content_hash="uniquehash0000000000000000000001",
        )
        session.add(s1)
        session.flush()
        session.add(s2)
        with pytest.raises(Exception):
            session.flush()

    def test_different_content_hashes_allowed(self, session: Session):
        s1 = self._make_signal(
            post_url="https://x.com/a/status/1",
            content_hash="hashA0000000000000000000000000a1",
        )
        s2 = self._make_signal(
            post_url="https://x.com/b/status/2",
            content_hash="hashB0000000000000000000000000b2",
        )
        session.add(s1)
        session.add(s2)
        session.flush()  # must not raise
        assert s1.id != s2.id

    def test_metrics_json_round_trip(self, session: Session):
        metrics = {"likes": 100, "reposts": 20, "views": 5000}
        signal = self._make_signal(
            content_hash="metricsroundtrip000000000000000a",
            metrics=metrics,
        )
        session.add(signal)
        session.flush()
        session.expire(signal)
        session.refresh(signal)
        assert signal.metrics["views"] == 5000

    def test_entities_json_round_trip(self, session: Session):
        entities = [
            {"name": "Nubank", "type": "company"},
            {"name": "David Velez", "type": "person"},
        ]
        signal = self._make_signal(
            content_hash="entitiesroundtrip0000000000000b",
            entities=entities,
        )
        session.add(signal)
        session.flush()
        session.expire(signal)
        session.refresh(signal)
        assert len(signal.entities) == 2
        assert signal.entities[1]["type"] == "person"

    def test_repr(self, session: Session):
        signal = self._make_signal(
            content_hash="reprtest000000000000000000000000",
            author_handle="handle_repr",
            text="Some text content here for repr",
        )
        r = repr(signal)
        assert "twitter" in r
        assert "handle_repr" in r


# ---------------------------------------------------------------------------
# SignalCluster
# ---------------------------------------------------------------------------

class TestSignalCluster:
    def test_create_minimal(self, session: Session):
        cluster = SignalCluster(
            id=uuid.uuid4(),
            name="Open Banking Regulation",
            slug="open-banking-regulation-2026-w14",
        )
        session.add(cluster)
        session.flush()

        assert cluster.name == "Open Banking Regulation"
        assert cluster.signal_count == 0
        assert cluster.narrative_stage is None
        assert cluster.composite_score is None

    def test_create_full(self, session: Session):
        now = datetime.now(timezone.utc)
        cluster = SignalCluster(
            id=uuid.uuid4(),
            name="AI in Brazilian Fintechs",
            slug="ai-brazilian-fintechs-2026-w14",
            theme="ai",
            sub_theme="fintech-adoption",
            description="Growing discussion around AI tooling adoption in LATAM fintechs.",
            signal_count=42,
            composite_score=0.78,
            dimensions={
                "volume": 0.7,
                "velocity": 0.8,
                "authority_concentration": 0.6,
                "sentiment_polarity": 0.5,
                "cross_platform_spread": 0.4,
                "novelty": 0.9,
                "entity_density": 0.6,
                "temporal_consistency": 0.7,
            },
            narrative_stage="accelerating",
            first_seen_at=now,
            last_active_at=now,
            top_voices=[{"handle": "pedrofranceschi", "name": "Pedro F", "authority": 0.9}],
            top_posts=[{"url": "https://x.com/x/1", "text": "AI is...", "metrics": {}}],
            related_companies=[{"slug": "nubank", "name": "Nubank"}],
            week_number=14,
            year=2026,
            agent_run_id="social-2026-04-03-001",
        )
        session.add(cluster)
        session.flush()

        assert cluster.composite_score == 0.78
        assert cluster.narrative_stage == "accelerating"
        assert cluster.signal_count == 42
        assert cluster.dimensions["novelty"] == 0.9
        assert cluster.top_voices[0]["handle"] == "pedrofranceschi"

    def test_slug_unique(self, session: Session):
        c1 = SignalCluster(id=uuid.uuid4(), name="A", slug="same-cluster-slug")
        c2 = SignalCluster(id=uuid.uuid4(), name="B", slug="same-cluster-slug")
        session.add(c1)
        session.flush()
        session.add(c2)
        with pytest.raises(Exception):
            session.flush()

    def test_related_companies_json_round_trip(self, session: Session):
        companies = [{"slug": "nubank", "name": "Nubank"}, {"slug": "stone", "name": "Stone"}]
        cluster = SignalCluster(
            id=uuid.uuid4(),
            name="Fintech Giants",
            slug="fintech-giants-2026-w14",
            related_companies=companies,
        )
        session.add(cluster)
        session.flush()
        session.expire(cluster)
        session.refresh(cluster)
        assert len(cluster.related_companies) == 2
        assert cluster.related_companies[0]["slug"] == "nubank"

    def test_dimensions_json_round_trip(self, session: Session):
        dims = {"volume": 0.5, "velocity": 0.6}
        cluster = SignalCluster(
            id=uuid.uuid4(),
            name="Dims Test",
            slug="dims-test-2026-w14",
            dimensions=dims,
        )
        session.add(cluster)
        session.flush()
        session.expire(cluster)
        session.refresh(cluster)
        assert cluster.dimensions["velocity"] == 0.6

    def test_default_signal_count(self, session: Session):
        cluster = SignalCluster(
            id=uuid.uuid4(), name="Zero Count", slug="zero-count-2026-w14"
        )
        session.add(cluster)
        session.flush()
        assert cluster.signal_count == 0

    def test_repr(self, session: Session):
        cluster = SignalCluster(
            id=uuid.uuid4(),
            name="Repr Cluster",
            slug="repr-cluster",
            theme="ai",
            narrative_stage="emerging",
        )
        r = repr(cluster)
        assert "Repr Cluster" in r
        assert "ai" in r
        assert "emerging" in r


# ---------------------------------------------------------------------------
# WeeklyPulse
# ---------------------------------------------------------------------------

class TestWeeklyPulse:
    def test_create_minimal(self, session: Session):
        pulse = WeeklyPulse(
            id=uuid.uuid4(),
            week_number=14,
            year=2026,
            slug="pulse-2026-w14",
        )
        session.add(pulse)
        session.flush()

        assert pulse.week_number == 14
        assert pulse.year == 2026
        assert pulse.status == "draft"
        assert pulse.accelerating_themes is None
        assert pulse.generated_at is None

    def test_create_full(self, session: Session):
        now = datetime.now(timezone.utc)
        pulse = WeeklyPulse(
            id=uuid.uuid4(),
            week_number=15,
            year=2026,
            slug="pulse-2026-w15",
            accelerating_themes=[{"name": "open-banking", "score": 0.82, "delta": 0.15}],
            emerging_signals=[{"name": "AI credit scoring", "score": 0.61, "platforms": ["twitter"]}],
            top_posts=[{"url": "https://x.com/x/1", "text": "...", "author": "user", "metrics": {}}],
            top_voices=[{"handle": "pedrofranceschi", "name": "Pedro F", "signal_count": 8}],
            startups_to_watch=[{"slug": "openco", "name": "OpenCo", "reason": "Series B raised"}],
            sector_implications=[{"sector": "fintech", "implication": "Open banking drives..."} ],
            generated_at=now,
            agent_run_id="social-2026-04-10-001",
            status="published",
        )
        session.add(pulse)
        session.flush()

        assert pulse.status == "published"
        assert pulse.accelerating_themes[0]["score"] == 0.82
        assert pulse.top_voices[0]["signal_count"] == 8
        assert pulse.startups_to_watch[0]["slug"] == "openco"

    def test_slug_unique(self, session: Session):
        p1 = WeeklyPulse(id=uuid.uuid4(), week_number=20, year=2026, slug="pulse-2026-w20")
        p2 = WeeklyPulse(id=uuid.uuid4(), week_number=20, year=2026, slug="pulse-2026-w20")
        session.add(p1)
        session.flush()
        session.add(p2)
        with pytest.raises(Exception):
            session.flush()

    def test_default_status_is_draft(self, session: Session):
        pulse = WeeklyPulse(
            id=uuid.uuid4(), week_number=21, year=2026, slug="pulse-2026-w21"
        )
        session.add(pulse)
        session.flush()
        assert pulse.status == "draft"

    def test_accelerating_themes_json_round_trip(self, session: Session):
        themes = [
            {"name": "ai", "score": 0.9, "delta": 0.2},
            {"name": "open-banking", "score": 0.75, "delta": 0.05},
        ]
        pulse = WeeklyPulse(
            id=uuid.uuid4(),
            week_number=22,
            year=2026,
            slug="pulse-2026-w22",
            accelerating_themes=themes,
        )
        session.add(pulse)
        session.flush()
        session.expire(pulse)
        session.refresh(pulse)
        assert len(pulse.accelerating_themes) == 2
        assert pulse.accelerating_themes[0]["name"] == "ai"

    def test_sector_implications_json_round_trip(self, session: Session):
        implications = [
            {"sector": "fintech", "implication": "Regulation tightening"},
            {"sector": "ai", "implication": "Rapid adoption in SMBs"},
        ]
        pulse = WeeklyPulse(
            id=uuid.uuid4(),
            week_number=23,
            year=2026,
            slug="pulse-2026-w23",
            sector_implications=implications,
        )
        session.add(pulse)
        session.flush()
        session.expire(pulse)
        session.refresh(pulse)
        assert pulse.sector_implications[1]["sector"] == "ai"

    def test_repr(self, session: Session):
        pulse = WeeklyPulse(
            id=uuid.uuid4(), week_number=30, year=2026, slug="pulse-2026-w30", status="published"
        )
        r = repr(pulse)
        assert "pulse-2026-w30" in r
        assert "published" in r
        assert "2026" in r
