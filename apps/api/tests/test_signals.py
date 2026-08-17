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
from packages.database.models.watchlist_item import WatchlistItem
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


# ---------------------------------------------------------------------------
# Voices — recent_signals enrichment
# ---------------------------------------------------------------------------


def test_voices_include_recent_signals_by_handle(client, sample_voices, sample_signals):
    """Test voices return recent_signals when author_handle matches."""
    response = client.get("/api/signals/voices")
    data = response.json()

    # founder1 voice matches founder1 signal by handle
    founder_voice = next(v for v in data["items"] if v["handle"] == "founder1")
    assert len(founder_voice["recent_signals"]) > 0
    assert founder_voice["recent_signals"][0]["platform"] == "twitter"


def test_voices_never_attribute_signals_by_sector_tags(client, db_session, sample_signals):
    """A shared topic is not authorship: never attach a post we cannot attribute.

    This used to assert the opposite. The sector_tags -> theme fallback put
    arbitrary posts under the name and bio of identifiable people, which is
    the one failure mode here with external reputational cost.
    """
    account = MonitoredAccount(
        id=uuid.uuid4(),
        platform="crunchbase",
        handle="sam-altman",  # Does NOT match any signal author_handle
        display_name="Sam Altman",  # Does NOT match any author_display_name
        account_type="founder",
        sector_tags=["ai"],  # Signals with theme="AI" exist, and must NOT match
        authority_score=0.95,
        is_active=True,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(account)
    db_session.commit()

    response = client.get("/api/signals/voices?platform=crunchbase")
    data = response.json()

    assert data["total"] == 1
    voice = data["items"][0]
    assert voice["handle"] == "sam-altman"
    assert voice["recent_signals"] == []


def test_voices_recent_signals_empty_when_no_match(client, db_session):
    """Test voices with no matching signals return empty recent_signals."""
    account = MonitoredAccount(
        id=uuid.uuid4(),
        platform="twitter",
        handle="no-signals-user",
        display_name="Nobody",
        account_type="founder",
        sector_tags=["quantum_computing"],  # No signals match this
        authority_score=0.5,
        is_active=True,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(account)
    db_session.commit()

    response = client.get("/api/signals/voices?platform=twitter")
    data = response.json()

    nobody_voice = next(v for v in data["items"] if v["handle"] == "no-signals-user")
    assert nobody_voice["recent_signals"] == []


def test_voices_recent_signals_limited_to_three(client, db_session):
    """Test that at most 3 recent signals are returned per voice."""
    # Create 5 signals with the same author
    for i in range(5):
        sig = SocialSignal(
            id=uuid.uuid4(),
            platform="twitter",
            post_url=f"https://twitter.com/prolific/status/{i}",
            author_handle="prolific-author",
            text=f"Signal number {i}",
            content_hash=f"hash_prolific_{i}",
            published_at=datetime(2026, 3, 20, i, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 3, 20, i, 0, 0, tzinfo=timezone.utc),
            theme="AI",
            created_at=datetime(2026, 3, 20, i, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 20, i, 0, 0, tzinfo=timezone.utc),
        )
        db_session.add(sig)

    account = MonitoredAccount(
        id=uuid.uuid4(),
        platform="twitter",
        handle="prolific-author",
        display_name="Prolific",
        authority_score=0.9,
        is_active=True,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(account)
    db_session.commit()

    response = client.get("/api/signals/voices?platform=twitter")
    data = response.json()

    prolific = next(v for v in data["items"] if v["handle"] == "prolific-author")
    assert len(prolific["recent_signals"]) == 3


# ---------------------------------------------------------------------------
# Watchlist — CRUD endpoints
# ---------------------------------------------------------------------------


def test_add_to_watchlist(client, db_session):
    """Test adding an item to the watchlist returns 201."""
    response = client.post(
        "/api/signals/watchlist",
        json={
            "email": "user@example.com",
            "item_type": "cluster",
            "item_slug": "ai-in-fintech",
            "item_name": "AI in Fintech",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_email"] == "user@example.com"
    assert data["item_type"] == "cluster"
    assert data["item_slug"] == "ai-in-fintech"
    assert data["item_name"] == "AI in Fintech"
    assert "id" in data


def test_list_watchlist_empty(client, db_session):
    """Test listing watchlist for a user with no items."""
    response = client.get("/api/signals/watchlist?email=nobody@example.com")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_watchlist_with_items(client, db_session):
    """Test listing watchlist returns all items for a user."""
    # Add two items
    client.post(
        "/api/signals/watchlist",
        json={
            "email": "user@example.com",
            "item_type": "cluster",
            "item_slug": "ai-in-fintech",
            "item_name": "AI in Fintech",
        },
    )
    client.post(
        "/api/signals/watchlist",
        json={
            "email": "user@example.com",
            "item_type": "voice",
            "item_slug": "founder1",
            "item_name": "Founder One",
        },
    )

    response = client.get("/api/signals/watchlist?email=user@example.com")
    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    slugs = {item["item_slug"] for item in data["items"]}
    assert slugs == {"ai-in-fintech", "founder1"}


def test_list_watchlist_filter_by_item_type(client, db_session):
    """Test listing watchlist filtered by item_type."""
    client.post(
        "/api/signals/watchlist",
        json={
            "email": "user@example.com",
            "item_type": "cluster",
            "item_slug": "ai-in-fintech",
            "item_name": "AI in Fintech",
        },
    )
    client.post(
        "/api/signals/watchlist",
        json={
            "email": "user@example.com",
            "item_type": "voice",
            "item_slug": "founder1",
            "item_name": "Founder One",
        },
    )

    response = client.get("/api/signals/watchlist?email=user@example.com&item_type=cluster")
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["item_type"] == "cluster"


def test_list_watchlist_filters_by_email(client, db_session):
    """Test that watchlist items are scoped to the requesting user."""
    client.post(
        "/api/signals/watchlist",
        json={
            "email": "alice@example.com",
            "item_type": "cluster",
            "item_slug": "ai-in-fintech",
            "item_name": "AI in Fintech",
        },
    )
    client.post(
        "/api/signals/watchlist",
        json={
            "email": "bob@example.com",
            "item_type": "cluster",
            "item_slug": "funding-surge",
            "item_name": "Funding Surge",
        },
    )

    alice_resp = client.get("/api/signals/watchlist?email=alice@example.com")
    bob_resp = client.get("/api/signals/watchlist?email=bob@example.com")

    assert alice_resp.json()["total"] == 1
    assert alice_resp.json()["items"][0]["item_slug"] == "ai-in-fintech"
    assert bob_resp.json()["total"] == 1
    assert bob_resp.json()["items"][0]["item_slug"] == "funding-surge"


def test_add_duplicate_watchlist_item_returns_409(client, db_session):
    """Test that adding the same item twice returns 409 Conflict."""
    payload = {
        "email": "user@example.com",
        "item_type": "cluster",
        "item_slug": "ai-in-fintech",
        "item_name": "AI in Fintech",
    }
    response1 = client.post("/api/signals/watchlist", json=payload)
    assert response1.status_code == 201

    response2 = client.post("/api/signals/watchlist", json=payload)
    assert response2.status_code == 409
    assert "already" in response2.json()["detail"].lower()


def test_remove_from_watchlist(client, db_session):
    """Test removing an item from the watchlist."""
    # Add item
    add_resp = client.post(
        "/api/signals/watchlist",
        json={
            "email": "user@example.com",
            "item_type": "cluster",
            "item_slug": "ai-in-fintech",
            "item_name": "AI in Fintech",
        },
    )
    item_id = add_resp.json()["id"]

    # Remove it
    del_resp = client.delete(f"/api/signals/watchlist/{item_id}")
    assert del_resp.status_code == 204

    # Verify it's gone
    list_resp = client.get("/api/signals/watchlist?email=user@example.com")
    assert list_resp.json()["total"] == 0


def test_remove_nonexistent_watchlist_item_returns_404(client, db_session):
    """Test removing a non-existent watchlist item returns 404."""
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/signals/watchlist/{fake_id}")
    assert response.status_code == 404


def test_watchlist_email_required(client, db_session):
    """Test that the email query param is required for listing."""
    response = client.get("/api/signals/watchlist")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Honesty guards — undated signals, duplicate clusters, scraped noise
# ---------------------------------------------------------------------------


def test_undated_signals_do_not_hijack_page_one(client, db_session):
    """Signals with no published_at must not outrank dated ones.

    Postgres sorts NULLS FIRST on DESC, so ordering by published_at alone put
    exactly the rows the collector failed to date — usually scrape errors — at
    the top of page 1. They now fall back to collected_at.
    """
    undated = SocialSignal(
        id=uuid.uuid4(),
        platform="twitter",
        post_url="https://x.com/undated",
        author_handle="broken_scrape",
        text="Scraped without a date",
        content_hash="hash_undated",
        published_at=None,
        collected_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    dated = SocialSignal(
        id=uuid.uuid4(),
        platform="twitter",
        post_url="https://x.com/dated",
        author_handle="working_scrape",
        text="Scraped with a date",
        content_hash="hash_dated",
        published_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 3, 20, 11, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 3, 20, 11, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 20, 11, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([undated, dated])
    db_session.commit()

    data = client.get("/api/signals").json()

    assert data["items"][0]["author_handle"] == "working_scrape"


def test_clusters_exclude_empty_theme_residual_bucket(client, db_session):
    """Clusters with no theme are the unclassified bucket, not a trend."""
    residual = SignalCluster(
        id=uuid.uuid4(),
        name="Outros Sinais",
        slug="outros-sinais",
        theme=None,
        description="Residual bucket",
        signal_count=999,
        composite_score=0.99,
        narrative_stage="emerging",
        week_number=12,
        year=2026,
        created_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(residual)
    db_session.commit()

    data = client.get("/api/signals/clusters").json()

    assert data["total"] == 0
    assert data["items"] == []


def test_clusters_dedupe_same_bucket_across_runs(client, db_session):
    """The same bucket re-inserted under a fresh slug appears once.

    The upsert key is a slug of the LLM-generated name, so a re-labelled
    cluster INSERTs instead of UPDATEs and the grid showed it twice.
    """
    common = dict(
        name="Desenvolvimento e experimentacao com modelos de IA",
        theme="AI",
        composite_score=0.5,
        narrative_stage="emerging",
        year=2026,
    )
    older = SignalCluster(
        id=uuid.uuid4(),
        slug="desenvolvimento-e-experimentacao-com-modelos-de-ia",
        signal_count=40,
        week_number=17,
        created_at=datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc),
        **common,
    )
    newer = SignalCluster(
        id=uuid.uuid4(),
        slug="desenvolvimento-e-experimentacao-com-modelos-de-ia-2",
        signal_count=40,
        week_number=18,
        created_at=datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc),
        **common,
    )
    db_session.add_all([older, newer])
    db_session.commit()

    data = client.get("/api/signals/clusters").json()

    assert data["total"] == 1
    # Ties on volume are broken by recency, so the newer copy survives.
    assert data["items"][0]["week_number"] == 18


def test_clusters_ranked_by_signal_count_not_composite_score(client, db_session):
    """Volume and recency are measured; composite_score is mostly defaults."""
    low_volume_high_score = SignalCluster(
        id=uuid.uuid4(),
        name="High score low volume",
        slug="high-score-low-volume",
        theme="AI",
        signal_count=3,
        composite_score=0.95,
        narrative_stage="emerging",
        week_number=12,
        year=2026,
        created_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    high_volume_low_score = SignalCluster(
        id=uuid.uuid4(),
        name="Low score high volume",
        slug="low-score-high-volume",
        theme="AI",
        signal_count=90,
        composite_score=0.30,
        narrative_stage="emerging",
        week_number=12,
        year=2026,
        created_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([low_volume_high_score, high_volume_low_score])
    db_session.commit()

    data = client.get("/api/signals/clusters?min_score=0").json()

    assert data["items"][0]["slug"] == "low-score-high-volume"


def test_cluster_description_dropped_when_it_is_a_raw_post(client, db_session):
    """A verbatim post quote is not a summary — blank it rather than publish it."""
    spam_text = (
        "Work Life as a Investment Banker. Viral Trending TikTok. "
        "#shorts Please Like And Subscribe"
    )
    cluster = SignalCluster(
        id=uuid.uuid4(),
        name="Investment Banking",
        slug="investment-banking",
        theme="Fintech",
        description=spam_text,
        signal_count=10,
        composite_score=0.5,
        narrative_stage="emerging",
        top_posts=[{"platform": "tiktok", "text": spam_text}],
        week_number=12,
        year=2026,
        created_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()

    data = client.get("/api/signals/clusters").json()

    assert data["items"][0]["description"] is None
    # And the detail endpoint applies the same guard.
    detail = client.get("/api/signals/clusters/investment-banking").json()
    assert detail["description"] is None


def test_cluster_drops_hashtag_spam_from_top_posts(client, db_session):
    """Posts stuffed with hashtags are promotion, not signal."""
    cluster = SignalCluster(
        id=uuid.uuid4(),
        name="Crypto Chatter",
        slug="crypto-chatter",
        theme="Fintech",
        description="A genuine summary of what these accounts are discussing.",
        signal_count=10,
        composite_score=0.5,
        narrative_stage="emerging",
        top_posts=[
            {"platform": "twitter", "text": "Real analysis of the sector"},
            {
                "platform": "twitter",
                "text": "BUY NOW #crypto #moon #shitcoin #pump #100x",
            },
        ],
        week_number=12,
        year=2026,
        created_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()

    data = client.get("/api/signals/clusters").json()
    posts = data["items"][0]["top_posts"]

    assert len(posts) == 1
    assert posts[0]["text"] == "Real analysis of the sector"
    # A real summary survives the guard.
    assert data["items"][0]["description"].startswith("A genuine summary")
