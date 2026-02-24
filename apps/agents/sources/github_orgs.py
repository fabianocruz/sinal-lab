"""Shared GitHub organization collection and enrichment.

Extracts LATAM tech organizations from GitHub Search API, filters
non-startups, scores startup likelihood, and enriches profiles
with org-level metadata.

Used by both MERCADO and INDEX agents.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


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


# --- Location map (LATAM cities) ---

_LOCATION_MAP = {
    # Brasil
    "São Paulo": ("São Paulo", "Brasil"),
    "Rio de Janeiro": ("Rio de Janeiro", "Brasil"),
    "Belo Horizonte": ("Belo Horizonte", "Brasil"),
    "Curitiba": ("Curitiba", "Brasil"),
    "Porto Alegre": ("Porto Alegre", "Brasil"),
    "Florianópolis": ("Florianópolis", "Brasil"),
    "Campinas": ("Campinas", "Brasil"),
    "Recife": ("Recife", "Brasil"),
    "Brasília": ("Brasília", "Brasil"),
    "Salvador": ("Salvador", "Brasil"),
    "Fortaleza": ("Fortaleza", "Brasil"),
    "Manaus": ("Manaus", "Brasil"),
    # Mexico
    "Mexico City": ("Mexico City", "Mexico"),
    "Guadalajara": ("Guadalajara", "Mexico"),
    "Monterrey": ("Monterrey", "Mexico"),
    # Argentina
    "Buenos Aires": ("Buenos Aires", "Argentina"),
    "Córdoba": ("Córdoba", "Argentina"),
    "Rosario": ("Rosario", "Argentina"),
    # Colombia
    "Bogotá": ("Bogotá", "Colombia"),
    "Medellín": ("Medellín", "Colombia"),
    "Cali": ("Cali", "Colombia"),
    # Chile
    "Santiago": ("Santiago", "Chile"),
    # Peru
    "Lima": ("Lima", "Peru"),
    # Uruguay
    "Montevideo": ("Montevideo", "Uruguay"),
    # Ecuador
    "Quito": ("Quito", "Ecuador"),
    # Costa Rica
    "San José": ("San José", "Costa Rica"),
    # Panama
    "Panama City": ("Panama City", "Panama"),
    # Dominican Republic
    "Santo Domingo": ("Santo Domingo", "Dominican Republic"),
    # Paraguay
    "Asunción": ("Asunción", "Paraguay"),
    # Bolivia
    "La Paz": ("La Paz", "Bolivia"),
    # Puerto Rico
    "San Juan": ("San Juan", "Puerto Rico"),
}


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


# --- Positive signal keywords for startup scoring ---

POSITIVE_SIGNALS = frozenset({
    "startup", "fintech", "saas", "ai", "ml", "healthtech",
    "edtech", "agritech", "proptech", "insurtech", "logistics",
    "e-commerce", "marketplace", "platform", "app", "api",
    "cloud", "data", "analytics", "automation", "iot",
    "payments", "banking", "crypto", "blockchain", "defi",
    "devtools", "developer", "infrastructure", "security",
    "b2b", "b2c", "mobile", "web",
})


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


def score_startup_likelihood(
    login: str,
    description: str = "",
    bio: str = "",
) -> float:
    """Score 0-1 how likely a GitHub org is a startup.

    Combines blocklist rejection with positive signal matching:
    - Blocklist match -> 0.0
    - No signals -> 0.3 (neutral, unknown org)
    - Positive keywords in description/bio -> 0.3 + 0.1 per hit (max 1.0)

    Args:
        login: GitHub organization login handle.
        description: Organization description from GitHub API.
        bio: Additional bio text (from /orgs/{login} API).

    Returns:
        Float 0.0-1.0 representing startup likelihood.
    """
    # Blocklist check first
    if not is_likely_startup(login, description):
        return 0.0

    # Count positive signals in combined text
    text = f"{login} {description or ''} {bio or ''}".lower()
    hits = sum(1 for signal in POSITIVE_SIGNALS if signal in text)

    if hits == 0:
        return 0.3  # Neutral — no positive or negative signals

    # 0.3 base + 0.1 per keyword hit, capped at 1.0
    return min(1.0, 0.3 + hits * 0.1)


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
    min_startup_score: float = 0.3,
) -> list[CompanyProfile]:
    """Collect organization profiles from GitHub Search API.

    Uses /search/users with type:org to find tech organizations
    by LATAM city location.  Paginates automatically (per_page=100,
    page 1-indexed) up to the GitHub Search hard limit of 1,000
    results per query.  Stops when a partial page is returned or
    the 1,000-result ceiling is reached.

    Filters non-startups using ``score_startup_likelihood()`` with
    configurable threshold.

    Args:
        source: GitHub API data source configuration.
        provenance: Provenance tracker for source recording.
        min_startup_score: Minimum startup likelihood score (0-1) to include
            an org. Default 0.3 keeps all non-blocklisted orgs.

    Returns:
        List of CompanyProfile objects discovered from GitHub.
    """
    profiles: list[CompanyProfile] = []

    try:
        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "token {}".format(token)

        query = source.params.get("q", "")
        city, country = _resolve_location(query)
        per_page = source.params.get("per_page", 100)
        # Build base params without 'page' (added per iteration)
        base_params = {k: v for k, v in source.params.items() if k != "page"}

        page = 1
        filtered_count = 0
        _GITHUB_MAX_RESULTS = 1000  # GitHub Search API hard limit

        while True:
            params = {**base_params, "page": page}
            response = httpx.get(
                source.url,
                params=params,
                headers=headers,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

            if page == 1:
                total = data.get("total_count", 0)
                logger.info(
                    "GitHub API returned %d organizations from %s",
                    total,
                    source.name,
                )

            items = data.get("items", [])
            for org in items:
                org_login = org.get("login", "")
                org_url = org.get("html_url", "")
                description = org.get("description") or ""

                if not org_login:
                    continue

                score = score_startup_likelihood(org_login, description)
                if score < min_startup_score:
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

            # Stop conditions
            if len(items) < per_page:
                break  # Partial or empty page — last page
            if page * per_page >= _GITHUB_MAX_RESULTS:
                break  # GitHub hard limit
            page += 1

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


def enrich_from_github_org(profile: CompanyProfile) -> CompanyProfile:
    """Enrich profile with GitHub organization data.

    Calls /orgs/{login} to get blog (website), description, name,
    created_at (founding date), and public_repos count.

    Args:
        profile: CompanyProfile to enrich.

    Returns:
        Enriched CompanyProfile with GitHub org data.
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


def enrich_github_profiles(
    profiles: list[CompanyProfile],
    delay: float = 0.1,
) -> list[CompanyProfile]:
    """Enrich multiple GitHub profiles with rate limiting.

    Calls ``enrich_from_github_org()`` for each profile that has a
    github_url, sleeping between calls to avoid API rate limits.

    Args:
        profiles: List of CompanyProfile objects to enrich.
        delay: Seconds to sleep between GitHub API calls (default 0.1).

    Returns:
        List of enriched CompanyProfile objects.
    """
    enriched = []

    for i, profile in enumerate(profiles):
        try:
            enriched_profile = enrich_from_github_org(profile)
            enriched.append(enriched_profile)
        except Exception as e:
            logger.error(
                "Failed to enrich profile for %s: %s",
                profile.name, e, exc_info=True,
            )
            enriched.append(profile)

        # Rate limiting between GitHub org API calls
        if i < len(profiles) - 1 and profile.github_url:
            time.sleep(delay)

    logger.info("Enriched %d/%d GitHub profiles", len(enriched), len(profiles))
    return enriched
