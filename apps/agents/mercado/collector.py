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


# --- Blocklist patterns by category (matched as substrings, case-insensitive) ---

_GOVT_PATTERNS = [
    "prefeitura", "governo", "gov-", "gobierno",
    "ministerio", "municipio",
]

_UNIVERSITY_PATTERNS = [
    "universid", "university",
    "faculdade", "faculdad",
    "fatec", "fiap", "espm", "puc-",
    "politecnic", "politecn",
    "instituto-", "itesm", "unam", "unicamp",
    "ufmg", "ufrj", "ufpr", "ufsc", "ufrgs",
    "uniandes", "javeriana",
]

_EDUCATION_PATTERNS = [
    "escola", "school", "college", "colegio",
    "curso", "treinaweb", "alura", "platzi",
    "bootcamp", "academia-",
]

_ACADEMIC_PATTERNS = [
    "-lab", "research-",
    "capitulo", "chapter", "-acm",
    "gamedev", "thunderatz",
]

_NONPROFIT_PATTERNS = [
    "bireme", "paho", "opas",
    "-ngo", "ong-", "fundacion", "fundacao",
    "opendesign",
]

_PERSONAL_PATTERNS = [
    "-eti", "consulting", "consultoria",
]

_KNOWN_LARGE_COMPANIES_PATTERNS = [
    "globo", "globocom",
    "wizeline",
    "mercadolibre", "mercadolivre",
    "despegar", "decolar",
    "totvs",
    "b2w-", "americanas",
    "embraer",
]

_ARCHIVE_PATTERNS = [
    "archive", "mirror", "backup",
]

# Combined substring blocklist (tuple for faster iteration)
_NON_STARTUP_PATTERNS = tuple(
    _GOVT_PATTERNS
    + _UNIVERSITY_PATTERNS
    + _EDUCATION_PATTERNS
    + _ACADEMIC_PATTERNS
    + _NONPROFIT_PATTERNS
    + _PERSONAL_PATTERNS
    + _KNOWN_LARGE_COMPANIES_PATTERNS
    + _ARCHIVE_PATTERNS
)

# Exact-login blocklist for short names that would cause false-positive
# substring matches (e.g., "vtex" is too short for safe substring matching).
_KNOWN_NON_STARTUP_LOGINS = frozenset([
    "vtex", "vtex-apps",
    "globocom", "globo",
    "wizeline",
    "mercadolibre", "mercadolivre",
    "totvs",
    "udistrital",
    "bireme",
    "hacklabr",
    "geosaber",
    "uspgamedev",
    "thesoftwaredesignlab",
    "capitulojaverianoacm",
    "thunderatz",
    "openingdesign",
])


def is_likely_startup(org_login: str, description: str = "") -> bool:
    """Check if a GitHub org is likely a startup vs an institution.

    Uses two checks in order:
    1. Exact login match against ``_KNOWN_NON_STARTUP_LOGINS``.
    2. Substring match of login+description against ``_NON_STARTUP_PATTERNS``.

    Examples:
        >>> is_likely_startup("nubank")
        True
        >>> is_likely_startup("prefeiturasp", "Prefeitura de São Paulo")
        False
        >>> is_likely_startup("vtex", "")
        False

    Args:
        org_login: GitHub organization login handle (e.g., ``"nubank"``).
        description: Organization description from GitHub API (may be empty
            or None-like; defaults to ``""``).

    Returns:
        True if the org passes all checks (likely a startup).
        False if any check rejects it.
    """
    login_lower = org_login.lower()

    # Check 1: exact login blocklist
    if login_lower in _KNOWN_NON_STARTUP_LOGINS:
        return False

    # Check 2: substring pattern matching
    text = (login_lower + " " + (description or "")).lower()
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
