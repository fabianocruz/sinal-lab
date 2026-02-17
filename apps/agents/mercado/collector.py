"""Data collection for MERCADO agent.

Collects company profiles from GitHub, Dealroom API, and other sources.
"""

import logging
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


def collect_from_github(
    source: DataSourceConfig,
    provenance: ProvenanceTracker,
) -> list[CompanyProfile]:
    """Collect company profiles from GitHub Search API.

    Args:
        source: GitHub API data source configuration
        provenance: Provenance tracker for source recording

    Returns:
        List of CompanyProfile objects discovered from GitHub
    """
    profiles: list[CompanyProfile] = []

    try:
        headers = {"Accept": "application/vnd.github+json"}
        # Add GitHub token if available (optional, increases rate limit)
        # token = os.getenv("GITHUB_TOKEN")
        # if token:
        #     headers["Authorization"] = f"token {token}"

        response = httpx.get(
            source.url,
            params=source.params,
            headers=headers,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()

        logger.info(
            "GitHub API returned %d repositories from %s",
            data.get("total_count", 0),
            source.name,
        )

        for repo in data.get("items", []):
            # Extract organization or owner
            owner = repo.get("owner", {})
            owner_name = owner.get("login", "")
            owner_url = owner.get("html_url", "")

            # Only process organization accounts (not personal repos)
            if owner.get("type") != "Organization":
                continue

            # Extract location from repo
            # GitHub doesn't provide org location in repo search, so we use query location
            location = source.params.get("q", "")
            city = None
            country = "Brasil"

            if "São+Paulo" in location or "Sao+Paulo" in location:
                city = "São Paulo"
                country = "Brasil"
            elif "Rio+de+Janeiro" in location:
                city = "Rio de Janeiro"
                country = "Brasil"
            elif "Mexico+City" in location:
                city = "Mexico City"
                country = "Mexico"
            elif "Buenos+Aires" in location:
                city = "Buenos Aires"
                country = "Argentina"
            elif "Bogotá" in location or "Bogota" in location:
                city = "Bogotá"
                country = "Colombia"

            # Extract tech stack from primary language
            tech_stack = []
            if repo.get("language"):
                tech_stack.append(repo["language"])

            profile = CompanyProfile(
                name=owner_name,
                slug=owner_name.lower().replace(" ", "-"),
                website=None,  # Will be enriched later
                description=repo.get("description", ""),
                sector=None,  # Will be classified later
                city=city,
                country=country,
                github_url=owner_url,
                tech_stack=tech_stack,
                source_url=repo.get("html_url", ""),
                source_name=source.name,
            )

            profiles.append(profile)

            # Track provenance
            provenance.track(
                source_url=repo.get("html_url", ""),
                source_name=source.name,
                extraction_method="api",
            )

    except httpx.TimeoutException:
        logger.error("Timeout fetching GitHub API: %s", source.name)
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching GitHub API %s: %s", source.name, e)
    except Exception as e:
        logger.error(
            "Unexpected error collecting from GitHub %s: %s",
            source.name,
            e,
            exc_info=True,
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
