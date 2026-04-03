"""Tests for signals router — Social Signal Intelligence dashboard.

Uses SQLite in-memory with StaticPool so all threads share the same
database connection. This is required because FastAPI runs sync endpoints
in a worker thread pool — without StaticPool, each thread would get a
separate in-memory database and see "no such table" errors.

Run: pytest apps/api/tests/test_signals.py -v
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_db
from apps.api.main import app
from packages.database.models.base import Base
from packages.database.models.monitored_account import MonitoredAccount
from packages.database.models.signal_cluster import SignalCluster
from packages.database.models.social_signal import SocialSignal
from packages.database.models.weekly_pulse import WeeklyPulse

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create test client with test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_signals(db_session):
    """Create sample social signals for testing."""
    signals = [
        SocialSignal(
            id=uuid.uuid4(),
            platform="twitter",
            post_url="https://twitter.com/founder1/status/1",
            author_handle="founder1",
            author_display_name="Founder One",
            text="AI is transforming fintech in LATAM",
            content_hash="hash001",
            published_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc),
            metrics={"likes": 120, "replies": 15, "reposts": 30},
            theme="AI",
            sub_theme="Fintech AI",
            sentiment=0.8,
            authority_score=0.9,
            created_at=datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc),
        ),
        SocialSignal(
            id=uuid.uuid4(),
            platform="twitter",
            post_url="https://twitter.com/vc1/status/2",
            author_handle="vc1",
            author_display_name="VC Partner",
            text="Series A rounds are heating up in Brazil",
            content_hash="hash002",
            published_at=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc),
            metrics={"likes": 80, "replies": 10},
            theme="Funding",
            sub_theme="Series A",
            sentiment=0.6,
            authority_score=0.85,
            created_at=datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc),
        ),
        SocialSignal(
            id=uuid.uuid4(),
            platform="reddit",
            post_url="https://reddit.com/r/startups/post/3",
            author_handle="redditor99",
            text="What are the best developer tools in Latin America?",
            content_hash="hash003",
            published_at=datetime(2026, 3, 18, 10, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc),
            theme="DevTools",
            sentiment=0.5,
            created_at=datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for s in signals:
        db_session.add(s)
    db_session.commit()
    return signals


@pytest.fixture
def sample_clusters(db_session):
    """Create sample signal clusters for testing."""
    clusters = [
        SignalCluster(
            id=uuid.uuid4(),
            name="AI in Fintech",
            slug="ai-in-fintech",
            theme="AI",
            sub_theme="Fintech AI",
            description="Growing conversation about AI applications in fintech",
            signal_count=15,
            composite_score=0.92,
            narrative_stage="accelerating",
            week_number=12,
            year=2026,
            created_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        ),
        SignalCluster(
            id=uuid.uuid4(),
            name="Funding Surge",
            slug="funding-surge",
            theme="Funding",
            description="Series A activity in Brazil accelerating",
            signal_count=8,
            composite_score=0.75,
            narrative_stage="emerging",
            week_number=12,
            year=2026,
            created_at=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
        ),
        SignalCluster(
            id=uuid.uuid4(),
            name="DevTools LATAM",
            slug="devtools-latam",
            theme="DevTools",
            description="Developer tooling ecosystem in LATAM",
            signal_count=5,
            composite_score=0.60,
            narrative_stage="emerging",
            week_number=11,
            year=2026,
            created_at=datetime(2026, 3, 18, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 18, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for c in clusters:
        db_session.add(c)
    db_session.commit()
    return clusters


@pytest.fixture
def sample_pulses(db_session):
    """Create sample weekly pulses for testing."""
    pulses = [
        WeeklyPulse(
            id=uuid.uuid4(),
            week_number=12,
            year=2026,
            slug="pulse-2026-w12",
            accelerating_themes=[{"name": "AI", "score": 0.92, "delta": 0.15}],
            emerging_signals=[{"name": "DevTools", "score": 0.60, "platforms": ["twitter"]}],
            top_posts=[{"url": "https://twitter.com/founder1/status/1", "text": "AI in LATAM"}],
            status="published",
            generated_at=datetime(2026, 3, 22, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 3, 22, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 22, 10, 0, 0, tzinfo=timezone.utc),
        ),
        WeeklyPulse(
            id=uuid.uuid4(),
            week_number=11,
            year=2026,
            slug="pulse-2026-w11",
            accelerating_themes=[{"name": "Funding", "score": 0.75, "delta": 0.10}],
            status="published",
            generated_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for p in pulses:
        db_session.add(p)
    db_session.commit()
    return pulses


@pytest.fixture
def sample_voices(db_session):
    """Create sample monitored accounts for testing."""
    accounts = [
        MonitoredAccount(
            id=uuid.uuid4(),
            platform="twitter",
            handle="founder1",
            display_name="Founder One",
            account_type="founder",
            sector_tags=["fintech", "ai"],
            authority_score=0.95,
            follower_count=50000,
            bio="Building the future of fintech in LATAM",
            is_active=True,
            created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        ),
        MonitoredAccount(
            id=uuid.uuid4(),
            platform="twitter",
            handle="vc1",
            display_name="VC Partner",
            account_type="vc",
            sector_tags=["fintech"],
            authority_score=0.85,
            follower_count=30000,
            is_active=True,
            created_at=datetime(2026, 3, 2, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 2, 10, 0, 0, tzinfo=timezone.utc),
        ),
        MonitoredAccount(
            id=uuid.uuid4(),
            platform="linkedin",
            handle="exec1",
            display_name="Tech Exec",
            account_type="exec",
            authority_score=0.70,
            follower_count=15000,
            is_active=False,
            created_at=datetime(2026, 3, 3, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 3, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for a in accounts:
        db_session.add(a)
    db_session.commit()
    return accounts


# ---------------------------------------------------------------------------
# Signals — paginated envelope
# ---------------------------------------------------------------------------


def test_list_signals_returns_paginated_envelope(client, sample_signals):
    """Test that listing signals returns paginated envelope."""
    response = client.get("/api/signals")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_signals_ordered_by_published_at_desc(client, sample_signals):
    """Test signals are ordered by published_at descending."""
    response = client.get("/api/signals")
    data = response.json()
    items = data["items"]

    # Most recent first
    assert items[0]["author_handle"] == "founder1"
    assert items[1]["author_handle"] == "vc1"
    assert items[2]["author_handle"] == "redditor99"


def test_list_signals_filter_by_platform(client, sample_signals):
    """Test filtering signals by platform."""
    response = client.get("/api/signals?platform=twitter")
    data = response.json()
    assert data["total"] == 2
    assert all(s["platform"] == "twitter" for s in data["items"])


def test_list_signals_filter_by_theme(client, sample_signals):
    """Test filtering signals by theme."""
    response = client.get("/api/signals?theme=AI")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["theme"] == "AI"


def test_list_signals_filter_by_sub_theme(client, sample_signals):
    """Test filtering signals by sub_theme."""
    response = client.get("/api/signals?sub_theme=Series A")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["sub_theme"] == "Series A"


def test_list_signals_search_text(client, sample_signals):
    """Test searching signals by text content."""
    response = client.get("/api/signals?search=fintech")
    data = response.json()
    assert data["total"] == 1
    assert "fintech" in data["items"][0]["text"].lower()


def test_list_signals_search_no_results(client, sample_signals):
    """Test search with no matching results."""
    response = client.get("/api/signals?search=NonExistentTopic")
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_list_signals_pagination(client, sample_signals):
    """Test signal pagination."""
    response = client.get("/api/signals?limit=2&offset=0")
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Second page
    response2 = client.get("/api/signals?limit=2&offset=2")
    data2 = response2.json()
    assert len(data2["items"]) == 1


def test_list_signals_limit_validation(client, sample_signals):
    """Test limit validation rejects out-of-range values."""
    response = client.get("/api/signals?limit=200")
    assert response.status_code == 422

    response = client.get("/api/signals?limit=0")
    assert response.status_code == 422


def test_list_signals_date_range_filter(client, sample_signals):
    """Test filtering signals by date range."""
    response = client.get(
        "/api/signals?date_from=2026-03-19T00:00:00Z&date_to=2026-03-19T23:59:59Z"
    )
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["author_handle"] == "vc1"


# ---------------------------------------------------------------------------
# Clusters — paginated envelope
# ---------------------------------------------------------------------------


def test_list_clusters_returns_paginated_envelope(client, sample_clusters):
    """Test that listing clusters returns paginated envelope."""
    response = client.get("/api/signals/clusters")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_clusters_ordered_by_composite_score_desc(client, sample_clusters):
    """Test clusters are ordered by composite_score descending."""
    response = client.get("/api/signals/clusters")
    data = response.json()
    items = data["items"]

    assert items[0]["slug"] == "ai-in-fintech"
    assert items[1]["slug"] == "funding-surge"
    assert items[2]["slug"] == "devtools-latam"


def test_list_clusters_filter_by_theme(client, sample_clusters):
    """Test filtering clusters by theme."""
    response = client.get("/api/signals/clusters?theme=AI")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["theme"] == "AI"


def test_list_clusters_filter_by_narrative_stage(client, sample_clusters):
    """Test filtering clusters by narrative stage."""
    response = client.get("/api/signals/clusters?narrative_stage=emerging")
    data = response.json()
    assert data["total"] == 2
    assert all(c["narrative_stage"] == "emerging" for c in data["items"])


def test_list_clusters_filter_by_week_and_year(client, sample_clusters):
    """Test filtering clusters by week number and year."""
    response = client.get("/api/signals/clusters?week_number=12&year=2026")
    data = response.json()
    assert data["total"] == 2


def test_get_cluster_by_slug_success(client, sample_clusters):
    """Test getting a cluster by slug returns full detail."""
    response = client.get("/api/signals/clusters/ai-in-fintech")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "ai-in-fintech"
    assert data["name"] == "AI in Fintech"
    assert data["composite_score"] == 0.92
    assert data["narrative_stage"] == "accelerating"


def test_get_cluster_by_slug_not_found(client, sample_clusters):
    """Test getting non-existent cluster returns 404."""
    response = client.get("/api/signals/clusters/non-existent-cluster")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Pulse — latest and by slug
# ---------------------------------------------------------------------------


def test_get_latest_pulse(client, sample_pulses):
    """Test getting the latest weekly pulse."""
    response = client.get("/api/signals/pulse")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "pulse-2026-w12"
    assert data["week_number"] == 12
    assert data["year"] == 2026


def test_get_pulse_by_week_and_year(client, sample_pulses):
    """Test getting a specific pulse by week and year parameters."""
    response = client.get("/api/signals/pulse?week=11&year=2026")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "pulse-2026-w11"
    assert data["week_number"] == 11


def test_get_pulse_not_found(client, sample_pulses):
    """Test getting a pulse that does not exist."""
    response = client.get("/api/signals/pulse?week=99&year=2020")

    assert response.status_code == 404


def test_get_pulse_by_slug_success(client, sample_pulses):
    """Test getting a pulse by slug."""
    response = client.get("/api/signals/pulse/pulse-2026-w12")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "pulse-2026-w12"
    assert data["status"] == "published"
    assert len(data["accelerating_themes"]) == 1


def test_get_pulse_by_slug_not_found(client, sample_pulses):
    """Test getting a non-existent pulse by slug returns 404."""
    response = client.get("/api/signals/pulse/non-existent-pulse")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Voices — paginated envelope
# ---------------------------------------------------------------------------


def test_list_voices_returns_paginated_envelope(client, sample_voices):
    """Test that listing voices returns paginated envelope."""
    response = client.get("/api/signals/voices")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_voices_ordered_by_authority_score_desc(client, sample_voices):
    """Test voices are ordered by authority_score descending."""
    response = client.get("/api/signals/voices")
    data = response.json()
    items = data["items"]

    assert items[0]["handle"] == "founder1"
    assert items[1]["handle"] == "vc1"
    assert items[2]["handle"] == "exec1"


def test_list_voices_filter_by_platform(client, sample_voices):
    """Test filtering voices by platform."""
    response = client.get("/api/signals/voices?platform=twitter")
    data = response.json()
    assert data["total"] == 2
    assert all(v["platform"] == "twitter" for v in data["items"])


def test_list_voices_filter_by_account_type(client, sample_voices):
    """Test filtering voices by account type."""
    response = client.get("/api/signals/voices?account_type=founder")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["handle"] == "founder1"


def test_list_voices_filter_by_is_active(client, sample_voices):
    """Test filtering voices by active status."""
    response = client.get("/api/signals/voices?is_active=true")
    data = response.json()
    assert data["total"] == 2
    assert all(v["is_active"] is True for v in data["items"])

    response2 = client.get("/api/signals/voices?is_active=false")
    data2 = response2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["handle"] == "exec1"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_stats_returns_correct_counts(client, sample_signals, sample_clusters, sample_voices):
    """Test stats endpoint returns correct aggregate counts."""
    response = client.get("/api/signals/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_signals"] == 3
    assert data["total_clusters"] == 3
    assert data["total_voices"] == 2  # only active voices
    assert data["platforms"]["twitter"] == 2
    assert data["platforms"]["reddit"] == 1
    assert data["themes"]["AI"] == 1
    assert data["themes"]["Funding"] == 1
    assert data["themes"]["DevTools"] == 1


def test_stats_empty_database(client, db_session):
    """Test stats returns zeros when database is empty."""
    response = client.get("/api/signals/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_signals"] == 0
    assert data["total_clusters"] == 0
    assert data["total_voices"] == 0
    assert data["platforms"] == {}
    assert data["themes"] == {}


# ---------------------------------------------------------------------------
# Empty results
# ---------------------------------------------------------------------------


def test_list_signals_empty(client, db_session):
    """Test listing signals when none exist."""
    response = client.get("/api/signals")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_latest_pulse_empty_database(client, db_session):
    """Test getting latest pulse when none exist returns 404."""
    response = client.get("/api/signals/pulse")

    assert response.status_code == 404
