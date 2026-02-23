"""Tests for the Sinal.lab FastAPI backend.

Uses an in-memory SQLite database and httpx TestClient.
"""

import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Import all models to ensure they register with Base.metadata
from packages.database.models import Base, AgentRun, Company, ContentPiece, User
from packages.database.models.investor import Investor
from packages.database.models.funding_round import FundingRound
from packages.database.models.ecosystem import Ecosystem

from apps.api.main import app
from apps.api.deps import get_db


# Use StaticPool so all connections share the same in-memory SQLite database
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    """Provide a test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Provide a direct database session for seeding test data."""
    session = TestSessionLocal()
    yield session
    session.close()


# ===== Root & Health =====


class TestRoot:
    def test_root(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sinal.lab API"
        assert data["version"] == "0.1.0"

    def test_health(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
        assert "timestamp" in data


# ===== Agents Router =====


class TestAgentsRouter:
    def test_list_runs_empty(self, client: TestClient):
        response = client.get("/api/agents/runs")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_runs_with_data(self, client: TestClient, db_session: Session):
        now = datetime.now(timezone.utc)
        run = AgentRun(
            id=uuid.uuid4(),
            agent_name="sintese",
            run_id="sintese-test-001",
            started_at=now,
            status="completed",
            items_collected=100,
        )
        db_session.add(run)
        db_session.commit()

        response = client.get("/api/agents/runs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["agent_name"] == "sintese"
        assert data[0]["run_id"] == "sintese-test-001"

    def test_list_runs_filter_by_agent(self, client: TestClient, db_session: Session):
        now = datetime.now(timezone.utc)
        for name in ["sintese", "radar", "radar"]:
            db_session.add(AgentRun(
                id=uuid.uuid4(), agent_name=name,
                run_id=f"{name}-{uuid.uuid4().hex[:6]}",
                started_at=now, status="completed",
            ))
        db_session.commit()

        response = client.get("/api/agents/runs?agent_name=radar")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(r["agent_name"] == "radar" for r in data)

    def test_get_run_by_id(self, client: TestClient, db_session: Session):
        now = datetime.now(timezone.utc)
        run = AgentRun(
            id=uuid.uuid4(), agent_name="codigo",
            run_id="codigo-test-001", started_at=now, status="running",
        )
        db_session.add(run)
        db_session.commit()

        response = client.get("/api/agents/runs/codigo-test-001")
        assert response.status_code == 200
        assert response.json()["run_id"] == "codigo-test-001"

    def test_get_run_not_found(self, client: TestClient):
        response = client.get("/api/agents/runs/nonexistent")
        assert response.status_code == 404

    def test_trigger_agent(self, client: TestClient):
        response = client.post("/api/agents/runs/sintese/trigger")
        assert response.status_code == 200
        assert response.json()["status"] == "queued"

    def test_trigger_invalid_agent(self, client: TestClient):
        response = client.post("/api/agents/runs/unknown_agent/trigger")
        assert response.status_code == 400


# ===== Content Router =====


class TestContentRouter:
    def test_list_content_empty(self, client: TestClient):
        response = client.get("/api/content")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_content_with_data(self, client: TestClient, db_session: Session):
        piece = ContentPiece(
            id=uuid.uuid4(),
            title="Sinal Semanal #1",
            slug="sinal-semanal-1",
            body_md="# Hello",
            content_type="DATA_REPORT",
            agent_name="sintese",
        )
        db_session.add(piece)
        db_session.commit()

        response = client.get("/api/content")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Sinal Semanal #1"

    def test_get_content_by_slug(self, client: TestClient, db_session: Session):
        piece = ContentPiece(
            id=uuid.uuid4(),
            title="RADAR W1",
            slug="radar-w1",
            body_md="# Trends",
            content_type="ANALYSIS",
        )
        db_session.add(piece)
        db_session.commit()

        response = client.get("/api/content/radar-w1")
        assert response.status_code == 200
        assert response.json()["slug"] == "radar-w1"

    def test_get_content_not_found(self, client: TestClient):
        response = client.get("/api/content/nonexistent")
        assert response.status_code == 404

    def test_get_latest_newsletter(self, client: TestClient, db_session: Session):
        now = datetime.now(timezone.utc)
        piece = ContentPiece(
            id=uuid.uuid4(),
            title="Sinal Semanal #5",
            slug="sinal-semanal-5",
            body_md="# Newsletter",
            content_type="DATA_REPORT",
            agent_name="sintese",
            review_status="published",
            published_at=now,
        )
        db_session.add(piece)
        db_session.commit()

        response = client.get("/api/content/newsletter/latest")
        assert response.status_code == 200
        assert response.json()["title"] == "Sinal Semanal #5"

    def test_get_latest_newsletter_none(self, client: TestClient):
        response = client.get("/api/content/newsletter/latest")
        assert response.status_code == 404

    def test_filter_by_content_type(self, client: TestClient, db_session: Session):
        for ct in ["DATA_REPORT", "ANALYSIS", "ANALYSIS"]:
            db_session.add(ContentPiece(
                id=uuid.uuid4(), title=f"Test {ct}",
                slug=f"test-{ct.lower()}-{uuid.uuid4().hex[:6]}",
                body_md="# Content", content_type=ct,
            ))
        db_session.commit()

        response = client.get("/api/content?content_type=ANALYSIS")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


# ===== Companies Router =====


class TestCompaniesRouter:
    def test_list_companies_empty(self, client: TestClient):
        response = client.get("/api/companies")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_companies_with_data(self, client: TestClient, db_session: Session):
        company = Company(
            id=uuid.uuid4(), name="Nubank", slug="nubank",
            sector="fintech", city="Sao Paulo", country="Brazil",
        )
        db_session.add(company)
        db_session.commit()

        response = client.get("/api/companies")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Nubank"

    def test_get_company_by_slug(self, client: TestClient, db_session: Session):
        company = Company(
            id=uuid.uuid4(), name="VTEX", slug="vtex",
            sector="e-commerce",
        )
        db_session.add(company)
        db_session.commit()

        response = client.get("/api/companies/vtex")
        assert response.status_code == 200
        assert response.json()["name"] == "VTEX"

    def test_company_not_found(self, client: TestClient):
        response = client.get("/api/companies/nonexistent")
        assert response.status_code == 404

    def test_filter_by_sector(self, client: TestClient, db_session: Session):
        for name, sector in [("A", "fintech"), ("B", "saas"), ("C", "fintech")]:
            db_session.add(Company(
                id=uuid.uuid4(), name=name, slug=name.lower(), sector=sector,
            ))
        db_session.commit()

        response = client.get("/api/companies?sector=fintech")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

    def test_filter_by_city(self, client: TestClient, db_session: Session):
        db_session.add(Company(
            id=uuid.uuid4(), name="X", slug="x",
            city="Florianopolis",
        ))
        db_session.add(Company(
            id=uuid.uuid4(), name="Y", slug="y",
            city="Sao Paulo",
        ))
        db_session.commit()

        response = client.get("/api/companies?city=Florianopolis")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1


# ===== Waitlist Router =====


class TestWaitlistRouter:
    def test_signup_success(self, client: TestClient):
        response = client.post("/api/waitlist", json={"email": "founder@startup.com"})
        assert response.status_code == 200
        data = response.json()
        assert "lista" in data["message"].lower() or "message" in data
        assert data["position"] == 1

    def test_signup_with_details(self, client: TestClient):
        response = client.post("/api/waitlist", json={
            "email": "cto@bigtech.com",
            "name": "Maria Silva",
            "role": "cto",
            "company": "BigTech Brasil",
        })
        assert response.status_code == 200

    def test_signup_duplicate(self, client: TestClient):
        client.post("/api/waitlist", json={"email": "dup@test.com"})
        response = client.post("/api/waitlist", json={"email": "dup@test.com"})
        assert response.status_code == 409

    def test_signup_invalid_email(self, client: TestClient):
        response = client.post("/api/waitlist", json={"email": "not-an-email"})
        assert response.status_code == 400

    def test_waitlist_count(self, client: TestClient):
        response = client.get("/api/waitlist/count")
        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_waitlist_count_after_signups(self, client: TestClient):
        for i in range(3):
            client.post("/api/waitlist", json={"email": f"user{i}@test.com"})

        response = client.get("/api/waitlist/count")
        assert response.status_code == 200
        assert response.json()["count"] == 3

    def test_sequential_positions(self, client: TestClient):
        positions = []
        for i in range(5):
            resp = client.post("/api/waitlist", json={"email": f"seq{i}@test.com"})
            positions.append(resp.json()["position"])

        assert positions == [1, 2, 3, 4, 5]
