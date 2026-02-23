"""Company profile enrichment for MERCADO agent.

Enriches company profiles with additional data from websites, WHOIS, GitHub orgs.

GitHub org enrichment is delegated to the shared
``apps.agents.sources.github_orgs`` module. This module re-exports
``enrich_from_github_org`` for backward compatibility.
"""

import logging
import time

from apps.agents.sources.github_orgs import CompanyProfile

# Re-export from shared module for backward compatibility.
from apps.agents.sources.github_orgs import enrich_from_github_org  # noqa: F401

logger = logging.getLogger(__name__)


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

    Includes rate limiting (100ms sleep between profiles) to avoid
    hitting GitHub API rate limits during org enrichment.

    Args:
        profiles: List of CompanyProfile objects to enrich

    Returns:
        List of enriched CompanyProfile objects
    """
    enriched = []

    for i, profile in enumerate(profiles):
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

        # Rate limiting between GitHub org API calls
        if i < len(profiles) - 1 and profile.github_url:
            time.sleep(0.1)

    logger.info("Enriched %d/%d profiles", len(enriched), len(profiles))
    return enriched
