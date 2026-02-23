"""Tests for companies router.

Uses SQLite in-memory with StaticPool so all threads share the same
database connection. This is required because FastAPI runs sync endpoints
in a worker thread pool — without StaticPool, each thread would get a
separate in-memory database and see "no such table" errors.

Run: pytest apps/api/tests/test_companies.py -v
"""

import json
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_db
from apps.api.main import app
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
            description="Digital bank for Latin America",
            short_description="Leading digital bank in Brazil",
            sector="Fintech",
            sub_sector="Digital Banking",
            city="São Paulo",
            state="SP",
            country="Brazil",
            tags=["fintech", "banking", "unicorn"],
            tech_stack=["Python", "Clojure", "Kafka"],
            founded_date=date(2013, 5, 6),
            team_size=8000,
            business_model="B2C",
            website="https://nubank.com.br",
            github_url="https://github.com/nubank",
            linkedin_url="https://linkedin.com/company/nubank",
            source_count=5,
            status="active",
            created_at=datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
        ),
        Company(
            id=uuid.uuid4(),
            slug="mercadolibre",
            name="MercadoLibre",
            description="E-commerce and fintech platform",
            short_description="Largest e-commerce platform in LATAM",
            sector="E-commerce",
            city="Buenos Aires",
            country="Argentina",
            tags=["e-commerce", "marketplace", "fintech"],
            source_count=3,
            status="active",
            website="https://mercadolibre.com",
            created_at=datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc),
        ),
        Company(
            id=uuid.uuid4(),
            slug="rappi",
            name="Rappi",
            description="On-demand delivery super app",
            sector="Delivery",
            city="Bogotá",
            country="Colombia",
            tags=["delivery", "super-app"],
            source_count=2,
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
            tags=["fintech"],
            source_count=1,
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


# ---------------------------------------------------------------------------
# Paginated envelope structure
# ---------------------------------------------------------------------------


def test_list_companies_returns_paginated_envelope(client, sample_companies):
    """Test that listing companies returns paginated envelope with items, total, limit, offset."""
    response = client.get("/api/companies")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 3  # only active companies
    assert len(data["items"]) == 3


def test_list_companies_all_statuses(client, sample_companies):
    """Test listing companies without status filter."""
    response = client.get("/api/companies?status=")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_list_companies_filter_by_sector(client, sample_companies):
    """Test filtering companies by sector."""
    response = client.get("/api/companies?sector=Fintech")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "nubank"


def test_list_companies_filter_by_city(client, sample_companies):
    """Test filtering companies by city."""
    response = client.get("/api/companies?city=São Paulo")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["city"] == "São Paulo"


def test_list_companies_filter_by_country(client, sample_companies):
    """Test filtering companies by country."""
    response = client.get("/api/companies?country=Argentina")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "mercadolibre"


def test_list_companies_multiple_filters(client, sample_companies):
    """Test filtering by multiple parameters."""
    response = client.get("/api/companies?country=Brazil&sector=Fintech")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "nubank"


def test_list_companies_status_filter_inactive(client, sample_companies):
    """Test filtering for inactive companies."""
    response = client.get("/api/companies?status=inactive")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "inactive"
    assert data["items"][0]["slug"] == "inactive-startup"


# ---------------------------------------------------------------------------
# Search filter
# ---------------------------------------------------------------------------


def test_list_companies_search_by_name(client, sample_companies):
    """Test searching companies by name (case-insensitive)."""
    response = client.get("/api/companies?search=nubank")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "nubank"


def test_list_companies_search_case_insensitive(client, sample_companies):
    """Test that search is case-insensitive."""
    response = client.get("/api/companies?search=RAPPI")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "rappi"


def test_list_companies_search_partial_match(client, sample_companies):
    """Test that search supports partial matching."""
    response = client.get("/api/companies?search=Mercado")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "mercadolibre"


def test_list_companies_search_no_results(client, sample_companies):
    """Test search with no matching results."""
    response = client.get("/api/companies?search=NonExistentCompany")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


def test_list_companies_pagination(client, sample_companies):
    """Test company pagination with paginated envelope."""
    response = client.get("/api/companies?limit=2&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Second page
    response2 = client.get("/api/companies?limit=2&offset=2")
    data2 = response2.json()
    assert len(data2["items"]) == 1


def test_list_companies_limit_validation(client, sample_companies):
    """Test limit validation."""
    # Too high
    response = client.get("/api/companies?limit=200")
    assert response.status_code == 422

    # Too low
    response = client.get("/api/companies?limit=0")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_companies_ordering(client, sample_companies):
    """Test that companies are ordered by created_at descending."""
    response = client.get("/api/companies")

    assert response.status_code == 200
    data = response.json()
    items = data["items"]
    # Most recently created active company (rappi, Feb 12) should be first
    assert items[0]["slug"] == "rappi"


# ---------------------------------------------------------------------------
# Detail endpoint
# ---------------------------------------------------------------------------


def test_get_company_by_slug_success(client, sample_companies):
    """Test getting company by slug returns full detail."""
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


# ---------------------------------------------------------------------------
# Expanded response schema
# ---------------------------------------------------------------------------


def test_company_response_includes_expanded_fields(client, sample_companies):
    """Test company response includes all expanded fields from the model."""
    response = client.get("/api/companies")

    assert response.status_code == 200
    data = response.json()
    company = data["items"][0]

    expanded_fields = {
        "slug",
        "name",
        "description",
        "short_description",
        "sector",
        "sub_sector",
        "city",
        "state",
        "country",
        "tags",
        "tech_stack",
        "founded_date",
        "team_size",
        "business_model",
        "website",
        "github_url",
        "linkedin_url",
        "twitter_url",
        "source_count",
        "status",
        "created_at",
    }
    assert expanded_fields.issubset(set(company.keys()))


def test_company_detail_includes_nubank_data(client, sample_companies):
    """Test that detail endpoint returns rich data for a well-populated company."""
    response = client.get("/api/companies/nubank")

    assert response.status_code == 200
    data = response.json()
    assert data["short_description"] == "Leading digital bank in Brazil"
    assert data["sub_sector"] == "Digital Banking"
    assert data["state"] == "SP"
    assert data["tags"] == ["fintech", "banking", "unicorn"]
    assert data["tech_stack"] == ["Python", "Clojure", "Kafka"]
    assert data["founded_date"] == "2013-05-06"
    assert data["team_size"] == 8000
    assert data["business_model"] == "B2C"
    assert data["github_url"] == "https://github.com/nubank"
    assert data["linkedin_url"] == "https://linkedin.com/company/nubank"
    assert data["source_count"] == 5


def test_company_detail_handles_sparse_data(client, sample_companies):
    """Test that detail endpoint handles companies with minimal data gracefully."""
    response = client.get("/api/companies/rappi")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Rappi"
    # These fields should be null when not set
    assert data["short_description"] is None
    assert data["sub_sector"] is None
    assert data["tech_stack"] is None
    assert data["founded_date"] is None
    assert data["team_size"] is None


# ---------------------------------------------------------------------------
# Empty results
# ---------------------------------------------------------------------------


def test_list_companies_empty_result(client, db_session):
    """Test listing companies when none match filters."""
    response = client.get("/api/companies?sector=NonExistentSector")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0
