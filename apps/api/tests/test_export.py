"""Tests for export router — CSV downloads for signals and curated feed.

Uses SQLite in-memory with StaticPool so all threads share the same
database connection (same pattern as test_signals.py).

Run: pytest apps/api/tests/test_export.py -v
"""

import csv
import io
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
from packages.database.models.curated_feed_item import CuratedFeedItem
from packages.database.models.social_signal import SocialSignal

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
    """Create sample social signals for export testing."""
    signals = [
        SocialSignal(
            id=uuid.uuid4(),
            platform="twitter",
            post_url="https://twitter.com/founder1/status/1",
            author_handle="founder1",
            author_display_name="Founder One",
            text="AI is transforming fintech in LATAM",
            content_hash="export_hash001",
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
            content_hash="export_hash002",
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
            content_hash="export_hash003",
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
def sample_feed_items(db_session):
    """Create sample curated feed items for export testing."""
    items = [
        CuratedFeedItem(
            id=uuid.uuid4(),
            content_hash="feed_hash001",
            editorial_headline="AI startups raise record funding",
            editorial_context="Multiple AI startups in LATAM closed rounds this week.",
            relevance_score=95,
            category="AI",
            source_platform="twitter",
            source_url="https://twitter.com/founder1/status/1",
            source_author="founder1",
            thumbnail_url="https://example.com/thumb1.jpg",
            curated_at=datetime(2026, 3, 20, 14, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 3, 20, 14, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 20, 14, 0, 0, tzinfo=timezone.utc),
        ),
        CuratedFeedItem(
            id=uuid.uuid4(),
            content_hash="feed_hash002",
            editorial_headline="Brazil fintech regulation update",
            editorial_context="New regulations expected to impact fintech sector.",
            relevance_score=80,
            category="Fintech",
            source_platform="twitter",
            source_url="https://twitter.com/regulator/status/5",
            source_author="regulator_br",
            curated_at=datetime(2026, 3, 19, 14, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 3, 19, 14, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 19, 14, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_csv(content: str) -> list[dict[str, str]]:
    """Parse CSV content into a list of dicts keyed by header."""
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


# ---------------------------------------------------------------------------
# Tests — Signals export
# ---------------------------------------------------------------------------


class TestExportSignals:
    """Tests for GET /api/export/signals."""

    def test_csv_returns_valid_csv_with_correct_headers(self, client, sample_signals):
        """CSV response has correct headers and matching row count."""
        response = client.get("/api/export/signals")

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        rows = _parse_csv(response.text)
        assert len(rows) == 3

        expected_headers = {
            "platform", "author_handle", "author_display_name", "text",
            "post_url", "published_at", "theme", "sub_theme", "sentiment",
            "authority_score", "likes", "replies", "reposts",
        }
        assert set(rows[0].keys()) == expected_headers

    def test_csv_contains_correct_data(self, client, sample_signals):
        """Spot-check that row values match the seed data."""
        response = client.get("/api/export/signals")
        rows = _parse_csv(response.text)

        # First row should be the most recent signal (published_at desc)
        first = rows[0]
        assert first["platform"] == "twitter"
        assert first["author_handle"] == "founder1"
        assert first["theme"] == "AI"
        assert first["likes"] == "120"
        assert first["replies"] == "15"
        assert first["reposts"] == "30"

    def test_theme_filter(self, client, sample_signals):
        """Theme query parameter filters results correctly."""
        response = client.get("/api/export/signals?theme=AI")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 1
        assert rows[0]["theme"] == "AI"

    def test_platform_filter(self, client, sample_signals):
        """Platform query parameter filters results correctly."""
        response = client.get("/api/export/signals?platform=reddit")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 1
        assert rows[0]["platform"] == "reddit"

    def test_search_filter(self, client, sample_signals):
        """Search query parameter performs text LIKE filtering."""
        response = client.get("/api/export/signals?search=fintech")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 1
        assert "fintech" in rows[0]["text"].lower()

    def test_empty_result_returns_headers_only(self, client):
        """When no signals exist, CSV has headers but no data rows."""
        response = client.get("/api/export/signals")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 0

        # Verify headers still present in the raw content
        first_line = response.text.split("\n")[0]
        assert "platform" in first_line
        assert "author_handle" in first_line

    def test_content_disposition_header(self, client, sample_signals):
        """Response includes Content-Disposition with dated filename."""
        response = client.get("/api/export/signals")

        assert response.status_code == 200
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "sinal-signals-" in disposition
        assert ".csv" in disposition

    def test_limit_parameter(self, client, sample_signals):
        """Limit parameter caps the number of exported rows."""
        response = client.get("/api/export/signals?limit=2")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 2

    def test_offset_parameter(self, client, sample_signals):
        """Offset parameter skips rows correctly."""
        response = client.get("/api/export/signals?offset=2")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 1

    def test_text_truncation(self, client, db_session):
        """Text longer than 500 chars is truncated in export."""
        long_text = "A" * 1000
        signal = SocialSignal(
            id=uuid.uuid4(),
            platform="twitter",
            post_url="https://twitter.com/test/status/999",
            text=long_text,
            content_hash="export_hash_long",
            published_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        )
        db_session.add(signal)
        db_session.commit()

        response = client.get("/api/export/signals")
        rows = _parse_csv(response.text)
        assert len(rows[0]["text"]) == 500

    def test_missing_metrics_handled_gracefully(self, client, sample_signals):
        """Signals with no metrics dict export empty strings for metric cols."""
        # The third signal (reddit) has no reposts in metrics
        response = client.get("/api/export/signals?platform=reddit")
        rows = _parse_csv(response.text)
        assert len(rows) == 1
        assert rows[0]["reposts"] == ""  # no reposts key in metrics


# ---------------------------------------------------------------------------
# Tests — Feed export
# ---------------------------------------------------------------------------


class TestExportFeed:
    """Tests for GET /api/export/feed."""

    def test_csv_returns_valid_csv_with_correct_headers(self, client, sample_feed_items):
        """CSV response has correct headers and matching row count."""
        response = client.get("/api/export/feed")

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        rows = _parse_csv(response.text)
        assert len(rows) == 2

        expected_headers = {
            "editorial_headline", "editorial_context", "category",
            "relevance_score", "source_platform", "source_url",
            "source_author", "thumbnail_url", "curated_at",
        }
        assert set(rows[0].keys()) == expected_headers

    def test_csv_contains_correct_data(self, client, sample_feed_items):
        """Spot-check that row values match the seed data."""
        response = client.get("/api/export/feed")
        rows = _parse_csv(response.text)

        # First row is highest relevance_score (desc order)
        first = rows[0]
        assert first["editorial_headline"] == "AI startups raise record funding"
        assert first["category"] == "AI"
        assert first["relevance_score"] == "95"
        assert first["source_platform"] == "twitter"

    def test_category_filter(self, client, sample_feed_items):
        """Category query parameter filters results correctly."""
        response = client.get("/api/export/feed?category=Fintech")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 1
        assert rows[0]["category"] == "Fintech"

    def test_theme_alias_filter(self, client, sample_feed_items):
        """Theme query parameter works as alias for category."""
        response = client.get("/api/export/feed?theme=AI")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 1
        assert rows[0]["category"] == "AI"

    def test_empty_result_returns_headers_only(self, client):
        """When no feed items exist, CSV has headers but no data rows."""
        response = client.get("/api/export/feed")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 0

        first_line = response.text.split("\n")[0]
        assert "editorial_headline" in first_line

    def test_content_disposition_header(self, client, sample_feed_items):
        """Response includes Content-Disposition with dated filename."""
        response = client.get("/api/export/feed")

        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "sinal-feed-" in disposition
        assert ".csv" in disposition

    def test_limit_parameter(self, client, sample_feed_items):
        """Limit parameter caps the number of exported rows."""
        response = client.get("/api/export/feed?limit=1")

        assert response.status_code == 200
        rows = _parse_csv(response.text)
        assert len(rows) == 1

    def test_nullable_fields_export_empty_string(self, client, sample_feed_items):
        """Nullable fields (e.g. thumbnail_url) export as empty strings."""
        # Second feed item has no thumbnail_url
        response = client.get("/api/export/feed?category=Fintech")
        rows = _parse_csv(response.text)
        assert rows[0]["thumbnail_url"] == ""
