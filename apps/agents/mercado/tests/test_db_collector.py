"""Tests for MERCADO database source collector.

Uses an in-memory SQLite database (same pattern as test_persistence.py).
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.github_orgs import CompanyProfile
from packages.database.models.base import Base
from packages.database.models.company import Company

from apps.agents.mercado.db_collector import (
    _company_to_profile,
    collect_from_database,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Provide a transactional database session for tests."""
    factory = sessionmaker(bind=engine)
    sess = factory()
    yield sess
    sess.rollback()
    sess.close()


def _make_company(
    name: str = "Nubank",
    slug: str = "nubank",
    status: str = "active",
    **kwargs,
) -> Company:
    """Build a Company record with sensible defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "name": name,
        "slug": slug,
        "status": status,
        "country": "Brazil",
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    return Company(**defaults)


# ---------------------------------------------------------------------------
# TestCompanyToProfile
# ---------------------------------------------------------------------------


class TestCompanyToProfile:
    """Tests for _company_to_profile()."""

    def test_maps_basic_fields(self, session: Session):
        company = _make_company(
            name="Nubank",
            slug="nubank",
            website="https://nubank.com.br",
            sector="Fintech",
            city="São Paulo",
        )
        session.add(company)
        session.flush()

        profile = _company_to_profile(company)

        assert profile.name == "Nubank"
        assert profile.slug == "nubank"
        assert profile.website == "https://nubank.com.br"
        assert profile.sector == "Fintech"
        assert profile.city == "São Paulo"

    def test_maps_all_company_fields(self, session: Session):
        company = _make_company(
            name="Stone",
            slug="stone",
            website="https://stone.com.br",
            description="Payment solutions",
            short_description="Fintech for payments",
            sector="Fintech",
            city="Rio de Janeiro",
            country="Brazil",
            founded_date=date(2012, 1, 1),
            team_size=5000,
            linkedin_url="https://linkedin.com/company/stone",
            github_url="https://github.com/stone-co",
            tech_stack=["Go", "Kotlin", "React"],
            tags=["fintech", "payments", "pos"],
        )
        session.add(company)
        session.flush()

        profile = _company_to_profile(company)

        assert profile.name == "Stone"
        assert profile.slug == "stone"
        assert profile.website == "https://stone.com.br"
        assert profile.description == "Fintech for payments"  # uses short_description
        assert profile.sector == "Fintech"
        assert profile.city == "Rio de Janeiro"
        assert profile.country == "Brazil"
        assert profile.founded_date == date(2012, 1, 1)
        assert profile.team_size == 5000
        assert profile.linkedin_url == "https://linkedin.com/company/stone"
        assert profile.github_url == "https://github.com/stone-co"
        assert profile.tech_stack == ["Go", "Kotlin", "React"]
        assert profile.tags == ["fintech", "payments", "pos"]
        assert profile.source_name == "companies_db"

    def test_uses_description_when_short_is_none(self, session: Session):
        company = _make_company(
            description="A long description about the company",
            short_description=None,
        )
        session.add(company)
        session.flush()

        profile = _company_to_profile(company)
        assert profile.description == "A long description about the company"

    def test_returns_company_profile_type(self, session: Session):
        company = _make_company()
        session.add(company)
        session.flush()

        profile = _company_to_profile(company)
        assert isinstance(profile, CompanyProfile)


# ---------------------------------------------------------------------------
# TestCollectFromDatabase
# ---------------------------------------------------------------------------


class TestCollectFromDatabase:
    """Tests for collect_from_database()."""

    def test_returns_active_companies(self, session: Session):
        session.add(_make_company(name="Active Corp", slug="active-corp", status="active"))
        session.add(_make_company(name="Inactive Corp", slug="inactive-corp", status="inactive"))
        session.commit()

        provenance = ProvenanceTracker()
        profiles = collect_from_database(session, provenance)

        assert len(profiles) == 1
        assert profiles[0].name == "Active Corp"

    def test_respects_limit(self, session: Session):
        for i in range(10):
            session.add(_make_company(
                name=f"Company {i}",
                slug=f"company-{i}",
                updated_at=datetime(2026, 3, 1, i, tzinfo=timezone.utc),
            ))
        session.commit()

        provenance = ProvenanceTracker()
        profiles = collect_from_database(session, provenance, limit=3)

        assert len(profiles) == 3

    def test_orders_by_updated_at_desc(self, session: Session):
        session.add(_make_company(
            name="Old",
            slug="old",
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ))
        session.add(_make_company(
            name="New",
            slug="new",
            updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        ))
        session.commit()

        provenance = ProvenanceTracker()
        profiles = collect_from_database(session, provenance)

        assert profiles[0].name == "New"
        assert profiles[1].name == "Old"

    def test_tracks_provenance(self, session: Session):
        session.add(_make_company(name="Test", slug="test"))
        session.commit()

        provenance = ProvenanceTracker()
        collect_from_database(session, provenance)

        sources = provenance.get_sources()
        assert "companies_db" in sources

    def test_handles_empty_table(self, session: Session):
        provenance = ProvenanceTracker()
        profiles = collect_from_database(session, provenance)

        assert profiles == []

    def test_handles_null_metadata(self, session: Session):
        session.add(_make_company(
            name="Sparse",
            slug="sparse",
            tech_stack=None,
            tags=None,
        ))
        session.commit()

        provenance = ProvenanceTracker()
        profiles = collect_from_database(session, provenance)

        assert len(profiles) == 1
        assert profiles[0].tech_stack == []
        assert profiles[0].tags == []

    def test_country_filter(self, session: Session):
        session.add(_make_company(name="BR Corp", slug="br", country="Brazil"))
        session.add(_make_company(name="MX Corp", slug="mx", country="Mexico"))
        session.commit()

        provenance = ProvenanceTracker()
        profiles = collect_from_database(session, provenance, country="Brazil")

        assert len(profiles) == 1
        assert profiles[0].name == "BR Corp"

    def test_source_name_is_companies_db(self, session: Session):
        session.add(_make_company())
        session.commit()

        provenance = ProvenanceTracker()
        profiles = collect_from_database(session, provenance)

        assert profiles[0].source_name == "companies_db"
