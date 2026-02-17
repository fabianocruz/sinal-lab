"""Database persistence for MERCADO agent.

Handles Company upsert logic with confidence-based merging
and Ecosystem metadata updates.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.agents.mercado.collector import CompanyProfile
from packages.database.models.company import Company
from packages.database.models.ecosystem import Ecosystem

logger = logging.getLogger(__name__)


def upsert_company(
    session: Session,
    profile: CompanyProfile,
    confidence: float,
) -> Company:
    """Insert or update a company record.

    Logic:
    - Check if exists by slug
    - If exists and new confidence > old confidence: update
    - Else: insert new record

    Args:
        session: SQLAlchemy session
        profile: CompanyProfile to persist
        confidence: Confidence score (0-1)

    Returns:
        Company record (existing or new)
    """
    if not profile.slug:
        logger.warning("Cannot persist company without slug: %s", profile.name)
        profile.slug = profile.name.lower().replace(" ", "-")

    # Check if exists
    existing = session.query(Company).filter_by(slug=profile.slug).first()

    if existing:
        # Get existing confidence from metadata
        existing_confidence = existing.metadata_.get("confidence", 0.0) if existing.metadata_ else 0.0

        # Update only if new confidence > old OR field was NULL
        if confidence > existing_confidence:
            logger.info(
                "Updating company %s (confidence: %.2f -> %.2f)",
                profile.name,
                existing_confidence,
                confidence,
            )

            # Update fields (preserve non-null existing data if new data is null)
            existing.name = profile.name
            existing.description = profile.description or existing.description
            existing.website = profile.website or existing.website
            existing.city = profile.city or existing.city
            existing.country = profile.country or existing.country

            # Update metadata
            if not existing.metadata_:
                existing.metadata_ = {}

            existing.metadata_["sector"] = profile.sector
            existing.metadata_["github_url"] = profile.github_url
            existing.metadata_["linkedin_url"] = profile.linkedin_url
            existing.metadata_["tech_stack"] = profile.tech_stack
            existing.metadata_["tags"] = profile.tags
            existing.metadata_["confidence"] = confidence
            existing.metadata_["last_updated_by_agent"] = "mercado"

            existing.updated_at = datetime.now(timezone.utc)

            session.commit()
            return existing
        else:
            logger.debug(
                "Skipping update for %s (existing confidence %.2f >= new %.2f)",
                profile.name,
                existing_confidence,
                confidence,
            )
            return existing

    # Insert new record
    company = Company(
        id=uuid4(),
        slug=profile.slug,
        name=profile.name,
        description=profile.description,
        website=profile.website,
        city=profile.city,
        country=profile.country,
        status="active",
        metadata_={
            "sector": profile.sector,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
            "tech_stack": profile.tech_stack,
            "tags": profile.tags,
            "confidence": confidence,
            "discovered_by_agent": "mercado",
        },
    )

    session.add(company)
    session.commit()

    logger.info(
        "Inserted new company: %s (%.2f confidence)",
        profile.name,
        confidence,
    )

    return company


def update_ecosystem_stats(
    session: Session,
    city: str,
    country: str,
) -> None:
    """Update Ecosystem metadata with aggregated stats.

    Updates:
    - total_startups
    - top_sectors (top 5)
    - notable_companies (top 10 by confidence)

    Args:
        session: SQLAlchemy session
        city: City name
        country: Country name
    """
    if not city:
        logger.debug("Skipping ecosystem update for null city")
        return

    # Get or create ecosystem
    ecosystem_slug = f"{city.lower().replace(' ', '-')}-{country.lower()}"
    ecosystem = session.query(Ecosystem).filter_by(slug=ecosystem_slug).first()

    if not ecosystem:
        ecosystem = Ecosystem(
            id=uuid4(),
            slug=ecosystem_slug,
            name=f"{city}, {country}",
            country=country,
            metadata_={},
        )
        session.add(ecosystem)

    # Get all active companies in this city
    companies = (
        session.query(Company)
        .filter_by(city=city, country=country, status="active")
        .all()
    )

    if not companies:
        return

    # Compute total_startups
    total_startups = len(companies)

    # Compute top_sectors
    sector_counts: dict[str, int] = {}
    for company in companies:
        sector = company.metadata_.get("sector") if company.metadata_ else None
        if sector:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

    top_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_sectors_list = [s[0] for s in top_sectors]

    # Compute notable_companies (top 10 by confidence)
    companies_with_confidence = [
        (c, c.metadata_.get("confidence", 0.0))
        for c in companies
        if c.metadata_
    ]
    companies_with_confidence.sort(key=lambda x: x[1], reverse=True)
    notable_companies = [c[0].slug for c in companies_with_confidence[:10]]

    # Update ecosystem metadata
    if not ecosystem.metadata_:
        ecosystem.metadata_ = {}

    ecosystem.metadata_["total_startups"] = total_startups
    ecosystem.metadata_["top_sectors"] = top_sectors_list
    ecosystem.metadata_["notable_companies"] = notable_companies
    ecosystem.updated_at = datetime.now(timezone.utc)

    session.commit()

    logger.info(
        "Updated ecosystem %s: %d startups, top sectors: %s",
        ecosystem_slug,
        total_startups,
        top_sectors_list,
    )


def persist_all_profiles(
    session: Session,
    profiles: list[tuple[CompanyProfile, float]],
) -> dict[str, int]:
    """Persist all company profiles to database.

    Args:
        session: SQLAlchemy session
        profiles: List of (CompanyProfile, confidence) tuples

    Returns:
        Dictionary with stats: {"inserted": X, "updated": Y, "skipped": Z}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0}

    for profile, confidence in profiles:
        # Get existing record count before upsert
        existing_count = session.query(Company).filter_by(slug=profile.slug).count()

        # Upsert
        result = upsert_company(session, profile, confidence)

        # Update stats
        if existing_count == 0:
            stats["inserted"] += 1
        elif result.metadata_ and result.metadata_.get("confidence") == confidence:
            stats["updated"] += 1
        else:
            stats["skipped"] += 1

        # Update ecosystem stats if city exists
        if profile.city:
            update_ecosystem_stats(session, profile.city, profile.country)

    logger.info(
        "Persistence complete: %d inserted, %d updated, %d skipped",
        stats["inserted"],
        stats["updated"],
        stats["skipped"],
    )

    return stats
