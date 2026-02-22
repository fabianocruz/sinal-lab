"""Tests for database models — validates schema, defaults, and constraints.

These tests use an in-memory SQLite database to verify model structure
without requiring a running PostgreSQL instance.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

# Use a simpler import path since we add project root to sys.path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from packages.database.models.base import Base
from packages.database.models.company import Company
from packages.database.models.content_piece import ContentPiece
from packages.database.models.agent_run import AgentRun
from packages.database.models.data_provenance import DataProvenance
from packages.database.models.investor import Investor
from packages.database.models.funding_round import FundingRound
from packages.database.models.ecosystem import Ecosystem
from packages.database.models.user import User


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Provide a transactional database session for tests."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.rollback()
    session.close()


class TestBase:
    """Test that all expected tables are created."""

    def test_all_tables_created(self, engine):
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "companies" in table_names
        assert "content_pieces" in table_names
        assert "agent_runs" in table_names
        assert "data_provenance" in table_names
        assert "investors" in table_names
        assert "funding_rounds" in table_names
        assert "ecosystems" in table_names
        assert "users" in table_names
        assert "evidence_items" in table_names
        assert "company_external_ids" in table_names

    def test_table_count(self, engine):
        inspector = inspect(engine)
        assert len(inspector.get_table_names()) == 13


class TestCompany:
    """Test Company model creation and defaults."""

    def test_create_company_minimal(self, session: Session):
        company = Company(
            id=uuid.uuid4(),
            name="Nubank",
            slug="nubank",
        )
        session.add(company)
        session.flush()

        assert company.name == "Nubank"
        assert company.slug == "nubank"
        assert company.country == "Brazil"
        assert company.status == "active"

    def test_create_company_full(self, session: Session):
        company = Company(
            id=uuid.uuid4(),
            name="Creditas",
            slug="creditas",
            description="Plataforma de credito com garantia",
            short_description="Fintech de credito",
            sector="fintech",
            sub_sector="lending",
            city="Sao Paulo",
            state="SP",
            country="Brazil",
            founded_date=date(2012, 1, 1),
            team_size=4000,
            business_model="B2C",
            website="https://creditas.com.br",
            github_url="https://github.com/creditas",
            status="active",
        )
        session.add(company)
        session.flush()

        assert company.sector == "fintech"
        assert company.team_size == 4000
        assert company.founded_date == date(2012, 1, 1)

    def test_company_slug_unique(self, session: Session):
        c1 = Company(id=uuid.uuid4(), name="A", slug="same-slug")
        c2 = Company(id=uuid.uuid4(), name="B", slug="same-slug")
        session.add(c1)
        session.flush()
        session.add(c2)
        with pytest.raises(Exception):
            session.flush()

    def test_company_repr(self, session: Session):
        company = Company(id=uuid.uuid4(), name="Test", slug="test", sector="ai")
        assert "Test" in repr(company)
        assert "test" in repr(company)


class TestContentPiece:
    """Test ContentPiece model creation and defaults."""

    def test_create_content_piece_minimal(self, session: Session):
        piece = ContentPiece(
            id=uuid.uuid4(),
            title="Sinal Semanal #1",
            slug="sinal-semanal-1",
            body_md="# Hello world",
            content_type="DATA_REPORT",
        )
        session.add(piece)
        session.flush()

        assert piece.review_status == "draft"
        assert piece.confidence_dq is None
        assert piece.published_at is None

    def test_create_content_with_confidence(self, session: Session):
        piece = ContentPiece(
            id=uuid.uuid4(),
            title="RADAR Report W7",
            slug="radar-report-w7",
            body_md="# Trends this week",
            content_type="ANALYSIS",
            agent_name="radar",
            confidence_dq=4.0,
            confidence_ac=3.5,
            review_status="approved",
        )
        session.add(piece)
        session.flush()

        assert piece.confidence_dq == 4.0
        assert piece.confidence_ac == 3.5
        assert piece.agent_name == "radar"

    def test_create_content_with_author_name(self, session: Session):
        piece = ContentPiece(
            id=uuid.uuid4(),
            title="Artigo com Autor",
            slug="artigo-com-autor",
            body_md="# Conteudo",
            content_type="ARTICLE",
            author_name="Fabiano Cruz",
        )
        session.add(piece)
        session.flush()

        assert piece.author_name == "Fabiano Cruz"

    def test_create_content_author_name_defaults_to_none(self, session: Session):
        piece = ContentPiece(
            id=uuid.uuid4(),
            title="Artigo Sem Autor",
            slug="artigo-sem-autor",
            body_md="# Conteudo",
            content_type="ARTICLE",
        )
        session.add(piece)
        session.flush()

        assert piece.author_name is None

    def test_content_slug_unique(self, session: Session):
        c1 = ContentPiece(
            id=uuid.uuid4(),
            title="A",
            slug="same",
            body_md="x",
            content_type="NEWS",
        )
        c2 = ContentPiece(
            id=uuid.uuid4(),
            title="B",
            slug="same",
            body_md="y",
            content_type="NEWS",
        )
        session.add(c1)
        session.flush()
        session.add(c2)
        with pytest.raises(Exception):
            session.flush()


class TestAgentRun:
    """Test AgentRun model creation and defaults."""

    def test_create_agent_run(self, session: Session):
        now = datetime.now(timezone.utc)
        run = AgentRun(
            id=uuid.uuid4(),
            agent_name="sintese",
            run_id="sintese-2026-02-16-001",
            started_at=now,
            status="running",
        )
        session.add(run)
        session.flush()

        assert run.agent_name == "sintese"
        assert run.error_count == 0
        assert run.completed_at is None

    def test_create_completed_run(self, session: Session):
        now = datetime.now(timezone.utc)
        run = AgentRun(
            id=uuid.uuid4(),
            agent_name="radar",
            run_id="radar-2026-02-16-001",
            started_at=now,
            completed_at=now,
            status="completed",
            items_collected=500,
            items_processed=480,
            items_output=10,
            avg_confidence=0.75,
        )
        session.add(run)
        session.flush()

        assert run.items_collected == 500
        assert run.avg_confidence == 0.75

    def test_run_id_unique(self, session: Session):
        now = datetime.now(timezone.utc)
        r1 = AgentRun(
            id=uuid.uuid4(),
            agent_name="a",
            run_id="same-run",
            started_at=now,
        )
        r2 = AgentRun(
            id=uuid.uuid4(),
            agent_name="b",
            run_id="same-run",
            started_at=now,
        )
        session.add(r1)
        session.flush()
        session.add(r2)
        with pytest.raises(Exception):
            session.flush()


class TestDataProvenance:
    """Test DataProvenance model creation and defaults."""

    def test_create_provenance(self, session: Session):
        now = datetime.now(timezone.utc)
        prov = DataProvenance(
            id=uuid.uuid4(),
            record_type="company",
            record_id="some-uuid",
            source_url="https://crunchbase.com/org/nubank",
            source_name="crunchbase",
            collected_at=now,
            extraction_method="api",
            confidence=0.9,
            quality_grade="A",
        )
        session.add(prov)
        session.flush()

        assert prov.confidence == 0.9
        assert prov.quality_grade == "A"
        assert prov.verified is False

    def test_create_unverified_provenance(self, session: Session):
        now = datetime.now(timezone.utc)
        prov = DataProvenance(
            id=uuid.uuid4(),
            record_type="content_piece",
            record_id="another-uuid",
            collected_at=now,
            extraction_method="rss",
            confidence=0.4,
            quality_grade="C",
        )
        session.add(prov)
        session.flush()

        assert prov.verified is False
        assert prov.source_url is None

    def test_provenance_with_verification(self, session: Session):
        now = datetime.now(timezone.utc)
        prov = DataProvenance(
            id=uuid.uuid4(),
            record_type="company",
            record_id="uuid-123",
            collected_at=now,
            extraction_method="manual",
            confidence=0.95,
            quality_grade="A",
            verified=True,
            verified_by="editor@sinal.ai",
            verified_at=now,
        )
        session.add(prov)
        session.flush()

        assert prov.verified is True
        assert prov.verified_by == "editor@sinal.ai"


class TestInvestor:
    """Test Investor model creation and defaults."""

    def test_create_investor_minimal(self, session: Session):
        investor = Investor(
            id=uuid.uuid4(),
            name="Kaszek Ventures",
            slug="kaszek-ventures",
        )
        session.add(investor)
        session.flush()

        assert investor.name == "Kaszek Ventures"
        assert investor.investor_type == "vc"
        assert investor.status == "active"
        assert investor.aum_usd is None

    def test_create_investor_full(self, session: Session):
        investor = Investor(
            id=uuid.uuid4(),
            name="SoftBank Latin America Fund",
            slug="softbank-latam",
            description="SoftBank's dedicated LATAM investment arm",
            investor_type="vc",
            aum_usd=5_000_000_000.0,
            portfolio_count=80,
            city="Miami",
            country="United States",
            thesis="Growth-stage LATAM tech companies",
            focus_sectors=["fintech", "e-commerce", "logistics"],
            focus_stages=["series_b", "series_c", "series_d"],
            focus_regions=["Brazil", "Mexico", "Colombia"],
            website="https://softbank.com",
            status="active",
        )
        session.add(investor)
        session.flush()

        assert investor.aum_usd == 5_000_000_000.0
        assert investor.portfolio_count == 80
        assert investor.focus_sectors == ["fintech", "e-commerce", "logistics"]

    def test_investor_slug_unique(self, session: Session):
        i1 = Investor(id=uuid.uuid4(), name="A", slug="same-slug")
        i2 = Investor(id=uuid.uuid4(), name="B", slug="same-slug")
        session.add(i1)
        session.flush()
        session.add(i2)
        with pytest.raises(Exception):
            session.flush()

    def test_investor_repr(self, session: Session):
        investor = Investor(
            id=uuid.uuid4(), name="Kaszek", slug="kaszek", investor_type="vc"
        )
        assert "Kaszek" in repr(investor)
        assert "vc" in repr(investor)


class TestFundingRound:
    """Test FundingRound model creation and defaults."""

    def test_create_funding_round_minimal(self, session: Session):
        fr = FundingRound(
            id=uuid.uuid4(),
            company_slug="nubank",
            company_name="Nubank",
            round_type="series_a",
        )
        session.add(fr)
        session.flush()

        assert fr.company_slug == "nubank"
        assert fr.round_type == "series_a"
        assert fr.currency == "USD"
        assert fr.confidence == 0.5
        assert fr.amount_usd is None

    def test_create_funding_round_full(self, session: Session):
        fr = FundingRound(
            id=uuid.uuid4(),
            company_slug="creditas",
            company_name="Creditas",
            round_type="series_b",
            amount_usd=200_000_000.0,
            currency="USD",
            valuation_usd=1_750_000_000.0,
            announced_date=date(2026, 1, 15),
            lead_investors=["softbank-latam"],
            participants=["kaszek-ventures", "qed-investors"],
            source_url="https://techcrunch.com/creditas-series-b",
            source_name="techcrunch",
            confidence=0.9,
            notes="Largest fintech round in Brazil Q1 2026",
        )
        session.add(fr)
        session.flush()

        assert fr.amount_usd == 200_000_000.0
        assert fr.valuation_usd == 1_750_000_000.0
        assert fr.lead_investors == ["softbank-latam"]
        assert len(fr.participants) == 2

    def test_funding_round_repr(self, session: Session):
        fr = FundingRound(
            id=uuid.uuid4(),
            company_slug="vtex",
            company_name="VTEX",
            round_type="series_c",
            amount_usd=100_000_000.0,
        )
        r = repr(fr)
        assert "VTEX" in r
        assert "series_c" in r


class TestEcosystem:
    """Test Ecosystem model creation and defaults."""

    def test_create_ecosystem_minimal(self, session: Session):
        eco = Ecosystem(
            id=uuid.uuid4(),
            name="Sao Paulo Tech",
            slug="sao-paulo-tech",
            country="Brazil",
        )
        session.add(eco)
        session.flush()

        assert eco.name == "Sao Paulo Tech"
        assert eco.country == "Brazil"
        assert eco.status == "active"
        assert eco.total_startups is None

    def test_create_ecosystem_full(self, session: Session):
        eco = Ecosystem(
            id=uuid.uuid4(),
            name="Florianopolis Tech",
            slug="florianopolis-tech",
            description="Silicon Valley of Brazil — strong SaaS and enterprise software cluster",
            country="Brazil",
            city="Florianopolis",
            region="Sul",
            total_startups=350,
            total_funding_usd=2_500_000_000.0,
            active_investors=45,
            total_exits=12,
            top_sectors=["saas", "enterprise", "fintech"],
            notable_companies=["resultados-digitais", "conta-azul"],
            ranking_score=7.8,
        )
        session.add(eco)
        session.flush()

        assert eco.total_startups == 350
        assert eco.ranking_score == 7.8
        assert eco.top_sectors == ["saas", "enterprise", "fintech"]

    def test_ecosystem_slug_unique(self, session: Session):
        e1 = Ecosystem(id=uuid.uuid4(), name="A", slug="same", country="Brazil")
        e2 = Ecosystem(id=uuid.uuid4(), name="B", slug="same", country="Mexico")
        session.add(e1)
        session.flush()
        session.add(e2)
        with pytest.raises(Exception):
            session.flush()

    def test_ecosystem_repr(self, session: Session):
        eco = Ecosystem(
            id=uuid.uuid4(), name="CDMX", slug="cdmx", country="Mexico"
        )
        assert "CDMX" in repr(eco)
        assert "Mexico" in repr(eco)


class TestUser:
    """Test User model creation and defaults."""

    def test_create_user_minimal(self, session: Session):
        user = User(
            id=uuid.uuid4(),
            email="founder@startup.com",
        )
        session.add(user)
        session.flush()

        assert user.email == "founder@startup.com"
        assert user.is_founding_member is False
        assert user.status == "waitlist"
        assert user.name is None
        assert user.onboarded_at is None

    def test_create_user_full(self, session: Session):
        now = datetime.now(timezone.utc)
        user = User(
            id=uuid.uuid4(),
            email="cto@bigtech.com",
            name="Maria Silva",
            role="cto",
            company="BigTech Brasil",
            title="Chief Technology Officer",
            waitlist_position=42,
            is_founding_member=True,
            onboarded_at=now,
            preferences={"newsletter_frequency": "weekly", "topics": ["ai", "fintech"]},
            status="active",
        )
        session.add(user)
        session.flush()

        assert user.name == "Maria Silva"
        assert user.role == "cto"
        assert user.is_founding_member is True
        assert user.waitlist_position == 42
        assert user.preferences["topics"] == ["ai", "fintech"]

    def test_user_email_unique(self, session: Session):
        u1 = User(id=uuid.uuid4(), email="same@email.com")
        u2 = User(id=uuid.uuid4(), email="same@email.com")
        session.add(u1)
        session.flush()
        session.add(u2)
        with pytest.raises(Exception):
            session.flush()

    def test_user_repr(self, session: Session):
        user = User(
            id=uuid.uuid4(), email="test@x.com", role="founder", status="waitlist"
        )
        assert "test@x.com" in repr(user)
        assert "waitlist" in repr(user)
