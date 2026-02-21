"""Tests for companies router."""

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
from packages.database.models.company import Company


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
def sample_companies(db_session):
    """Create sample companies for testing."""
    companies = [
        Company(
            id=uuid.uuid4(),
            slug="nubank",
            name="Nubank",
            sector="Fintech",
            city="São Paulo",
            country="Brazil",
            status="active",
            website="https://nubank.com.br",
            created_at=datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
        ),
        Company(
            id=uuid.uuid4(),
            slug="mercadolibre",
            name="MercadoLibre",
            sector="E-commerce",
            city="Buenos Aires",
            country="Argentina",
            status="active",
            website="https://mercadolibre.com",
            created_at=datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc),
        ),
        Company(
            id=uuid.uuid4(),
            slug="rappi",
            name="Rappi",
            sector="Delivery",
            city="Bogotá",
            country="Colombia",
            status="active",
            website="https://rappi.com",
            created_at=datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc),
        ),
        Company(
            id=uuid.uuid4(),
            slug="inactive-startup",
            name="Inactive Startup",
            sector="Fintech",
            city="São Paulo",
            country="Brazil",
            status="inactive",
            website="https://example.com",
            created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for company in companies:
        db_session.add(company)
    db_session.commit()
    return companies


def test_list_companies_all(client, sample_companies):
    """Test listing all active companies (default status filter)."""
    response = client.get("/api/companies")

    assert response.status_code == 200
    data = response.json()
    # Should only return active companies by default
    assert len(data) == 3
    assert all(c["status"] == "active" for c in data)


def test_list_companies_all_statuses(client, sample_companies):
    """Test listing companies without status filter."""
    response = client.get("/api/companies?status=")

    assert response.status_code == 200
    data = response.json()
    # Should return all companies (active and inactive)
    assert len(data) == 4


def test_list_companies_filter_by_sector(client, sample_companies):
    """Test filtering companies by sector."""
    response = client.get("/api/companies?sector=Fintech")

    assert response.status_code == 200
    data = response.json()
    # Should only return active Fintech companies
    assert len(data) == 1
    assert data[0]["slug"] == "nubank"


def test_list_companies_filter_by_city(client, sample_companies):
    """Test filtering companies by city."""
    response = client.get("/api/companies?city=São Paulo")

    assert response.status_code == 200
    data = response.json()
    # Should only return active companies in São Paulo
    assert len(data) == 1
    assert data[0]["city"] == "São Paulo"


def test_list_companies_filter_by_country(client, sample_companies):
    """Test filtering companies by country."""
    response = client.get("/api/companies?country=Argentina")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "mercadolibre"


def test_list_companies_multiple_filters(client, sample_companies):
    """Test filtering by multiple parameters."""
    response = client.get("/api/companies?country=Brazil&sector=Fintech")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "nubank"


def test_list_companies_pagination(client, sample_companies):
    """Test company pagination."""
    response = client.get("/api/companies?limit=2&offset=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_companies_limit_validation(client, sample_companies):
    """Test limit validation."""
    # Too high
    response = client.get("/api/companies?limit=200")
    assert response.status_code == 422

    # Too low
    response = client.get("/api/companies?limit=0")
    assert response.status_code == 422


def test_get_company_by_slug_success(client, sample_companies):
    """Test getting company by slug."""
    response = client.get("/api/companies/nubank")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "nubank"
    assert data["name"] == "Nubank"
    assert data["sector"] == "Fintech"
    assert data["website"] == "https://nubank.com.br"


def test_get_company_by_slug_not_found(client, sample_companies):
    """Test getting non-existent company."""
    response = client.get("/api/companies/non-existent-company")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_companies_ordering(client, sample_companies):
    """Test that companies are ordered by created_at descending."""
    response = client.get("/api/companies")

    assert response.status_code == 200
    data = response.json()

    # Verify descending order (most recent first)
    # Last created should be first (inactive-startup is last but filtered out)
    assert data[0]["slug"] == "rappi"


def test_company_response_schema(client, sample_companies):
    """Test company response includes all required fields."""
    response = client.get("/api/companies")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    # Check first item has required fields
    company = data[0]
    required_fields = {
        "slug", "name", "sector", "city", "country", "status"
    }
    assert required_fields.issubset(set(company.keys()))


def test_list_companies_empty_result(client, db_session):
    """Test listing companies when none match filters."""
    response = client.get("/api/companies?sector=NonExistentSector")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_list_companies_status_filter_inactive(client, sample_companies):
    """Test filtering for inactive companies."""
    response = client.get("/api/companies?status=inactive")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "inactive"
    assert data[0]["slug"] == "inactive-startup"
