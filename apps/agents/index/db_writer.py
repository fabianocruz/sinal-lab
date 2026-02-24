"""Database persistence for INDEX agent.

Handles Company upsert with cross-source dedup via CompanyExternalId,
source_count tracking, and ecosystem stats updates.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from apps.agents.index.pipeline import FUNDING_STAGE_PRIORITY, MergedCompany
from apps.agents.sources.entity_matcher import normalize_cnpj, normalize_domain
from packages.database.models.company import Company
from packages.database.models.company_external_id import CompanyExternalId
from packages.database.models.ecosystem import Ecosystem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Quality gate — filter out non-startup entities before persistence
# ---------------------------------------------------------------------------

# Aligned with INDEX_CONFIG.min_confidence_to_publish (0.3).
# Data agents should store all LATAM companies — the editorial pipeline
# applies stricter quality filters before publication.
MIN_INDEX_SCORE = 0.30

_NON_STARTUP_NAME_PATTERNS = (
    # Universities / education
    "universid", "universidad", "university", "faculdade", "faculty",
    "maestría", "mestrado", "doutorado", "licenciatura",
    "escola", "school", "college", "politécnic",
    "programa de", "curso de", "disciplina",
    # Specific institutions
    "utn ", "ufrj", "usp ", "unicamp", "unam",
    # Government / non-profit
    "instituto", "institute",
    "prefeitura", "gobierno", "government", "ministério", "ministry",
    "fundação", "fundacion", "foundation",
    # Churches / religious orgs
    "igreja", "paróquia", "diocese",
)


def _is_non_startup(name: str) -> bool:
    """Return True if the name matches a known non-startup pattern."""
    lower = name.lower()
    return any(pat in lower for pat in _NON_STARTUP_NAME_PATTERNS)


def cleanup_non_startups(session: Session) -> int:
    """Mark existing non-startup entries as inactive.

    Scans all active companies and deactivates those matching
    non-startup name patterns. Intended for one-time cleanup runs.

    Args:
        session: SQLAlchemy session (caller must commit).

    Returns:
        Number of companies deactivated.
    """
    companies = session.query(Company).filter(Company.status == "active").all()
    deactivated = 0
    for c in companies:
        if _is_non_startup(c.name):
            c.status = "inactive"
            deactivated += 1
            logger.info("Deactivated non-startup: %s (slug=%s)", c.name, c.slug)
    session.flush()
    logger.info("Cleanup complete: %d non-startup entries deactivated", deactivated)
    return deactivated


def _register_external_ids(
    session: Session,
    company_slug: str,
    merged: MergedCompany,
) -> int:
    """Register external IDs for a company.

    Creates CompanyExternalId records for all known identifiers
    (CNPJ, domain, permalink, github_login). Skips if already exists.

    Args:
        session: SQLAlchemy session (not committed).
        company_slug: The company's slug.
        merged: MergedCompany with external IDs.

    Returns:
        Number of new external IDs registered.
    """
    registered = 0
    ids_to_register: list[tuple[str, str, str, float]] = []

    # CNPJ
    if merged.cnpj:
        cnpj = normalize_cnpj(merged.cnpj)
        if cnpj:
            ids_to_register.append(("cnpj", cnpj, "receita_federal", 1.0))

    # Domain
    domain = merged.domain or normalize_domain(merged.website)
    if domain:
        ids_to_register.append(("domain", domain.lower(), merged.sources[0] if merged.sources else "index", 0.95))

    # Crunchbase permalink
    if merged.crunchbase_permalink:
        ids_to_register.append(("crunchbase_permalink", merged.crunchbase_permalink, "crunchbase", 0.9))

    # GitHub login
    if merged.github_login:
        ids_to_register.append(("github_login", merged.github_login, "github", 0.7))

    for id_type, id_value, source_name, confidence in ids_to_register:
        existing = (
            session.query(CompanyExternalId)
            .filter_by(id_type=id_type, id_value=id_value)
            .first()
        )
        if existing:
            # Update company_slug if different (company was renamed/merged)
            if existing.company_slug != company_slug:
                logger.warning(
                    "External ID %s=%s already registered to %s, skipping (wanted %s)",
                    id_type, id_value, existing.company_slug, company_slug,
                )
            continue

        ext_id = CompanyExternalId(
            id=uuid4(),
            company_slug=company_slug,
            id_type=id_type,
            id_value=id_value,
            source_name=source_name,
            confidence=confidence,
        )
        session.add(ext_id)
        registered += 1

    return registered


def upsert_company_from_index(
    session: Session,
    merged: MergedCompany,
    score: float,
) -> str:
    """Insert or update a company from the INDEX pipeline.

    Logic:
    - If exists by slug: update if score > existing confidence, always increment source_count
    - If new: insert with all available fields

    Args:
        session: SQLAlchemy session (not committed).
        merged: MergedCompany from pipeline.
        score: Composite score from scorer.

    Returns:
        "inserted", "updated", or "skipped"
    """
    existing = session.query(Company).filter_by(slug=merged.slug).first()

    if existing:
        existing_confidence = existing.metadata_.get("confidence", 0.0) if existing.metadata_ else 0.0

        # Always update source_count
        existing.source_count = max(
            getattr(existing, "source_count", 1) or 1,
            merged.source_count,
        )

        if score > existing_confidence:
            # Update fields (preserve non-null existing data)
            existing.name = merged.name
            existing.description = merged.description or existing.description
            existing.website = merged.website or existing.website
            existing.city = merged.city or existing.city
            existing.state = merged.state or existing.state
            existing.country = merged.country or existing.country
            existing.sector = merged.sector or existing.sector
            existing.github_url = merged.github_url or existing.github_url
            existing.linkedin_url = merged.linkedin_url or existing.linkedin_url
            existing.twitter_url = merged.twitter_url or existing.twitter_url
            existing.business_model = merged.business_model or existing.business_model

            # Funding: total_funding_usd — take MAX
            if merged.total_funding_usd is not None:
                if existing.total_funding_usd is None or merged.total_funding_usd > existing.total_funding_usd:
                    existing.total_funding_usd = merged.total_funding_usd

            # Funding: funding_stage — take highest priority
            if merged.funding_stage:
                cur = FUNDING_STAGE_PRIORITY.get(existing.funding_stage or "", -1)
                new = FUNDING_STAGE_PRIORITY.get(merged.funding_stage, -1)
                if new > cur:
                    existing.funding_stage = merged.funding_stage

            # Set CNPJ if available
            if merged.cnpj and not getattr(existing, "cnpj", None):
                existing.cnpj = merged.cnpj

            # Merge tech_stack and tags
            if merged.tech_stack:
                old_stack = existing.tech_stack or []
                existing.tech_stack = sorted(set(old_stack) | set(merged.tech_stack))

            if merged.tags:
                old_tags = existing.tags or []
                existing.tags = sorted(set(old_tags) | set(merged.tags))

            # Update metadata
            if not existing.metadata_:
                existing.metadata_ = {}
            existing.metadata_["confidence"] = score
            existing.metadata_["source_count"] = merged.source_count
            existing.metadata_["sources"] = merged.sources
            existing.metadata_["last_updated_by_agent"] = "index"
            flag_modified(existing, "metadata_")

            existing.updated_at = datetime.now(timezone.utc)

            # Register external IDs
            _register_external_ids(session, merged.slug, merged)

            logger.debug("Updated company %s (score: %.3f)", merged.slug, score)
            return "updated"
        else:
            # Register external IDs even if score didn't beat existing
            _register_external_ids(session, merged.slug, merged)
            logger.debug("Skipped update for %s (existing %.3f >= new %.3f)", merged.slug, existing_confidence, score)
            return "skipped"

    # Insert new record
    company = Company(
        id=uuid4(),
        slug=merged.slug,
        name=merged.name,
        description=merged.description,
        website=merged.website,
        sector=merged.sector,
        city=merged.city,
        state=merged.state,
        country=merged.country,
        github_url=merged.github_url,
        linkedin_url=merged.linkedin_url,
        twitter_url=merged.twitter_url,
        business_model=merged.business_model,
        funding_stage=merged.funding_stage,
        total_funding_usd=merged.total_funding_usd,
        tech_stack=merged.tech_stack or None,
        tags=merged.tags or None,
        status="active",
        source_count=merged.source_count,
        metadata_={
            "confidence": score,
            "source_count": merged.source_count,
            "sources": merged.sources,
            "discovered_by_agent": "index",
        },
    )

    # Set CNPJ if available
    if merged.cnpj:
        company.cnpj = merged.cnpj

    session.add(company)

    # Register external IDs
    _register_external_ids(session, merged.slug, merged)

    logger.debug("Inserted company %s (score: %.3f)", merged.slug, score)
    return "inserted"


def persist_index_results(
    session: Session,
    scored_companies: list[tuple],  # list[tuple[MergedCompany, float]]
) -> dict[str, int]:
    """Persist all INDEX pipeline results to database.

    Applies quality gate: skips entries below MIN_INDEX_SCORE or
    matching non-startup name patterns (universities, government, etc.).

    Args:
        session: SQLAlchemy session.
        scored_companies: List of (MergedCompany, score) tuples.

    Returns:
        Stats dict: {"inserted": N, "updated": N, "skipped": N, "filtered": N}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "filtered": 0}

    for merged, score in scored_companies:
        # Quality gate: minimum score threshold
        if score < MIN_INDEX_SCORE:
            logger.debug("Filtered %s (score %.3f < %.3f)", merged.name, score, MIN_INDEX_SCORE)
            stats["filtered"] += 1
            continue

        # Quality gate: non-startup name patterns
        if _is_non_startup(merged.name):
            logger.debug("Filtered non-startup: %s", merged.name)
            stats["filtered"] += 1
            continue

        result = upsert_company_from_index(session, merged, score)
        stats[result] = stats.get(result, 0) + 1

    session.flush()

    logger.info(
        "INDEX persistence complete: %d inserted, %d updated, %d skipped, %d filtered",
        stats["inserted"],
        stats["updated"],
        stats["skipped"],
        stats["filtered"],
    )

    return stats
