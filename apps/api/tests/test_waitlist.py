"""Tests for waitlist router."""

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
from packages.database.models.user import User


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
def sample_waitlist_users(db_session):
    """Create sample waitlist users."""
    users = [
        User(
            id=uuid.uuid4(),
            email="user1@example.com",
            name="User One",
            role="CTO",
            company="Company A",
            waitlist_position=1,
            status="waitlist",
        ),
        User(
            id=uuid.uuid4(),
            email="user2@example.com",
            name="User Two",
            role="Engineer",
            company="Company B",
            waitlist_position=2,
            status="waitlist",
        ),
    ]
    for user in users:
        db_session.add(user)
    db_session.commit()
    return users


def test_signup_waitlist_success(client):
    """Test successful waitlist signup."""
    payload = {
        "email": "test@example.com",
        "name": "Test User",
        "role": "CTO",
        "company": "Test Co",
    }
    response = client.post("/api/waitlist", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "lista" in data["message"].lower()
    assert data["position"] == 1


def test_signup_waitlist_position_increments(client, db_session):
    """Test that waitlist positions increment correctly."""
    # Add first user
    payload1 = {
        "email": "user1@example.com",
        "name": "User One",
        "role": "CTO",
        "company": "Company A",
    }
    response1 = client.post("/api/waitlist", json=payload1)
    assert response1.status_code == 200
    assert response1.json()["position"] == 1

    # Add second user
    payload2 = {
        "email": "user2@example.com",
        "name": "User Two",
        "role": "Engineer",
        "company": "Company B",
    }
    response2 = client.post("/api/waitlist", json=payload2)
    assert response2.status_code == 200
    assert response2.json()["position"] == 2


def test_signup_waitlist_email_normalization(client):
    """Test that emails are normalized (lowercase, trimmed)."""
    payload = {
        "email": "  Test@Example.COM  ",
        "name": "Test User",
        "role": "CTO",
        "company": "Test Co",
    }
    response = client.post("/api/waitlist", json=payload)

    assert response.status_code == 200

    # Try to sign up again with same email (different case/whitespace)
    payload2 = {
        "email": "test@example.com",
        "name": "Another User",
        "role": "Engineer",
        "company": "Another Co",
    }
    response2 = client.post("/api/waitlist", json=payload2)
    assert response2.status_code == 409
    assert "já cadastrado" in response2.json()["detail"].lower()


def test_signup_waitlist_duplicate_email(client, sample_waitlist_users):
    """Test that duplicate email returns 409."""
    payload = {
        "email": "user1@example.com",
        "name": "Duplicate User",
        "role": "CTO",
        "company": "Test Co",
    }
    response = client.post("/api/waitlist", json=payload)

    assert response.status_code == 409
    assert "já cadastrado" in response.json()["detail"].lower()


def test_signup_waitlist_invalid_email(client):
    """Test that invalid email returns 400."""
    invalid_emails = [
        "notanemail",
        "missing@domain",
        "@nodomain.com",
        "spaces in@email.com",
    ]

    for email in invalid_emails:
        payload = {
            "email": email,
            "name": "Test User",
            "role": "CTO",
            "company": "Test Co",
        }
        response = client.post("/api/waitlist", json=payload)
        assert response.status_code == 400
        assert "inválido" in response.json()["detail"].lower()


def test_signup_waitlist_missing_fields(client):
    """Test that missing required fields returns 422."""
    # Missing email
    response = client.post("/api/waitlist", json={"name": "Test"})
    assert response.status_code == 422


def test_waitlist_count_empty(client):
    """Test waitlist count when empty."""
    response = client.get("/api/waitlist/count")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0


def test_waitlist_count_with_users(client, sample_waitlist_users):
    """Test waitlist count with users."""
    response = client.get("/api/waitlist/count")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2


def test_list_waitlist_users_success(client, sample_waitlist_users):
    """Test listing waitlist users."""
    response = client.get("/api/waitlist/list")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Should be ordered by position ascending
    assert data[0]["email"] == "user1@example.com"
    assert data[0]["waitlist_position"] == 1
    assert data[1]["email"] == "user2@example.com"
    assert data[1]["waitlist_position"] == 2


def test_list_waitlist_users_pagination(client, sample_waitlist_users):
    """Test pagination of waitlist users."""
    response = client.get("/api/waitlist/list?limit=1&offset=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == "user2@example.com"


def test_list_waitlist_users_includes_all_fields(client, sample_waitlist_users):
    """Test that list endpoint includes all user fields."""
    response = client.get("/api/waitlist/list")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    user = data[0]
    required_fields = {
        "id", "email", "name", "role", "company",
        "waitlist_position", "created_at"
    }
    assert required_fields.issubset(set(user.keys()))


def test_waitlist_only_counts_waitlist_status(client, db_session):
    """Test that count only includes users with waitlist status."""
    # Add a waitlist user
    waitlist_user = User(
        id=uuid.uuid4(),
        email="waitlist@example.com",
        name="Waitlist User",
        waitlist_position=1,
        status="waitlist",
    )
    db_session.add(waitlist_user)

    # Add an active user (not in waitlist)
    active_user = User(
        id=uuid.uuid4(),
        email="active@example.com",
        name="Active User",
        status="active",
    )
    db_session.add(active_user)
    db_session.commit()

    response = client.get("/api/waitlist/count")
    assert response.status_code == 200
    # Should only count waitlist user, not active user
    assert response.json()["count"] == 1
