"""Data collection for MERCADO agent.

Collects company profiles from GitHub, Dealroom API, and other sources.

GitHub strategy: Uses the /search/users endpoint (not /search/repositories)
because GitHub's `location:` qualifier only works on user/org profiles.
The query includes `type:org` to filter for organizations (companies)
and `repos:>N` to ensure only active tech orgs are returned.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


# Map query location strings to (city, country) tuples.
# Used by _resolve_location() to derive city/country from the GitHub
# search query parameter, since the API response doesn't include location.
_LOCATION_MAP = {
    "São Paulo": ("São Paulo", "Brasil"),
    "Rio de Janeiro": ("Rio de Janeiro", "Brasil"),
    "Mexico City": ("Mexico City", "Mexico"),
    "Buenos Aires": ("Buenos Aires", "Argentina"),
    "Bogotá": ("Bogotá", "Colombia"),
}


@dataclass
class CompanyProfile:
    """Represents a discovered company profile."""

    name: str
    slug: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    city: Optional[str] = None
    country: str = "Brasil"
    founded_date: Optional[date] = None
    team_size: Optional[int] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    tech_stack: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_url: str = ""
    source_name: str = ""


# Patterns indicating non-startup organizations (matched case-insensitive).
# Universities, government, training platforms, archives, etc.
_NON_STARTUP_PATTERNS = [
    "prefeitura", "governo", "gov-",
    "universid", "university",
    "faculdade", "fatec", "fiap", "espm", "puc-",
    "escola", "school", "college",
    "curso", "treinaweb", "alura", "platzi",
    "archive",
]


def is_likely_startup(org_login: str, description: str = "") -> bool:
    """Check if a GitHub org is likely a startup vs an institution.

    Concatenates org_login and description into a single lowercase string,
    then checks for substring matches against ``_NON_STARTUP_PATTERNS``.
    A single match is enough to reject the org.

    Filtered categories:
        - Government: ``prefeitura``, ``governo``, ``gov-``
        - Universities: ``universid``, ``university``, ``faculdade``,
          ``fatec``, ``fiap``, ``espm``, ``puc-``
        - Schools: ``escola``, ``school``, ``college``
        - Training platforms: ``curso``, ``treinaweb``, ``alura``, ``platzi``
        - Archives: ``archive``

    Examples:
        >>> is_likely_startup("nubank")
        True
        >>> is_likely_startup("prefeiturasp", "Prefeitura de São Paulo")
        False
        >>> is_likely_startup("fiap", "")
        False

    Args:
        org_login: GitHub organization login handle (e.g., ``"nubank"``).
        description: Organization description from GitHub API (may be empty
            or None-like; defaults to ``""``).

    Returns:
        True if no blocklist pattern matches — the org is likely a startup
        or tech company. False if any pattern matches.
    """
    text = (org_login + " " + description).lower()
    for pattern in _NON_STARTUP_PATTERNS:
        if pattern in text:
            return False
    return True


def _format_display_name(org_login: str) -> str:
    """Convert GitHub login to a human-readable display name.

    Args:
        org_login: GitHub organization login (e.g., "stone-payments").

    Returns:
        Formatted name (e.g., "Stone Payments").
    """
    return org_login.replace("-", " ").replace("_", " ").title()


def _resolve_location(query: str) -> tuple:
    """Extract (city, country) from the GitHub search query string."""
    for loc_name, (city, country) in _LOCATION_MAP.items():
        if loc_name in query:
            return city, country
    return None, "Brasil"


def collect_from_github(
    source: DataSourceConfig,
    provenance: ProvenanceTracker,
) -> list[CompanyProfile]:
    """Collect organization profiles from GitHub Search API.

    Uses /search/users with type:org to find tech organizations
    by LATAM city location.

    Args:
        source: GitHub API data source configuration
        provenance: Provenance tracker for source recording

    Returns:
        List of CompanyProfile objects discovered from GitHub
    """
    profiles: list[CompanyProfile] = []

    try:
        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "token {}".format(token)

        response = httpx.get(
            source.url,
            params=source.params,
            headers=headers,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total_count", 0)
        logger.info(
            "GitHub API returned %d organizations from %s",
            total,
            source.name,
        )

        query = source.params.get("q", "")
        city, country = _resolve_location(query)

        filtered_count = 0
        for org in data.get("items", []):
            org_login = org.get("login", "")
            org_url = org.get("html_url", "")
            description = org.get("description") or ""

            if not org_login:
                continue

            # Filter out non-startup organizations
            if not is_likely_startup(org_login, description):
                filtered_count += 1
                continue

            profile = CompanyProfile(
                name=_format_display_name(org_login),
                slug=org_login.lower(),
                description=description,
                city=city,
                country=country,
                github_url=org_url,
                source_url=org_url,
                source_name=source.name,
            )

            profiles.append(profile)

            provenance.track(
                source_url=org_url,
                source_name=source.name,
                extraction_method="api",
            )

        if filtered_count:
            logger.info("Filtered out %d non-startup orgs from %s", filtered_count, source.name)

    except httpx.TimeoutException:
        logger.error("Timeout fetching GitHub API: %s", source.name)
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching GitHub API %s: %s", source.name, e)
    except Exception as e:
        logger.error(
            "Unexpected error collecting from GitHub %s: %s",
            source.name, e, exc_info=True,
        )

    logger.info("Collected %d company profiles from %s", len(profiles), source.name)
    return profiles


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
