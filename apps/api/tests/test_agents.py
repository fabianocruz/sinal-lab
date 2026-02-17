"""Tests for agents router."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.main import app
from apps.api.deps import get_db
from packages.database.models.base import Base
from packages.database.models.agent_run import AgentRun


# Test database setup
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
def sample_agent_runs(db_session):
    """Create sample agent runs for testing."""
    runs = [
        AgentRun(
            run_id="run-001",
            agent_name="sintese",
            status="completed",
            started_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 2, 15, 10, 5, 0, tzinfo=timezone.utc),
            items_processed=25,
            avg_confidence=0.85,
            data_sources={"techmeme": 10, "hackernews": 15},
            error_count=0,
        ),
        AgentRun(
            run_id="run-002",
            agent_name="radar",
            status="completed",
            started_at=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 2, 16, 10, 3, 0, tzinfo=timezone.utc),
            items_processed=12,
            avg_confidence=0.72,
            data_sources={"github": 12},
            error_count=1,
        ),
        AgentRun(
            run_id="run-003",
            agent_name="sintese",
            status="failed",
            started_at=datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 2, 17, 10, 1, 0, tzinfo=timezone.utc),
            items_processed=0,
            avg_confidence=None,
            data_sources={},
            error_count=5,
            error_message="RSS feed timeout",
        ),
    ]
    for run in runs:
        db_session.add(run)
    db_session.commit()
    return runs


def test_list_agent_runs_all(client, sample_agent_runs):
    """Test listing all agent runs."""
    response = client.get("/api/agents/runs")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Should be ordered by started_at descending
    assert data[0]["run_id"] == "run-003"
    assert data[1]["run_id"] == "run-002"
    assert data[2]["run_id"] == "run-001"


def test_list_agent_runs_filter_by_agent(client, sample_agent_runs):
    """Test filtering runs by agent name."""
    response = client.get("/api/agents/runs?agent_name=sintese")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(run["agent_name"] == "sintese" for run in data)


def test_list_agent_runs_filter_by_status(client, sample_agent_runs):
    """Test filtering runs by status."""
    response = client.get("/api/agents/runs?status=completed")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(run["status"] == "completed" for run in data)


def test_list_agent_runs_pagination(client, sample_agent_runs):
    """Test pagination with limit and offset."""
    response = client.get("/api/agents/runs?limit=2&offset=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["run_id"] == "run-002"


def test_list_agent_runs_limit_validation(client, sample_agent_runs):
    """Test that limit is validated."""
    # Limit too high
    response = client.get("/api/agents/runs?limit=200")
    assert response.status_code == 422

    # Limit too low
    response = client.get("/api/agents/runs?limit=0")
    assert response.status_code == 422


def test_get_agent_run_success(client, sample_agent_runs):
    """Test getting a specific agent run."""
    response = client.get("/api/agents/runs/run-001")

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "run-001"
    assert data["agent_name"] == "sintese"
    assert data["status"] == "completed"
    assert data["items_processed"] == 25


def test_get_agent_run_not_found(client, sample_agent_runs):
    """Test getting non-existent run returns 404."""
    response = client.get("/api/agents/runs/run-999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_agent_summary(client, sample_agent_runs):
    """Test getting summary of latest run per agent."""
    response = client.get("/api/agents/summary")

    assert response.status_code == 200
    data = response.json()

    # Should have 2 agents (sintese, radar)
    assert len(data) == 2

    # Check structure
    agent_names = {item["agent_name"] for item in data}
    assert agent_names == {"sintese", "radar"}

    # Verify sintese shows latest run (run-003)
    sintese_summary = next(s for s in data if s["agent_name"] == "sintese")
    assert sintese_summary["status"] == "failed"
    assert sintese_summary["error_count"] == 5
    assert sintese_summary["items_processed"] == 0


def test_trigger_agent_valid(client):
    """Test triggering a valid agent."""
    response = client.post("/api/agents/runs/sintese/trigger")

    assert response.status_code == 200
    data = response.json()
    assert "sintese" in data["message"]
    assert data["status"] == "queued"


def test_trigger_agent_invalid(client):
    """Test triggering an invalid agent name."""
    response = client.post("/api/agents/runs/invalid-agent/trigger")

    assert response.status_code == 400
    assert "Unknown agent" in response.json()["detail"]


def test_trigger_all_valid_agents(client):
    """Test that all valid agents can be triggered."""
    valid_agents = ["sintese", "radar", "codigo", "funding", "mercado"]

    for agent in valid_agents:
        response = client.post(f"/api/agents/runs/{agent}/trigger")
        assert response.status_code == 200
        assert agent in response.json()["message"]
