"""Converters from source-specific dataclasses to CandidateCompany.

Each converter normalizes source data into the shared CandidateCompany
format used by the entity matcher and pipeline.  Sector fields are
normalized to canonical SECTOR_OPTIONS via ``normalize_sector()``.
"""

import logging
from typing import Optional

from apps.agents.sources.entity_matcher import CandidateCompany, normalize_cnpj, normalize_domain
from apps.agents.sources.sector_normalizer import normalize_sector

logger = logging.getLogger(__name__)


def from_receita_federal(
    company,  # ReceitaFederalCompany
    confidence: float = 0.9,
) -> CandidateCompany:
    """Convert a Receita Federal record to CandidateCompany.

    Args:
        company: ReceitaFederalCompany dataclass.
        confidence: Source confidence (default 0.9 for government data).

    Returns:
        CandidateCompany with CNPJ as primary dedup key.
    """
    cnpj = normalize_cnpj(company.cnpj)
    name = company.nome_fantasia or company.razao_social
    slug = name.lower().replace(" ", "-").replace(".", "").replace("/", "")[:100] if name else None

    return CandidateCompany(
        name=name,
        slug=slug,
        city=company.municipio,
        state=company.uf,
        country="Brasil",
        cnpj=cnpj,
        source_name="receita_federal",
        confidence=confidence,
        founded_date=company.data_abertura or None,
    )


def from_abstartups(
    company,  # ABStartupsCompany
    confidence: float = 0.7,
) -> CandidateCompany:
    """Convert an ABStartups record to CandidateCompany.

    Args:
        company: ABStartupsCompany dataclass.
        confidence: Source confidence (default 0.7).

    Returns:
        CandidateCompany with domain and name as dedup keys.
    """
    domain = normalize_domain(company.website)

    return CandidateCompany(
        name=company.name,
        slug=company.slug,
        website=company.website,
        description=company.description,
        sector=normalize_sector(company.sector) or company.sector,
        city=company.city,
        state=company.state,
        country="Brasil",
        domain=domain,
        source_name="abstartups",
        confidence=confidence,
        business_model=company.business_model,
    )


def from_yc(
    company,  # YCCompany
    confidence: float = 0.85,
) -> CandidateCompany:
    """Convert a YC Portfolio record to CandidateCompany.

    Args:
        company: YCCompany dataclass.
        confidence: Source confidence (default 0.85).

    Returns:
        CandidateCompany with domain as primary dedup key.
    """
    domain = normalize_domain(company.website)

    return CandidateCompany(
        name=company.name,
        slug=company.slug,
        website=company.website,
        description=company.description,
        sector=normalize_sector(company.vertical) or company.vertical,
        city=company.city,
        country=company.country or "Brasil",
        domain=domain,
        source_name="yc_portfolio",
        confidence=confidence,
        team_size=company.team_size,
        tags=[company.batch] if company.batch else [],
    )


def from_github(
    profile,  # CompanyProfile from mercado.collector
    confidence: float = 0.5,
) -> CandidateCompany:
    """Convert a GitHub-sourced CompanyProfile to CandidateCompany.

    Args:
        profile: CompanyProfile dataclass from MERCADO's collector.
        confidence: Source confidence (default 0.5).

    Returns:
        CandidateCompany with github_login as dedup key.
    """
    domain = normalize_domain(profile.website)

    return CandidateCompany(
        name=profile.name,
        slug=profile.slug,
        website=profile.website,
        description=profile.description,
        sector=normalize_sector(profile.sector) or profile.sector,
        city=profile.city,
        country=profile.country,
        domain=domain,
        github_login=profile.slug,  # GitHub login is the slug
        github_url=profile.github_url,
        source_name=profile.source_name or "github",
        confidence=confidence,
        tech_stack=profile.tech_stack,
        tags=profile.tags,
    )


def from_crunchbase(
    company,  # CrunchbaseCompany or CrunchbaseOpenCompany
    confidence: float = 0.8,
) -> CandidateCompany:
    """Convert a Crunchbase record to CandidateCompany.

    Args:
        company: CrunchbaseCompany or CrunchbaseOpenCompany dataclass.
        confidence: Source confidence (default 0.8).

    Returns:
        CandidateCompany with crunchbase_permalink as dedup key.
    """
    domain = normalize_domain(getattr(company, "domain", None) or getattr(company, "website_url", None))

    # Handle both CrunchbaseCompany and CrunchbaseOpenCompany
    city = getattr(company, "city", None) or getattr(company, "headquarters_location", None) or ""
    country = getattr(company, "country", None) or ""
    categories = getattr(company, "categories", [])
    founded_on = getattr(company, "founded_on", None)

    # Derive sector from Crunchbase categories
    sector = None
    for cat in categories:
        sector = normalize_sector(cat)
        if sector:
            break

    return CandidateCompany(
        name=company.name,
        slug=company.permalink,
        website=getattr(company, "website_url", None) or getattr(company, "domain", None),
        description=getattr(company, "short_description", ""),
        sector=sector,
        city=city,
        country=country or "Brasil",
        domain=domain,
        crunchbase_permalink=company.permalink,
        source_name="crunchbase",
        confidence=confidence,
        founded_date=str(founded_on) if founded_on else None,
        tags=[c.lower() for c in categories[:5]] if categories else [],
    )


