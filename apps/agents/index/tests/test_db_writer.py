"""Tests for INDEX db_writer — company upsert and external ID registration.

Uses SQLite in-memory for testing (following project convention).
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base
from packages.database.models.company import Company
from packages.database.models.company_external_id import CompanyExternalId
from apps.agents.index.pipeline import MergedCompany
from apps.agents.index.db_writer import (
    _register_external_ids,
    persist_index_results,
    upsert_company_from_index,
)


@pytest.fixture
def session():
    """Create an in-memory SQLite session with all tables."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _merged(**kwargs) -> MergedCompany:
    defaults = {
        "slug": "test-co",
        "name": "Test Co",
        "sources": ["test_source"],
        "source_count": 1,
        "best_confidence": 0.5,
        "is_new": True,
    }
    defaults.update(kwargs)
    return MergedCompany(**defaults)


class TestUpsertCompanyFromIndex:
    def test_inserts_new_company(self, session):
        merged = _merged(slug="nubank", name="Nubank", city="São Paulo", website="https://nubank.com.br")
        result = upsert_company_from_index(session, merged, score=0.8)

        assert result == "inserted"
        company = session.query(Company).filter_by(slug="nubank").first()
        assert company is not None
        assert company.name == "Nubank"
        assert company.city == "São Paulo"
        assert company.metadata_["confidence"] == 0.8

    def test_updates_when_higher_score(self, session):
        # Insert initial
        merged1 = _merged(slug="ifood", name="iFood", city="Campinas")
        upsert_company_from_index(session, merged1, score=0.5)

        # Update with higher score
        merged2 = _merged(slug="ifood", name="iFood", city="Campinas", website="https://ifood.com.br", source_count=2, sources=["s1", "s2"])
        result = upsert_company_from_index(session, merged2, score=0.8)

        assert result == "updated"
        company = session.query(Company).filter_by(slug="ifood").first()
        assert company.website == "https://ifood.com.br"
        assert company.metadata_["confidence"] == 0.8

    def test_skips_when_lower_score(self, session):
        # Insert with high score
        merged1 = _merged(slug="stone", name="Stone", website="https://stone.co")
        upsert_company_from_index(session, merged1, score=0.9)

        # Try update with lower score
        merged2 = _merged(slug="stone", name="Stone Pagamentos", website="https://other.com")
        result = upsert_company_from_index(session, merged2, score=0.3)

        assert result == "skipped"
        company = session.query(Company).filter_by(slug="stone").first()
        assert company.website == "https://stone.co"  # Unchanged

    def test_sets_cnpj_on_insert(self, session):
        merged = _merged(slug="nubank", name="Nubank", cnpj="18236120000158")
        upsert_company_from_index(session, merged, score=0.8)

        company = session.query(Company).filter_by(slug="nubank").first()
        assert company.cnpj == "18236120000158"

    def test_preserves_existing_fields(self, session):
        # Insert with description
        merged1 = _merged(slug="test", name="Test", description="Original description")
        upsert_company_from_index(session, merged1, score=0.5)

        # Update without description (should preserve original)
        merged2 = _merged(slug="test", name="Test", description=None, website="https://test.com")
        upsert_company_from_index(session, merged2, score=0.8)

        company = session.query(Company).filter_by(slug="test").first()
        assert company.description == "Original description"
        assert company.website == "https://test.com"

    def test_inserts_funding_fields(self, session):
        merged = _merged(
            slug="funded-co", name="FundedCo",
            funding_stage="series_a", total_funding_usd=10_000_000.0,
        )
        upsert_company_from_index(session, merged, score=0.7)
        company = session.query(Company).filter_by(slug="funded-co").first()
        assert company.funding_stage == "series_a"
        assert company.total_funding_usd == 10_000_000.0

    def test_updates_funding_fields_when_higher_score(self, session):
        merged1 = _merged(slug="co", name="Co", funding_stage="seed", total_funding_usd=1_000_000.0)
        upsert_company_from_index(session, merged1, score=0.5)

        merged2 = _merged(slug="co", name="Co", funding_stage="series_a", total_funding_usd=5_000_000.0)
        upsert_company_from_index(session, merged2, score=0.8)

        company = session.query(Company).filter_by(slug="co").first()
        assert company.funding_stage == "series_a"
        assert company.total_funding_usd == 5_000_000.0

    def test_funding_fields_none_does_not_overwrite(self, session):
        merged1 = _merged(slug="co2", name="Co2", funding_stage="series_b", total_funding_usd=20_000_000.0)
        upsert_company_from_index(session, merged1, score=0.5)

        merged2 = _merged(slug="co2", name="Co2", funding_stage=None, total_funding_usd=None)
        upsert_company_from_index(session, merged2, score=0.8)

        company = session.query(Company).filter_by(slug="co2").first()
        assert company.funding_stage == "series_b"
        assert company.total_funding_usd == 20_000_000.0

    def test_funding_stage_takes_highest_priority(self, session):
        merged1 = _merged(slug="co3", name="Co3", funding_stage="series_c")
        upsert_company_from_index(session, merged1, score=0.5)

        # Lower stage should not overwrite
        merged2 = _merged(slug="co3", name="Co3", funding_stage="seed")
        upsert_company_from_index(session, merged2, score=0.8)

        company = session.query(Company).filter_by(slug="co3").first()
        assert company.funding_stage == "series_c"


