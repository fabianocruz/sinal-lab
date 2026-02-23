"""Tests for content router.

Uses SQLite in-memory with StaticPool so all threads share the same
database connection. This is required because FastAPI runs sync endpoints
in a worker thread pool — without StaticPool, each thread would get a
separate in-memory database and see "no such table" errors.

Run: pytest apps/api/tests/test_content.py -v
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from apps.api.deps import get_db
from packages.database.models.base import Base
from packages.database.models.content_piece import ContentPiece


# StaticPool ensures all threads share a single connection to the in-memory DB.
# Without it, FastAPI's thread pool creates separate connections that can't
# see each other's tables. See: https://sqlalche.me/e/20/e3q8
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


@pytest.fixture
def sample_content(db_session):
    """Create sample content pieces for testing."""
    pieces = [
        ContentPiece(
            slug="newsletter-edition-1",
            title="Newsletter Edition #1",
            content_type="DATA_REPORT",
            agent_name="sintese",
            body_md="# Newsletter content",
            confidence_dq=0.85,
            confidence_ac=0.78,
            review_status="published",
            published_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="trend-ai-agents-2026",
            title="AI Agents Rising in 2026",
            content_type="TREND_ANALYSIS",
            agent_name="radar",
            body_md="# Trend analysis content",
            confidence_dq=0.72,
            confidence_ac=0.68,
            review_status="published",
            published_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="draft-article",
            title="Draft Article",
            content_type="ARTICLE",
            agent_name="codigo",
            body_md="# Draft content",
            confidence_dq=0.65,
            confidence_ac=0.60,
            review_status="pending",
            published_at=None,
            created_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for piece in pieces:
        db_session.add(piece)
    db_session.commit()
    return pieces


def test_list_content_all(client, sample_content):
    """Test listing all content pieces returns paginated response."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_content_filter_by_type(client, sample_content):
    """Test filtering content by type."""
    response = client.get("/api/content?content_type=DATA_REPORT")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "newsletter-edition-1"


def test_list_content_exclude_by_type(client, sample_content):
    """Test excluding content by type (content_type_exclude)."""
    response = client.get("/api/content?content_type_exclude=ARTICLE")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(c["content_type"] != "ARTICLE" for c in data["items"])


def test_list_content_filter_by_agent(client, sample_content):
    """Test filtering content by agent."""
    response = client.get("/api/content?agent_name=radar")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["agent_name"] == "radar"


def test_list_content_filter_by_status(client, sample_content):
    """Test filtering content by review status."""
    response = client.get("/api/content?status=published")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(c["review_status"] == "published" for c in data["items"])


def test_list_content_search(client, sample_content):
    """Test searching content by title."""
    response = client.get("/api/content?search=Newsletter")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "newsletter-edition-1"


def test_list_content_pagination(client, sample_content):
    """Test content pagination."""
    response = client.get("/api/content?limit=2&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Second page
    response2 = client.get("/api/content?limit=2&offset=2")
    data2 = response2.json()
    assert len(data2["items"]) == 1


def test_list_content_limit_validation(client, sample_content):
    """Test limit validation."""
    # Too high
    response = client.get("/api/content?limit=200")
    assert response.status_code == 422

    # Too low
    response = client.get("/api/content?limit=0")
    assert response.status_code == 422


def test_get_latest_newsletter_success(client, sample_content):
    """Test getting the latest published newsletter."""
    response = client.get("/api/content/newsletter/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "newsletter-edition-1"
    assert data["content_type"] == "DATA_REPORT"


def test_get_latest_newsletter_not_found(client):
    """Test getting latest newsletter when none exists."""
    response = client.get("/api/content/newsletter/latest")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_content_by_slug_success(client, sample_content):
    """Test getting content by slug."""
    response = client.get("/api/content/newsletter-edition-1")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "newsletter-edition-1"
    assert data["title"] == "Newsletter Edition #1"
    assert "body_md" in data


def test_get_content_by_slug_not_found(client, sample_content):
    """Test getting non-existent content."""
    response = client.get("/api/content/non-existent-slug")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_content_ordering(client, sample_content):
    """Test that content is ordered by published_at descending."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    items = data["items"]

    # Verify descending order by published_at (most recent first)
    # newsletter-edition-1 has published_at=Feb 15 (latest)
    assert items[0]["slug"] == "newsletter-edition-1"


def test_content_response_schema(client, sample_content):
    """Test content response includes all required fields."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0

    item = data["items"][0]
    required_fields = {
        "slug", "title", "content_type", "agent_name",
        "confidence_dq", "confidence_ac", "review_status"
    }
    assert required_fields.issubset(set(item.keys()))
