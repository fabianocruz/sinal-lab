"""Tests for content router."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.main import app
from apps.api.deps import get_db
from packages.database.models.base import Base
from packages.database.models.content_piece import ContentPiece


SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
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
            body_markdown="# Newsletter content",
            confidence_dq=0.85,
            confidence_ac=0.78,
            review_status="published",
            publish_ready=True,
            published_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="trend-ai-agents-2026",
            title="AI Agents Rising in 2026",
            content_type="TREND_ANALYSIS",
            agent_name="radar",
            body_markdown="# Trend analysis content",
            confidence_dq=0.72,
            confidence_ac=0.68,
            review_status="published",
            publish_ready=True,
            published_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="draft-article",
            title="Draft Article",
            content_type="ARTICLE",
            agent_name="codigo",
            body_markdown="# Draft content",
            confidence_dq=0.65,
            confidence_ac=0.60,
            review_status="pending",
            publish_ready=False,
            published_at=None,
        ),
    ]
    for piece in pieces:
        db_session.add(piece)
    db_session.commit()
    return pieces


def test_list_content_all(client, sample_content):
    """Test listing all content pieces."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_list_content_filter_by_type(client, sample_content):
    """Test filtering content by type."""
    response = client.get("/api/content?content_type=DATA_REPORT")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "newsletter-edition-1"


def test_list_content_filter_by_agent(client, sample_content):
    """Test filtering content by agent."""
    response = client.get("/api/content?agent_name=radar")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["agent_name"] == "radar"


def test_list_content_filter_by_status(client, sample_content):
    """Test filtering content by review status."""
    response = client.get("/api/content?status=published")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(c["review_status"] == "published" for c in data)


def test_list_content_pagination(client, sample_content):
    """Test content pagination."""
    response = client.get("/api/content?limit=2&offset=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


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
    assert "body_markdown" in data


def test_get_content_by_slug_not_found(client, sample_content):
    """Test getting non-existent content."""
    response = client.get("/api/content/non-existent-slug")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_content_ordering(client, sample_content):
    """Test that content is ordered by created_at descending."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()

    # Verify descending order (most recent first)
    # Draft article should be first (most recent created_at)
    assert data[0]["slug"] == "draft-article"


def test_content_response_schema(client, sample_content):
    """Test content response includes all required fields."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    # Check first item has required fields
    item = data[0]
    required_fields = {
        "slug", "title", "content_type", "agent_name",
        "confidence_dq", "confidence_ac", "review_status"
    }
    assert required_fields.issubset(set(item.keys()))
