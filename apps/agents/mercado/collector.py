"""Data collection for MERCADO agent.

Collects company profiles from GitHub, Dealroom API, and other sources.

GitHub collection and startup filtering are delegated to the shared
``apps.agents.sources.github_orgs`` module. This module re-exports key
symbols for backward compatibility.
"""

import logging

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker

# Re-export from shared module for backward compatibility.
# MERCADO tests and other code import these from here.
from apps.agents.sources.github_orgs import (  # noqa: F401
    CompanyProfile,
    collect_from_github,
    is_likely_startup,
    score_startup_likelihood,
)

logger = logging.getLogger(__name__)


def collect_from_dealroom(
    source: DataSourceConfig,
    provenance: ProvenanceTracker,
) -> list[CompanyProfile]:
    """Collect company profiles from Dealroom API.

    Args:
        source: Dealroom API data source configuration
        provenance: Provenance tracker for source recording

    Returns:
        List of CompanyProfile objects from Dealroom
    """
    # TODO: Implement when Dealroom API key is available
    logger.info("Dealroom API not yet configured, skipping %s", source.name)
    return []


def collect_all_sources(
    sources: list[DataSourceConfig],
    provenance: ProvenanceTracker,
) -> list[CompanyProfile]:
    """Collect company profiles from all configured sources.

    Args:
        sources: List of data source configurations
        provenance: Provenance tracker for source recording

    Returns:
        Combined list of CompanyProfile objects from all sources
    """
    all_profiles: list[CompanyProfile] = []

    for source in sources:
        if not source.enabled:
            logger.debug("Skipping disabled source: %s", source.name)
            continue

        if "gtrends" in source.name:
            # Google Trends data is supplementary — collected separately
            # by the agent via collect_market_trends()
            logger.debug(
                "Skipping gtrends source %s in profile collection "
                "(used by synthesizer)",
                source.name,
            )
            continue

        if "bcb" in source.name:
            try:
                from apps.agents.sources.bcb_institutions import fetch_bcb_institutions

                segments_str = source.params.get("segments", "")
                segments = [s.strip() for s in segments_str.split(",") if s.strip()] if segments_str else None

                with httpx.Client(timeout=15.0) as bcb_client:
                    institutions = fetch_bcb_institutions(source, bcb_client, segments=segments)

                for inst in institutions:
                    cnpj_clean = inst.cnpj.replace(".", "").replace("/", "").replace("-", "")
                    profile = CompanyProfile(
                        name=inst.name,
                        slug=cnpj_clean,
                        city=inst.municipality,
                        country="Brasil",
                        sector="Fintech",
                        tags=[inst.segment, "bcb-authorized"],
                        source_url="https://www.bcb.gov.br/estabilidadefinanceira/encontreinstituicao",
                        source_name="bcb_authorized",
                    )
                    all_profiles.append(profile)
                    provenance.track(
                        source_url=profile.source_url,
                        source_name="bcb_authorized",
                        extraction_method="api",
                    )
                logger.info("Collected %d BCB institutions", len(institutions))
            except Exception as e:
                logger.warning("BCB collection failed (graceful degradation): %s", e)
            continue

        if "gupy" in source.name:
            # Gupy enrichment handled separately in agent.process()
            logger.debug("Skipping gupy source %s in profile collection", source.name)
            continue

        if "crunchbase" in source.name:
            # Crunchbase company discovery — converts CrunchbaseCompany to CompanyProfile
            from apps.agents.sources.crunchbase import fetch_companies

            locations_str = source.params.get("locations", "")
            locations = [loc.strip() for loc in locations_str.split(",") if loc.strip()] if locations_str else None
            categories_str = source.params.get("categories", "")
            categories = [c.strip() for c in categories_str.split(",") if c.strip()] if categories_str else None
            limit = source.params.get("limit", 25)

            with httpx.Client(timeout=15.0) as cb_client:
                companies = fetch_companies(source, cb_client, locations=locations, categories=categories, limit=limit)
            for c in companies:
                profile = CompanyProfile(
                    name=c.name,
                    slug=c.permalink,
                    website=c.website_url,
                    description=c.short_description,
                    tags=[cat.lower() for cat in c.categories[:5]],
                    source_url=c.source_url,
                    source_name=source.name,
                )
                if c.headquarters_location:
                    profile.city = c.headquarters_location
                if c.founded_on:
                    profile.founded_date = c.founded_on
                all_profiles.append(profile)
                provenance.track(
                    source_url=c.source_url,
                    source_name=source.name,
                    extraction_method="api",
                )
            continue

        if "linkedin" in source.name:
            # LinkedIn company discovery — converts LinkedInCompany to CompanyProfile
            from apps.agents.sources.linkedin import fetch_linkedin_companies

            query = source.params.get("query", "")
            limit = source.params.get("limit", 10)
            with httpx.Client(timeout=15.0) as li_client:
                companies = fetch_linkedin_companies(source, li_client, query=query, limit=limit)
            for c in companies:
                profile = CompanyProfile(
                    name=c.name,
                    slug=c.name.lower().replace(" ", "-"),
                    website=c.website,
                    description=c.description,
                    sector=c.industry,
                    linkedin_url=c.url,
                    source_url=c.url,
                    source_name=source.name,
                )
                if c.headquarters:
                    parts = c.headquarters.split(", ", 1)
                    profile.city = parts[0]
                    if len(parts) > 1:
                        profile.country = parts[1]
                all_profiles.append(profile)
                provenance.track(
                    source_url=c.url,
                    source_name=source.name,
                    extraction_method="api",
                )
            continue

        logger.info("Collecting from source: %s (%s)", source.name, source.source_type)

        if source.source_type == "api":
            if "github" in source.name:
                profiles = collect_from_github(source, provenance)
            elif "dealroom" in source.name:
                profiles = collect_from_dealroom(source, provenance)
            else:
                logger.warning("Unknown API source: %s", source.name)
                continue

            all_profiles.extend(profiles)

    logger.info(
        "Total company profiles collected: %d from %d sources",
        len(all_profiles),
        len([s for s in sources if s.enabled]),
    )

    return all_profiles


