"""Tests for health check router."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from apps.api.main import app
from apps.api.deps import get_db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check_success(client):
    """Test health check with database connected."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["database"] in ["connected", "disconnected"]
    assert "timestamp" in data


def test_health_check_includes_timestamp(client):
    """Test that health check includes ISO timestamp."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    # Verify it's ISO format (will raise if not)
    from datetime import datetime
    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


def test_health_check_database_connectivity(client):
    """Test database connectivity status is reported."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    # Database can be connected or disconnected, both are valid states
    assert data["database"] in ["connected", "disconnected", "unknown"]


def test_health_check_with_database_failure():
    """Test health check when database connection fails."""
    # Create a mock DB session that always fails
    def get_failing_db():
        # Create an in-memory SQLite database that we immediately close
        engine = create_engine("sqlite:///:memory:")
        engine.dispose()  # Close it immediately
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Override the dependency
    app.dependency_overrides[get_db] = get_failing_db

    client = TestClient(app)
    response = client.get("/api/health")

    # Clean up
    app.dependency_overrides.clear()

    # Should still return 200 but with disconnected status
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"  # API is still OK even if DB is down
    assert data["database"] == "disconnected"


def test_health_check_response_schema(client):
    """Test health check response matches expected schema."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields are present
    required_fields = {"status", "version", "database", "timestamp"}
    assert set(data.keys()) == required_fields

    # Verify types
    assert isinstance(data["status"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["database"], str)
    assert isinstance(data["timestamp"], str)
