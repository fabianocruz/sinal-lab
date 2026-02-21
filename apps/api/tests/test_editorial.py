"""Tests for editorial router."""

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from apps.api.deps import get_db
from packages.database.models.base import Base
from packages.database.models.content_piece import ContentPiece


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
    """Create sample content for testing."""
    pieces = [
        ContentPiece(
            id=uuid.uuid4(),
            slug="draft-article-1",
            title="Draft Article 1",
            content_type="DATA_REPORT",
            agent_name="sintese",
            body_markdown="# Test content",
            body_md="# Test content",
            confidence_dq=0.75,
            confidence_ac=0.70,
            review_status="draft",
            publish_ready=False,
        ),
        ContentPiece(
            id=uuid.uuid4(),
            slug="review-article-1",
            title="Article in Review",
            content_type="TREND_ANALYSIS",
            agent_name="radar",
            body_markdown="# Review content",
            body_md="# Review content",
            confidence_dq=0.80,
            confidence_ac=0.75,
            review_status="review",
            publish_ready=False,
        ),
        ContentPiece(
            id=uuid.uuid4(),
            slug="published-article-1",
            title="Published Article",
            content_type="DATA_REPORT",
            agent_name="sintese",
            body_markdown="# Published content",
            body_md="# Published content",
            confidence_dq=0.85,
            confidence_ac=0.80,
            review_status="published",
            publish_ready=True,
            published_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for piece in pieces:
        db_session.add(piece)
    db_session.commit()
    return pieces


def test_review_content_success(client, sample_content):
    """Test running editorial pipeline on content."""
    payload = {"content_slug": "draft-article-1"}
    response = client.post("/api/editorial/review", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    required_fields = {
        "content_title", "agent_name", "run_id", "publish_ready",
        "overall_grade", "blocker_count", "layers_run", "total_flags"
    }
    assert required_fields.issubset(set(data.keys()))

    # Verify data
    assert data["content_title"] == "Draft Article 1"
    assert data["agent_name"] == "sintese"
    assert isinstance(data["publish_ready"], bool)
    assert isinstance(data["layers_run"], int)


def test_review_content_not_found(client, sample_content):
    """Test reviewing non-existent content."""
    payload = {"content_slug": "non-existent-slug"}
    response = client.post("/api/editorial/review", json=payload)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_review_queue(client, sample_content):
    """Test getting editorial review queue."""
    response = client.get("/api/editorial/queue")

    assert response.status_code == 200
    data = response.json()

    # Should return only draft and review status content
    assert len(data) == 2

    # Verify all are in draft or review status
    statuses = {item["review_status"] for item in data}
    assert statuses.issubset({"draft", "review"})

    # Verify no published content
    assert not any(item["review_status"] == "published" for item in data)


def test_get_review_queue_pagination(client, sample_content):
    """Test review queue pagination."""
    response = client.get("/api/editorial/queue?limit=1&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_review_queue_response_fields(client, sample_content):
    """Test review queue response includes required fields."""
    response = client.get("/api/editorial/queue")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    item = data[0]
    required_fields = {
        "id", "title", "slug", "content_type", "agent_name",
        "review_status", "confidence_dq", "confidence_ac"
    }
    assert required_fields.issubset(set(item.keys()))


def test_approve_content_success(client, sample_content):
    """Test approving content for publication."""
    payload = {
        "reviewer_name": "Test Reviewer",
        "notes": "Looks good"
    }
    response = client.post("/api/editorial/approve/draft-article-1", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["slug"] == "draft-article-1"
    assert data["review_status"] == "published"
    assert data["reviewer"] == "Test Reviewer"
    assert "approved" in data["message"].lower()


def test_approve_content_sets_published_at(client, sample_content, db_session):
    """Test that approving content sets published_at timestamp."""
    payload = {"reviewer_name": "Test"}
    response = client.post("/api/editorial/approve/draft-article-1", json=payload)

    assert response.status_code == 200

    # Verify in database
    piece = db_session.query(ContentPiece).filter(
        ContentPiece.slug == "draft-article-1"
    ).first()
    assert piece.review_status == "published"
    assert piece.published_at is not None


def test_approve_content_not_found(client, sample_content):
    """Test approving non-existent content."""
    payload = {"reviewer_name": "Test"}
    response = client.post("/api/editorial/approve/non-existent", json=payload)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_approve_already_published_content(client, sample_content):
    """Test approving already published content returns error."""
    payload = {"reviewer_name": "Test"}
    response = client.post("/api/editorial/approve/published-article-1", json=payload)

    assert response.status_code == 400
    assert "already published" in response.json()["detail"].lower()


def test_approve_content_without_reviewer_name(client, sample_content):
    """Test approving content without reviewer name."""
    payload = {}
    response = client.post("/api/editorial/approve/draft-article-1", json=payload)

    # Should succeed (reviewer_name is optional)
    assert response.status_code == 200
    data = response.json()
    assert data["reviewer"] is None


def test_get_editorial_history_success(client, sample_content):
    """Test getting editorial history for content."""
    response = client.get("/api/editorial/history/draft-article-1")

    assert response.status_code == 200
    data = response.json()

    required_fields = {
        "slug", "title", "review_status", "content_type",
        "agent_name", "created_at", "revisions"
    }
    assert required_fields.issubset(set(data.keys()))

    # Verify revisions array exists
    assert isinstance(data["revisions"], list)
    assert len(data["revisions"]) > 0


def test_get_editorial_history_not_found(client, sample_content):
    """Test getting history for non-existent content."""
    response = client.get("/api/editorial/history/non-existent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_review_queue_ordering(client, sample_content):
    """Test that review queue is ordered by created_at descending."""
    response = client.get("/api/editorial/queue")

    assert response.status_code == 200
    data = response.json()

    # Most recent should be first
    # review-article-1 was created after draft-article-1
    assert data[0]["slug"] == "review-article-1"
    assert data[1]["slug"] == "draft-article-1"


def test_review_content_pipeline_executes(client, sample_content):
    """Test that editorial pipeline actually executes layers."""
    payload = {"content_slug": "draft-article-1"}
    response = client.post("/api/editorial/review", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Should run all 6 layers
    assert data["layers_run"] == 6

    # Should have an overall grade (A, B, C, or D)
    assert data["overall_grade"] in ["A", "B", "C", "D"]

    # Should have blocker count (>= 0)
    assert data["blocker_count"] >= 0