def collect_market_trends(
    sources: list[DataSourceConfig],
) -> list:
    """Collect Google Trends data for market context.

    Returns GoogleTrendItem list for use by synthesizer/writer.
    Separate from CompanyProfile collection pipeline.
    """
    from apps.agents.sources.google_trends import fetch_related_queries

    all_items: list = []
    for source in sources:
        if "gtrends" not in source.name or not source.enabled:
            continue

        keywords_str = source.params.get("keywords", "")
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        region = source.params.get("region", "BR")

        items = fetch_related_queries(source, keywords=keywords, region=region)
        all_items.extend(items)

    logger.info("Collected %d market trend signals", len(all_items))
    return all_items


def enrich_from_gupy(
    profiles: list[CompanyProfile],
    source: DataSourceConfig,
) -> list[CompanyProfile]:
    """Enrich company tech_stack using Gupy job listings.

    Uses profile slugs as Gupy company slugs. Profiles without a Gupy
    match keep their existing tech_stack unchanged.

    Args:
        profiles: List of CompanyProfile objects to enrich.
        source: DataSourceConfig for Gupy (used for provenance metadata).

    Returns:
        List of CompanyProfile objects with enriched tech_stack where available.
    """
    if not profiles:
        return profiles

    max_slugs = source.params.get("max_slugs", 20)
    slugs = [p.slug for p in profiles if p.slug][:max_slugs]

    if not slugs:
        return profiles

    try:
        from apps.agents.sources.gupy_jobs import fetch_gupy_jobs

        with httpx.Client(timeout=15.0) as gupy_client:
            jobs = fetch_gupy_jobs(source, gupy_client, company_slugs=slugs)
    except Exception as e:
        logger.warning("Gupy enrichment failed (graceful degradation): %s", e)
        return profiles

    # Build slug -> tech_stack mapping from jobs
    slug_tech: dict[str, set[str]] = {}
    for job in jobs:
        if job.tech_stack:
            slug_tech.setdefault(job.company_slug, set()).update(job.tech_stack)

    # Merge tech stacks into profiles
    for profile in profiles:
        if profile.slug in slug_tech:
            existing = set(profile.tech_stack)
            merged = list(existing | slug_tech[profile.slug])
            profile.tech_stack = sorted(merged)

    logger.info(
        "Gupy enrichment: %d/%d profiles got tech_stack updates",
        sum(1 for p in profiles if p.slug in slug_tech),
        len(profiles),
    )
    return profiles