class TestRegisterExternalIds:
    def test_registers_cnpj(self, session):
        merged = _merged(cnpj="18236120000158")
        count = _register_external_ids(session, "nubank", merged)

        assert count >= 1
        ext = session.query(CompanyExternalId).filter_by(id_type="cnpj").first()
        assert ext is not None
        assert ext.id_value == "18236120000158"
        assert ext.company_slug == "nubank"

    def test_registers_domain(self, session):
        merged = _merged(website="https://nubank.com.br")
        count = _register_external_ids(session, "nubank", merged)

        assert count >= 1
        ext = session.query(CompanyExternalId).filter_by(id_type="domain").first()
        assert ext is not None
        assert ext.id_value == "nubank.com.br"

    def test_skips_duplicate(self, session):
        merged = _merged(cnpj="18236120000158")
        _register_external_ids(session, "nubank", merged)
        count2 = _register_external_ids(session, "nubank", merged)

        assert count2 == 0  # No new IDs registered

    def test_registers_multiple_id_types(self, session):
        merged = _merged(
            cnpj="18236120000158",
            website="https://nubank.com.br",
            crunchbase_permalink="nubank",
            github_login="nubank",
        )
        count = _register_external_ids(session, "nubank", merged)
        assert count == 4


class TestPersistIndexResults:
    def test_batch_insert(self, session):
        companies = [
            (_merged(slug="co-1", name="Company 1"), 0.7),
            (_merged(slug="co-2", name="Company 2"), 0.8),
            (_merged(slug="co-3", name="Company 3"), 0.6),
        ]
        stats = persist_index_results(session, companies)

        assert stats["inserted"] == 3
        assert session.query(Company).count() == 3

    def test_mixed_insert_and_update(self, session):
        # Pre-insert one company with low score
        merged0 = _merged(slug="existing", name="Existing Co")
        upsert_company_from_index(session, merged0, score=0.3)

        companies = [
            (_merged(slug="existing", name="Existing Co Updated", website="https://existing.co"), 0.8),
            (_merged(slug="new-co", name="New Company"), 0.7),
        ]
        stats = persist_index_results(session, companies)

        assert stats["inserted"] == 1
        assert stats["updated"] == 1

    def test_empty_list(self, session):
        stats = persist_index_results(session, [])
        assert stats["inserted"] == 0
        assert stats["updated"] == 0
        assert stats["skipped"] == 0
