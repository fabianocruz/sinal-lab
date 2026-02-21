"""Company profile enrichment for MERCADO agent.

Enriches company profiles with additional data from websites, WHOIS, GitHub orgs.
"""

import logging
import os
import time
from datetime import date

import httpx

from apps.agents.mercado.collector import CompanyProfile

logger = logging.getLogger(__name__)


def enrich_from_github_org(profile: CompanyProfile) -> CompanyProfile:
    """Enrich profile with GitHub organization data.

    Calls /orgs/{login} to get blog (website), description, name,
    created_at (founding date), and public_repos count.

    Args:
        profile: CompanyProfile to enrich

    Returns:
        Enriched CompanyProfile with GitHub org data
    """
    if not profile.github_url or not profile.slug:
        return profile

    org_login = profile.slug
    url = f"https://api.github.com/orgs/{org_login}"

    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        response = httpx.get(url, headers=headers, timeout=15.0)
        if response.status_code == 404:
            logger.debug("GitHub org not found: %s", org_login)
            return profile
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        logger.warning("Failed to enrich %s from GitHub: %s", org_login, e)
        return profile

    # Enrich website from blog field
    blog = data.get("blog")
    if blog and not profile.website:
        if not blog.startswith(("http://", "https://")):
            blog = "https://" + blog
        profile.website = blog

    # Enrich description (prefer longer)
    api_description = data.get("description") or ""
    if len(api_description) > len(profile.description or ""):
        profile.description = api_description

    # Enrich human-readable name
    api_name = data.get("name")
    if api_name and api_name != org_login:
        profile.name = api_name

    # Enrich founding date from org creation date
    created_at = data.get("created_at")
    if created_at and not profile.founded_date:
        try:
            profile.founded_date = date.fromisoformat(created_at[:10])
        except ValueError:
            pass

    # Store public_repos count as metadata tag
    public_repos = data.get("public_repos", 0)
    if public_repos > 0:
        profile.tags = list(set(profile.tags + [f"repos:{public_repos}"]))

    logger.debug(
        "Enriched %s: website=%s, description_len=%d, repos=%d",
        org_login, profile.website, len(profile.description or ""), public_repos,
    )
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
