"""Company profile enrichment for MERCADO agent.

Enriches company profiles with additional data from websites, WHOIS, GitHub orgs.
"""

import logging
from typing import Optional

from apps.agents.mercado.collector import CompanyProfile

logger = logging.getLogger(__name__)


def enrich_from_github_org(profile: CompanyProfile) -> CompanyProfile:
    """Enrich profile with GitHub organization data.

    Args:
        profile: CompanyProfile to enrich

    Returns:
        Enriched CompanyProfile with GitHub org data
    """
    if not profile.github_url:
        return profile

    # TODO: Implement GitHub org API calls
    # - Fetch org details (blog/website, location, public_repos count)
    # - Analyze top repos for main languages (tech_stack)
    # - Estimate team_size from contributor count

    logger.debug("GitHub org enrichment not yet implemented for %s", profile.name)
    return profile


def enrich_from_website(profile: CompanyProfile) -> CompanyProfile:
    """Enrich profile by scraping company website.

    Args:
        profile: CompanyProfile to enrich

    Returns:
        Enriched CompanyProfile with website data
    """
    if not profile.website:
        return profile

    # TODO: Implement website scraping
    # - Extract full description from About page
    # - Extract team size from Careers page
    # - Extract tech stack from job listings
    # - Extract LinkedIn URL from footer

    logger.debug("Website enrichment not yet implemented for %s", profile.name)
    return profile


def enrich_from_whois(profile: CompanyProfile) -> CompanyProfile:
    """Enrich profile with WHOIS domain data.

    Args:
        profile: CompanyProfile to enrich

    Returns:
        Enriched CompanyProfile with WHOIS data (founded_date estimate)
    """
    if not profile.website:
        return profile

    # TODO: Implement WHOIS lookup
    # - Extract domain creation date → founded_date estimate

    logger.debug("WHOIS enrichment not yet implemented for %s", profile.name)
    return profile


def enrich_profile(profile: CompanyProfile) -> CompanyProfile:
    """Enrich a company profile with all available sources.

    Args:
        profile: CompanyProfile to enrich

    Returns:
        Fully enriched CompanyProfile
    """
    profile = enrich_from_github_org(profile)
    profile = enrich_from_website(profile)
    profile = enrich_from_whois(profile)

    return profile


def enrich_all_profiles(profiles: list[CompanyProfile]) -> list[CompanyProfile]:
    """Enrich all company profiles.

    Args:
        profiles: List of CompanyProfile objects to enrich

    Returns:
        List of enriched CompanyProfile objects
    """
    enriched = []

    for profile in profiles:
        try:
            enriched_profile = enrich_profile(profile)
            enriched.append(enriched_profile)
        except Exception as e:
            logger.error(
                "Failed to enrich profile for %s: %s",
                profile.name,
                e,
                exc_info=True,
            )
            # Keep original profile if enrichment fails
            enriched.append(profile)

    logger.info("Enriched %d/%d profiles", len(enriched), len(profiles))
    return enriched
