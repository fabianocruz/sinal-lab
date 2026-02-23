"""Tests for scripts/enrich_companies.py — startup classification and enrichment.

Validates classify_startup(), classify_sector(), generate_tags(),
fetch_companies(), and update_company() using SQLite in-memory
(same pattern as other script tests in this package).

Run: pytest scripts/tests/test_enrich_companies.py -v
"""

import json
import uuid
from typing import Any, List, Optional

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base

from scripts.enrich_companies import (
    NON_STARTUP_SLUGS,
    classify_sector,
    classify_startup,
    fetch_companies,
    generate_tags,
    update_company,
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
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def session(engine) -> Session:
    """Provide a database session for each test."""
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def _insert_company(
    session: Session,
    slug: str,
    name: str = "Acme Corp",
    description: str = "",
    website: str = "",
    sector: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: str = "active",
) -> None:
    """Insert a minimal company row via raw SQL (mirrors the companies table schema)."""
    session.execute(
        text(
            "INSERT INTO companies "
            "(id, name, slug, description, website, sector, tags, status, "
            " country, source_count, created_at, updated_at) "
            "VALUES "
            "(:id, :name, :slug, :desc, :website, :sector, :tags, :status, "
            " :country, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "slug": slug,
            "desc": description,
            "website": website,
            "sector": sector,
            "tags": json.dumps(tags) if tags is not None else None,
            "status": status,
            "country": "Brazil",
        },
    )
    session.commit()


# ---------------------------------------------------------------------------
# classify_startup() — happy path (real startup)
# ---------------------------------------------------------------------------


def test_enrich_companies_classify_startup_returns_true_for_normal_company() -> None:
    """A plain company name and description is classified as a startup."""
    is_startup, reason = classify_startup(
        name="Nubank",
        description="Digital bank for consumers in Latin America",
        slug="nubank",
        website="https://nubank.com.br",
    )
    assert is_startup is True
    assert reason == "startup"


def test_enrich_companies_classify_startup_returns_true_for_saas_company() -> None:
    """A SaaS company with a tech description is classified as a startup."""
    is_startup, reason = classify_startup(
        name="Pipefy",
        description="Cloud-based workflow management platform for teams",
        slug="pipefy",
        website="https://pipefy.com",
    )
    assert is_startup is True
    assert reason == "startup"


def test_enrich_companies_classify_startup_returns_true_for_empty_description() -> None:
    """A company with no description still classifies as startup when name is clean."""
    is_startup, reason = classify_startup(
        name="SomeStartup",
        description="",
        slug="some-startup",
        website="",
    )
    assert is_startup is True
    assert reason == "startup"


# ---------------------------------------------------------------------------
# classify_startup() — slug blocklist
# ---------------------------------------------------------------------------


def test_enrich_companies_classify_startup_returns_false_for_blocklisted_slug() -> None:
    """A slug in NON_STARTUP_SLUGS is immediately rejected regardless of description."""
    is_startup, reason = classify_startup(
        name="Gobierno de Buenos Aires",
        description="Government technology initiatives",
        slug="gcba",
        website="https://gcba.gob.ar",
    )
    assert is_startup is False
    assert reason == "slug_blocklist"


def test_enrich_companies_classify_startup_blocklist_ignores_description() -> None:
    """Blocklist match takes priority over any startup-looking description."""
    is_startup, reason = classify_startup(
        name="Normal Company Name",
        description="SaaS platform for enterprise payments fintech cloud",
        slug="thedatapub",
        website="",
    )
    assert is_startup is False
    assert reason == "slug_blocklist"


def test_enrich_companies_classify_startup_all_blocklist_slugs_rejected() -> None:
    """Every slug in NON_STARTUP_SLUGS is rejected with 'slug_blocklist'."""
    for slug in NON_STARTUP_SLUGS:
        is_startup, reason = classify_startup(
            name="Anything", description="", slug=slug, website=""
        )
        assert is_startup is False, f"Expected {slug!r} to be blocked"
        assert reason == "slug_blocklist"


# ---------------------------------------------------------------------------
# classify_startup() — university / academic patterns
# ---------------------------------------------------------------------------


def test_enrich_companies_classify_startup_returns_false_for_university_name() -> None:
    """A name containing 'Universidade' is classified as university."""
    is_startup, reason = classify_startup(
        name="Universidade de São Paulo",
        description="Public research university",
        slug="usp-research",
        website="https://usp.br",
    )
    assert is_startup is False
    assert reason == "university"


def test_enrich_companies_classify_startup_returns_false_for_universidad() -> None:
    """Spanish 'Universidad' is also caught by the university pattern."""
    is_startup, reason = classify_startup(
        name="Universidad Nacional de Colombia",
        description="",
        slug="unal",
        website="",
    )
    assert is_startup is False
    assert reason == "university"


def test_enrich_companies_classify_startup_returns_false_for_utn_slug_in_name() -> None:
    """UTN abbreviation in the name triggers university detection."""
    is_startup, reason = classify_startup(
        name="Diseño de Sistemas UTN FRBA",
        description="Software design course",
        slug="dds-utn-custom",
        website="",
    )
    assert is_startup is False
    assert reason == "university"


def test_enrich_companies_classify_startup_returns_false_for_academic_course() -> None:
    """A course name like 'Programación con Objetos' (with accent) is classified as academic_course.

    The pattern requires 'programación con' (with accent mark) — the accent must be
    present in the input for the match to fire.
    """
    is_startup, reason = classify_startup(
        name="Programación con Objetos II",
        description="",
        slug="obj2-custom",
        website="",
    )
    assert is_startup is False
    assert reason == "academic_course"


def test_enrich_companies_classify_startup_returns_false_for_catedra() -> None:
    """Spanish 'cátedra' in description triggers academic_course classification."""
    is_startup, reason = classify_startup(
        name="Algoritmos y Estructuras de Datos",
        description="cátedra oficial de algoritmos",
        slug="algo-ed",
        website="",
    )
    assert is_startup is False
    assert reason == "academic_course"


def test_enrich_companies_classify_startup_returns_false_for_research_lab() -> None:
    """'Laboratorio de Sistemas' is classified as research_lab."""
    is_startup, reason = classify_startup(
        name="Laboratorio de Sistemas Embebidos",
        description="Research on embedded systems",
        slug="lse-custom",
        website="",
    )
    assert is_startup is False
    assert reason == "research_lab"


def test_enrich_companies_classify_startup_returns_false_for_lab_abbreviation() -> None:
    """A standalone 'lab' word in the name triggers research_lab detection.

    Description must NOT contain a university pattern (university fires first
    in the pattern list and would override research_lab).
    """
    is_startup, reason = classify_startup(
        name="AI Research Lab",
        description="Computational systems research group",
        slug="ai-research-lab",
        website="",
    )
    assert is_startup is False
    assert reason == "research_lab"


def test_enrich_companies_classify_startup_returns_false_for_academic_project() -> None:
    """'ejercicios y apuntes' signals an academic project, not a startup."""
    is_startup, reason = classify_startup(
        name="Ejercicios y Apuntes de Python",
        description="Course exercises repository",
        slug="python-apuntes",
        website="",
    )
    assert is_startup is False
    assert reason == "academic_project"


# ---------------------------------------------------------------------------
# classify_startup() — government entities
# ---------------------------------------------------------------------------


def test_enrich_companies_classify_startup_returns_false_for_gobierno() -> None:
    """'Gobierno de Buenos Aires' in description is classified as government."""
    is_startup, reason = classify_startup(
        name="Dirección de Sistemas",
        description="Gobierno de Buenos Aires digital transformation",
        slug="dir-sistemas",
        website="",
    )
    assert is_startup is False
    assert reason == "government"


def test_enrich_companies_classify_startup_returns_false_for_secretaria() -> None:
    """'Secretaria' in a Brazilian gov entity name triggers government."""
    is_startup, reason = classify_startup(
        name="Secretaria de Inovação SP",
        description="Inovação tecnológica para o estado",
        slug="sec-inov-sp",
        website="",
    )
    assert is_startup is False
    assert reason == "government"


def test_enrich_companies_classify_startup_returns_false_for_gob_domain() -> None:
    """A gob.ar website domain is classified as government."""
    is_startup, reason = classify_startup(
        name="Portal Nacional",
        description="",
        slug="portal-nacional",
        website="https://www.gob.ar",
    )
    assert is_startup is False
    assert reason == "government"


def test_enrich_companies_classify_startup_returns_false_for_prefeitura() -> None:
    """Brazilian 'prefeitura' in description triggers government detection."""
    is_startup, reason = classify_startup(
        name="Prefeitura de Belo Horizonte Digital",
        description="",
        slug="pbh-digital",
        website="",
    )
    assert is_startup is False
    assert reason == "government"


# ---------------------------------------------------------------------------
# classify_startup() — personal pages / freelancers
# ---------------------------------------------------------------------------


def test_enrich_companies_classify_startup_returns_false_for_fullstack_dev() -> None:
    """'Fullstack Dev' in name signals a personal profile, not a startup."""
    is_startup, reason = classify_startup(
        name="Wesley Andrade Fullstack Dev",
        description="Personal portfolio",
        slug="wesandrade-dev",
        website="",
    )
    assert is_startup is False
    assert reason == "personal"


def test_enrich_companies_classify_startup_returns_false_for_frontend_dev() -> None:
    """'Frontend <something> Dev' pattern signals a personal page.

    The regex is 'frontend .* dev' which requires at least one character
    between 'frontend' and 'dev'.  'Frontend JavaScript Dev' matches;
    bare 'Frontend Dev' (no middle token) does NOT.
    """
    is_startup, reason = classify_startup(
        name="Maria Silva Frontend JavaScript Dev",
        description="React portfolio",
        slug="maria-frontend",
        website="",
    )
    assert is_startup is False
    assert reason == "personal"


def test_enrich_companies_classify_startup_returns_false_for_professor() -> None:
    """'professor' keyword in name or description triggers personal classification.

    Note: 'prof.' (abbreviation with trailing dot) does NOT match because
    the word boundary after '.' fails.  The full word 'professor' is required.
    """
    is_startup, reason = classify_startup(
        name="Professor de Computação",
        description="",
        slug="prof-computacao",
        website="",
    )
    assert is_startup is False
    assert reason == "personal"


# ---------------------------------------------------------------------------
# classify_startup() — case insensitivity
# ---------------------------------------------------------------------------


def test_enrich_companies_classify_startup_case_insensitive_university() -> None:
    """University pattern matches regardless of input casing."""
    is_startup, reason = classify_startup(
        name="UNIVERSIDADE FEDERAL DO RIO",
        description="",
        slug="ufrj-custom",
        website="",
    )
    assert is_startup is False
    assert reason == "university"


def test_enrich_companies_classify_startup_case_insensitive_government() -> None:
    """Government pattern matches uppercase input."""
    is_startup, reason = classify_startup(
        name="GOBIERNO DE MEXICO",
        description="",
        slug="gob-mex",
        website="",
    )
    assert is_startup is False
    assert reason == "government"


# ---------------------------------------------------------------------------
# classify_sector()
# ---------------------------------------------------------------------------


def test_enrich_companies_classify_sector_returns_fintech_for_banking() -> None:
    """'digital banking platform' maps to Fintech."""
    sector = classify_sector("MyBank", "digital banking platform for consumers", "")
    assert sector == "Fintech"


def test_enrich_companies_classify_sector_returns_fintech_for_payment() -> None:
    """'payment' keyword maps to Fintech."""
    sector = classify_sector("PayCo", "fast payment processing for online merchants", "")
    assert sector == "Fintech"


def test_enrich_companies_classify_sector_returns_ecommerce_for_marketplace() -> None:
    """'marketplace for online shopping' maps to E-commerce."""
    sector = classify_sector("ShopHub", "marketplace for online shopping", "")
    assert sector == "E-commerce"


def test_enrich_companies_classify_sector_returns_ecommerce_for_retail() -> None:
    """'retail' keyword maps to E-commerce."""
    sector = classify_sector("RetailCo", "retail platform for fashion brands", "")
    assert sector == "E-commerce"


def test_enrich_companies_classify_sector_returns_healthtech_for_healthcare() -> None:
    """'healthcare analytics platform' maps to Healthtech."""
    sector = classify_sector("HealthAI", "healthcare analytics platform", "")
    assert sector == "Healthtech"


def test_enrich_companies_classify_sector_returns_healthtech_for_telemedicine() -> None:
    """'telemedicine' keyword maps to Healthtech."""
    sector = classify_sector("DrNow", "telemedicine platform connecting patients to doctors", "")
    assert sector == "Healthtech"


def test_enrich_companies_classify_sector_returns_edtech_for_education() -> None:
    """'online education and learning' maps to Edtech."""
    sector = classify_sector("EduApp", "online education and learning platform", "")
    assert sector == "Edtech"


def test_enrich_companies_classify_sector_returns_edtech_for_bootcamp() -> None:
    """'coding school' maps to Edtech."""
    sector = classify_sector("DevSchool", "coding school for aspiring developers", "")
    assert sector == "Edtech"


def test_enrich_companies_classify_sector_returns_logistics_for_supply_chain() -> None:
    """'supply chain' + 'logistics' maps to Logistics with a clear keyword advantage.

    Using multiple Logistics keywords avoids ties with overlapping sectors
    (e.g., 'retail' would also score an E-commerce hit).
    """
    sector = classify_sector("ChainCo", "logistics and supply chain shipping platform", "")
    assert sector == "Logistics"


def test_enrich_companies_classify_sector_returns_logistics_for_shipping() -> None:
    """'shipping' keyword maps to Logistics."""
    sector = classify_sector("ShipFast", "freight shipping and last mile delivery", "")
    assert sector == "Logistics"


def test_enrich_companies_classify_sector_returns_aiml_for_machine_learning() -> None:
    """Multiple AI/ML keywords (machine learning + deep learning + nlp) maps to AI/ML.

    Using several AI/ML keywords avoids ties with single hits from other sectors
    such as Edtech ('learning') or SaaS ('automation').
    """
    sector = classify_sector("Analytix", "machine learning deep learning nlp platform", "")
    assert sector == "AI/ML"


def test_enrich_companies_classify_sector_returns_aiml_for_llm() -> None:
    """'llm' + 'ai platform' keywords clearly maps to AI/ML.

    'enterprise' alone would score a SaaS hit — pairing with multiple AI/ML
    keywords ensures AI/ML wins the count comparison.
    """
    sector = classify_sector("LLMCo", "llm ai platform neural network for developers", "")
    assert sector == "AI/ML"


def test_enrich_companies_classify_sector_returns_saas_for_cloud_platform() -> None:
    """'cloud platform for developers' maps to SaaS."""
    sector = classify_sector("CloudDev", "cloud platform for developers", "")
    assert sector == "SaaS"


def test_enrich_companies_classify_sector_returns_saas_for_erp() -> None:
    """'erp' keyword maps to SaaS."""
    sector = classify_sector("ERPSoft", "enterprise erp solution for manufacturers", "")
    assert sector == "SaaS"


def test_enrich_companies_classify_sector_returns_proptech_for_real_estate() -> None:
    """Multiple Proptech keywords (real estate + property + housing) maps to Proptech.

    'marketplace' alone would tie Proptech with E-commerce.  Using multiple
    Proptech keywords ensures Proptech wins.
    """
    sector = classify_sector("RealHub", "real estate property housing platform", "")
    assert sector == "Proptech"


def test_enrich_companies_classify_sector_returns_proptech_for_rent() -> None:
    """'rent' keyword maps to Proptech."""
    sector = classify_sector("RentEasy", "rent management platform for landlords", "")
    assert sector == "Proptech"


def test_enrich_companies_classify_sector_returns_hrtech_for_recruiting() -> None:
    """'recruiting and talent platform' maps to HR Tech."""
    sector = classify_sector("TalentLink", "recruiting and talent platform for companies", "")
    assert sector == "HR Tech"


def test_enrich_companies_classify_sector_returns_hrtech_for_payroll() -> None:
    """'payroll' keyword maps to HR Tech."""
    sector = classify_sector("PayPeople", "payroll and benefits management", "")
    assert sector == "HR Tech"


def test_enrich_companies_classify_sector_returns_agritech_for_agriculture() -> None:
    """'precision agriculture technology' maps to Agritech."""
    sector = classify_sector("FarmTech", "precision agriculture technology for crops", "")
    assert sector == "Agritech"


def test_enrich_companies_classify_sector_returns_agritech_for_agro() -> None:
    """'agro' keyword maps to Agritech."""
    sector = classify_sector("AgroBR", "agro management platform for farms", "")
    assert sector == "Agritech"


def test_enrich_companies_classify_sector_returns_none_when_no_keywords_match() -> None:
    """No matching keywords returns None."""
    sector = classify_sector("WeirdCo", "we build cool things for people", "")
    assert sector is None


def test_enrich_companies_classify_sector_returns_none_for_empty_inputs() -> None:
    """Empty name, description, and website returns None."""
    sector = classify_sector("", "", "")
    assert sector is None


def test_enrich_companies_classify_sector_is_case_insensitive() -> None:
    """Sector keyword matching is case insensitive."""
    sector_lower = classify_sector("Co", "digital banking platform", "")
    sector_upper = classify_sector("Co", "DIGITAL BANKING PLATFORM", "")
    assert sector_lower == "Fintech"
    assert sector_upper == "Fintech"


def test_enrich_companies_classify_sector_picks_highest_score_sector() -> None:
    """When multiple sectors match, the one with more keyword hits wins."""
    # "fintech payment banking" = 3 Fintech hits
    # "health" = 1 Healthtech hit
    # Fintech should win
    sector = classify_sector(
        "FinHealth",
        "fintech payment banking digital health",
        "",
    )
    assert sector == "Fintech"


def test_enrich_companies_classify_sector_uses_website_in_matching() -> None:
    """Website URL contributes to keyword matching."""
    # Description alone has no keywords; website domain contains 'health'
    sector = classify_sector("CorpX", "", "https://healthcare-solutions.com")
    assert sector == "Healthtech"


# ---------------------------------------------------------------------------
# generate_tags()
# ---------------------------------------------------------------------------


def test_enrich_companies_generate_tags_sector_is_first_tag() -> None:
    """When sector is provided, it appears as the first tag."""
    tags = generate_tags("Nubank", "digital bank", "Fintech")
    assert len(tags) > 0
    assert tags[0] == "Fintech"


def test_enrich_companies_generate_tags_includes_open_source() -> None:
    """'open source' in description adds 'open-source' tag."""
    tags = generate_tags("MyLib", "open source library for developers", None)
    assert "open-source" in tags


def test_enrich_companies_generate_tags_includes_open_source_hyphenated() -> None:
    """'open-source' (hyphenated) in description also triggers the tag."""
    tags = generate_tags("OpenTool", "open-source tool for teams", None)
    assert "open-source" in tags


def test_enrich_companies_generate_tags_includes_b2b_for_enterprise() -> None:
    """'enterprise' keyword maps to B2B tag."""
    tags = generate_tags("SaaSCo", "enterprise workflow automation", None)
    assert "B2B" in tags


def test_enrich_companies_generate_tags_includes_b2b_for_empresas() -> None:
    """'empresas' (Portuguese) also triggers B2B tag."""
    tags = generate_tags("EmpresaApp", "solução para empresas de médio porte", None)
    assert "B2B" in tags


def test_enrich_companies_generate_tags_includes_brazil_tag() -> None:
    """'brasil' in name or description adds Brazil tag."""
    tags = generate_tags("StartupBrasil", "plataforma para o mercado brasileiro", None)
    assert "Brazil" in tags


def test_enrich_companies_generate_tags_includes_mexico_tag() -> None:
    """'mexico' in description adds Mexico tag."""
    tags = generate_tags("MexCo", "fintech startup focused on mexico", None)
    assert "Mexico" in tags


def test_enrich_companies_generate_tags_includes_argentina_tag() -> None:
    """'argentina' in description adds Argentina tag."""
    tags = generate_tags("ArgApp", "logistics platform serving argentina", None)
    assert "Argentina" in tags


def test_enrich_companies_generate_tags_includes_colombia_tag() -> None:
    """'colombia' in description adds Colombia tag."""
    tags = generate_tags("ColCo", "edtech startup based in colombia", None)
    assert "Colombia" in tags


def test_enrich_companies_generate_tags_includes_mobile_tag() -> None:
    """'mobile' in description adds mobile tag."""
    tags = generate_tags("AppCo", "mobile app for android and ios users", None)
    assert "mobile" in tags


def test_enrich_companies_generate_tags_includes_cloud_tag() -> None:
    """'cloud' in description adds cloud tag."""
    tags = generate_tags("CloudX", "cloud infrastructure for startups", None)
    assert "cloud" in tags


def test_enrich_companies_generate_tags_includes_api_tag() -> None:
    """'api' in description adds API tag."""
    tags = generate_tags("APICo", "rest api platform for developer tools", None)
    assert "API" in tags


def test_enrich_companies_generate_tags_includes_crypto_tag() -> None:
    """'blockchain' in description adds crypto tag."""
    tags = generate_tags("ChainApp", "blockchain payments for defi users", None)
    assert "crypto" in tags


def test_enrich_companies_generate_tags_capped_at_8() -> None:
    """Tags list is capped at 8 elements."""
    # Construct a description that triggers many tags
    name = "MegaCo Brazil Argentina"
    description = (
        "enterprise open-source mobile cloud api blockchain b2b "
        "colombia mexico analytics data marketplace"
    )
    tags = generate_tags(name, description, "Fintech")
    assert len(tags) <= 8


def test_enrich_companies_generate_tags_returns_empty_for_no_matches() -> None:
    """When neither sector nor keywords match, an empty list is returned."""
    tags = generate_tags("WeirdCo", "we do stuff", None)
    assert tags == []


def test_enrich_companies_generate_tags_handles_none_sector() -> None:
    """None sector does not raise an error."""
    tags = generate_tags("OpenProj", "open source project", None)
    assert "open-source" in tags
    # Sector not inserted since it's None
    assert None not in tags


def test_enrich_companies_generate_tags_sector_not_duplicated() -> None:
    """Sector appears exactly once even if it also matches a keyword."""
    # "fintech" in description would add to tag_keywords, but sector insert prepends it
    tags = generate_tags("PayCo", "fintech payments platform", "Fintech")
    assert tags.count("Fintech") == 1


# ---------------------------------------------------------------------------
# fetch_companies()
# ---------------------------------------------------------------------------


def test_enrich_companies_fetch_companies_returns_empty_for_empty_db(session: Session) -> None:
    """fetch_companies returns an empty list when no companies exist."""
    result = fetch_companies(session)
    assert result == []


def test_enrich_companies_fetch_companies_returns_all_rows(session: Session) -> None:
    """fetch_companies returns one dict per inserted company."""
    _insert_company(session, slug="nubank", name="Nubank")
    _insert_company(session, slug="pipefy", name="Pipefy")
    _insert_company(session, slug="totvs", name="Totvs")

    result = fetch_companies(session)
    assert len(result) == 3


def test_enrich_companies_fetch_companies_returns_expected_fields(session: Session) -> None:
    """Each returned dict contains the required fields."""
    _insert_company(
        session,
        slug="nubank",
        name="Nubank",
        description="Digital bank",
        website="https://nubank.com.br",
        sector="Fintech",
        tags=["Fintech", "B2B"],
        status="active",
    )

    rows = fetch_companies(session)
    assert len(rows) == 1
    row = rows[0]

    assert row["slug"] == "nubank"
    assert row["name"] == "Nubank"
    assert row["description"] == "Digital bank"
    assert row["website"] == "https://nubank.com.br"
    assert row["sector"] == "Fintech"
    assert row["status"] == "active"


def test_enrich_companies_fetch_companies_ordered_by_name(session: Session) -> None:
    """fetch_companies returns rows ordered alphabetically by name."""
    _insert_company(session, slug="zzz-co", name="Zzz Co")
    _insert_company(session, slug="aaa-co", name="Aaa Co")
    _insert_company(session, slug="mmm-co", name="Mmm Co")

    result = fetch_companies(session)
    names = [r["name"] for r in result]
    assert names == sorted(names)


def test_enrich_companies_fetch_companies_handles_null_fields(session: Session) -> None:
    """fetch_companies handles None description, website, sector gracefully."""
    _insert_company(
        session, slug="minimal-co", name="Minimal Co",
        description="", website="", sector=None, tags=None,
    )

    rows = fetch_companies(session)
    assert len(rows) == 1
    row = rows[0]
    assert row["sector"] is None


# ---------------------------------------------------------------------------
# update_company()
# ---------------------------------------------------------------------------


def test_enrich_companies_update_company_sets_sector(session: Session) -> None:
    """update_company writes the sector field to the database."""
    _insert_company(session, slug="pipefy", name="Pipefy")

    update_company(session, "pipefy", sector="SaaS", tags=None)
    session.commit()

    row = session.execute(
        text("SELECT sector FROM companies WHERE slug = :slug"), {"slug": "pipefy"}
    ).fetchone()
    assert row[0] == "SaaS"


def test_enrich_companies_update_company_sets_tags(session: Session) -> None:
    """update_company writes the tags JSON to the database."""
    _insert_company(session, slug="nubank", name="Nubank")

    update_company(session, "nubank", sector="Fintech", tags=["Fintech", "B2B", "Brazil"])
    session.commit()

    raw = session.execute(
        text("SELECT tags FROM companies WHERE slug = :slug"), {"slug": "nubank"}
    ).scalar()
    # SQLite stores JSON as text; parse it back
    loaded = json.loads(raw) if isinstance(raw, str) else raw
    assert loaded == ["Fintech", "B2B", "Brazil"]


def test_enrich_companies_update_company_sets_status(session: Session) -> None:
    """update_company can update status to 'inactive'."""
    _insert_company(session, slug="gcba", name="GCBA", status="active")

    update_company(session, "gcba", sector=None, tags=None, status="inactive")
    session.commit()

    row = session.execute(
        text("SELECT status FROM companies WHERE slug = :slug"), {"slug": "gcba"}
    ).fetchone()
    assert row[0] == "inactive"


def test_enrich_companies_update_company_partial_update_sector_only(session: Session) -> None:
    """Passing only sector does not overwrite existing tags or status."""
    _insert_company(session, slug="co", name="Co", tags=["API"], status="active")

    update_company(session, "co", sector="SaaS", tags=None)
    session.commit()

    row = session.execute(
        text("SELECT sector, status FROM companies WHERE slug = :slug"), {"slug": "co"}
    ).fetchone()
    # sector updated, status preserved
    assert row[0] == "SaaS"
    assert row[1] == "active"


def test_enrich_companies_update_company_noop_when_no_fields(session: Session) -> None:
    """update_company with no updatable fields does not raise and leaves DB unchanged."""
    _insert_company(session, slug="noop-co", name="Noop Co", status="active")

    # All None — nothing to update
    update_company(session, "noop-co", sector=None, tags=None, status=None)
    session.commit()

    row = session.execute(
        text("SELECT sector, status FROM companies WHERE slug = :slug"), {"slug": "noop-co"}
    ).fetchone()
    assert row[0] is None
    assert row[1] == "active"


def test_enrich_companies_update_company_nonexistent_slug_does_not_raise(
    session: Session,
) -> None:
    """Updating a slug that does not exist in the DB executes without error."""
    update_company(session, "nonexistent-slug", sector="SaaS", tags=["SaaS"])
    session.commit()
    # No rows affected — no exception raised
    count = session.execute(text("SELECT count(*) FROM companies")).scalar()
    assert count == 0


# ---------------------------------------------------------------------------
# Integration: classify_startup + classify_sector + generate_tags round-trip
# ---------------------------------------------------------------------------


def test_enrich_companies_integration_full_enrichment_pipeline(session: Session) -> None:
    """A real startup is classified, sectored, tagged, and updated in DB correctly."""
    _insert_company(
        session,
        slug="nubank",
        name="Nubank",
        description="Digital neobank for consumer banking and payments in Brazil",
        website="https://nubank.com.br",
        sector=None,
        tags=None,
    )

    rows = fetch_companies(session)
    assert len(rows) == 1
    co = rows[0]

    is_startup, _ = classify_startup(
        co["name"], co["description"] or "", co["slug"], co["website"] or ""
    )
    assert is_startup is True

    sector = classify_sector(co["name"], co["description"] or "", co["website"] or "")
    assert sector == "Fintech"

    tags = generate_tags(co["name"], co["description"] or "", sector)
    assert "Fintech" in tags
    assert "Brazil" in tags

    update_company(session, co["slug"], sector=sector, tags=tags)
    session.commit()

    updated = session.execute(
        text("SELECT sector FROM companies WHERE slug = :slug"), {"slug": "nubank"}
    ).scalar()
    assert updated == "Fintech"


def test_enrich_companies_integration_non_startup_deactivation(session: Session) -> None:
    """A blocklisted slug is classified as non-startup and can be deactivated."""
    _insert_company(session, slug="gcba", name="Gobierno de Buenos Aires", status="active")

    rows = fetch_companies(session)
    co = rows[0]

    is_startup, reason = classify_startup(
        co["name"], co["description"] or "", co["slug"], co["website"] or ""
    )
    assert is_startup is False
    assert reason == "slug_blocklist"

    update_company(session, co["slug"], sector=None, tags=None, status="inactive")
    session.commit()

    status = session.execute(
        text("SELECT status FROM companies WHERE slug = :slug"), {"slug": "gcba"}
    ).scalar()
    assert status == "inactive"
