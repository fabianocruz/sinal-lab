"""Database source collector for MERCADO agent.

Reads active companies from the ``companies`` table (populated by INDEX
with Crunchbase, YC, ABStartups, etc.) and converts them to CompanyProfile
objects for the MERCADO pipeline.

This provides a much richer data source than GitHub org search alone.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.github_orgs import CompanyProfile

logger = logging.getLogger(__name__)


def _company_to_profile(company: "Company") -> CompanyProfile:  # noqa: F821
    """Convert a Company ORM record to a CompanyProfile dataclass.

    Maps all relevant Company fields to CompanyProfile fields.
    """
    return CompanyProfile(
        name=company.name,
        slug=company.slug,
        website=company.website,
        description=company.short_description or company.description,
        sector=company.sector,
        city=company.city,
        country=company.country or "Brasil",
        founded_date=company.founded_date,
        team_size=company.team_size,
        linkedin_url=company.linkedin_url,
        github_url=company.github_url,
        tech_stack=company.tech_stack or [],
        tags=company.tags or [],
        source_url=company.website or "",
        source_name="companies_db",
    )


def collect_from_database(
    session: Session,
    provenance: ProvenanceTracker,
    limit: int = 500,
    country: Optional[str] = None,
) -> list[CompanyProfile]:
    """Read active companies from the database.

    Args:
        session: SQLAlchemy session.
        provenance: Provenance tracker for source recording.
        limit: Maximum number of companies to fetch.
        country: Optional country filter (e.g. "Brazil").

    Returns:
        List of CompanyProfile objects from the database.
    """
    try:
        from packages.database.models import Company
    except ImportError:
        logger.warning("Could not import Company model, skipping DB source")
        return []

    query = session.query(Company).filter(Company.status == "active")

    if country:
        query = query.filter(Company.country == country)

    query = query.order_by(Company.updated_at.desc()).limit(limit)

    companies = query.all()

    profiles: list[CompanyProfile] = []
    for company in companies:
        profile = _company_to_profile(company)
        profiles.append(profile)

        provenance.track(
            source_url=profile.source_url or f"db://companies/{company.slug}",
            source_name="companies_db",
            extraction_method="database",
        )

    logger.info(
        "Collected %d company profiles from database (limit=%d)",
        len(profiles),
        limit,
    )
    return profiles