def from_startups_latam(
    company,  # StartupsLatamCompany
    confidence: float = 0.7,
) -> CandidateCompany:
    """Convert a StartupsLatam record to CandidateCompany.

    Args:
        company: StartupsLatamCompany dataclass.
        confidence: Source confidence (default 0.7 for curated directory).

    Returns:
        CandidateCompany with slug and name as dedup keys.
    """
    from apps.agents.sources.startups_latam import INDUSTRY_ALIASES

    # Map StartupsLatam industry → sector normalizer input
    raw_sector = INDUSTRY_ALIASES.get(company.industry, company.industry)
    sector = normalize_sector(raw_sector)

    return CandidateCompany(
        name=company.name,
        slug=company.slug,
        description=company.description,
        sector=sector,
        country=company.country,
        source_name="startups_latam",
        confidence=confidence,
        tags=[company.industry.lower()] if company.industry else [],
    )


def from_coresignal(
    company,  # CoreSignalCompany
    confidence: float = 0.8,
) -> CandidateCompany:
    """Convert a CoreSignal record to CandidateCompany.

    Args:
        company: CoreSignalCompany dataclass.
        confidence: Source confidence (default 0.8 for LinkedIn-sourced data).

    Returns:
        CandidateCompany with domain and linkedin_url as dedup keys.
    """
    domain = normalize_domain(company.website)
    sector = normalize_sector(company.industry) if company.industry else None

    return CandidateCompany(
        name=company.name,
        slug=company.slug,
        website=company.website,
        description=company.description,
        sector=sector,
        city=company.city,
        country=company.country or "Brasil",
        domain=domain,
        linkedin_url=company.linkedin_url,
        source_name="coresignal",
        confidence=confidence,
        team_size=company.employees_count,
        founded_date=str(company.founded_year) if company.founded_year else None,
    )


def convert_all(
    receita_companies: list = None,
    abstartups_companies: list = None,
    yc_companies: list = None,
    github_profiles: list = None,
    crunchbase_companies: list = None,
    startups_latam_companies: list = None,
    coresignal_companies: list = None,
) -> list[CandidateCompany]:
    """Convert all source records to CandidateCompany format.

    Args:
        receita_companies: List of ReceitaFederalCompany objects.
        abstartups_companies: List of ABStartupsCompany objects.
        yc_companies: List of YCCompany objects.
        github_profiles: List of CompanyProfile objects.
        crunchbase_companies: List of CrunchbaseCompany/CrunchbaseOpenCompany objects.

    Returns:
        Combined list of CandidateCompany objects.
    """
    candidates: list[CandidateCompany] = []

    if receita_companies:
        for c in receita_companies:
            candidates.append(from_receita_federal(c))
        logger.info("Converted %d Receita Federal records", len(receita_companies))

    if abstartups_companies:
        for c in abstartups_companies:
            candidates.append(from_abstartups(c))
        logger.info("Converted %d ABStartups records", len(abstartups_companies))

    if yc_companies:
        for c in yc_companies:
            candidates.append(from_yc(c))
        logger.info("Converted %d YC records", len(yc_companies))

    if github_profiles:
        for p in github_profiles:
            candidates.append(from_github(p))
        logger.info("Converted %d GitHub profiles", len(github_profiles))

    if crunchbase_companies:
        for c in crunchbase_companies:
            candidates.append(from_crunchbase(c))
        logger.info("Converted %d Crunchbase records", len(crunchbase_companies))

    if startups_latam_companies:
        for c in startups_latam_companies:
            candidates.append(from_startups_latam(c))
        logger.info("Converted %d StartupsLatam records", len(startups_latam_companies))

    if coresignal_companies:
        for c in coresignal_companies:
            candidates.append(from_coresignal(c))
        logger.info("Converted %d CoreSignal records", len(coresignal_companies))

    logger.info("Total candidates converted: %d", len(candidates))
    return candidates
