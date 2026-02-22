"""Y Combinator portfolio collector for LATAM companies.

Fetches YC companies from the public directory and filters for LATAM region.
Returns structured data for the INDEX agent pipeline.

Data source: https://www.ycombinator.com/companies
Confidence: 0.85 (well-known accelerator, verified data).
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

YC_COMPANIES_URL = "https://www.ycombinator.com/companies"
DEFAULT_CONFIDENCE = 0.85

# LATAM countries for filtering
LATAM_COUNTRIES: set[str] = {
    "Brazil", "Brasil",
    "Mexico", "México",
    "Argentina",
    "Colombia",
    "Chile",
    "Peru", "Perú",
    "Uruguay",
    "Ecuador",
    "Bolivia",
    "Paraguay",
    "Venezuela",
    "Costa Rica",
    "Panama", "Panamá",
    "Guatemala",
    "Honduras",
    "El Salvador",
    "Dominican Republic", "República Dominicana",
    "Cuba",
    "Nicaragua",
    "Puerto Rico",
}

# LATAM cities commonly listed without country
LATAM_CITIES: set[str] = {
    "São Paulo", "Sao Paulo",
    "Rio de Janeiro",
    "Mexico City", "Ciudad de México",
    "Buenos Aires",
    "Bogotá", "Bogota",
    "Santiago",
    "Lima",
    "Montevideo",
    "Medellín", "Medellin",
    "Guadalajara",
    "Curitiba",
    "Belo Horizonte",
    "Porto Alegre",
    "Florianópolis", "Florianopolis",
    "Campinas",
    "Recife",
    "Quito",
    "La Paz",
}


@dataclass
class YCCompany:
    """A company from Y Combinator's portfolio."""

    name: str
    slug: str
    batch: str = ""  # e.g., "W24", "S23"
    vertical: str = ""
    city: str = ""
    country: str = ""
    region: str = ""
    website: str = ""
    description: str = ""
    status: str = "Active"
    source_url: str = ""
    team_size: Optional[int] = None


def _is_latam_location(
    country: str = "",
    city: str = "",
    region: str = "",
) -> bool:
    """Check if a company's location is in LATAM.

    Checks country first, then city as a fallback for entries
    that list city without country.

    Args:
        country: Company country.
        city: Company city.
        region: Company region string.

    Returns:
        True if the company is based in LATAM.
    """
    # Check country
    if country:
        for latam_country in LATAM_COUNTRIES:
            if latam_country.lower() in country.lower():
                return True

    # Check region
    if region:
        region_lower = region.lower()
        if any(term in region_lower for term in ["latin america", "south america", "latam"]):
            return True

    # Check city as fallback
    if city:
        for latam_city in LATAM_CITIES:
            if latam_city.lower() in city.lower():
                return True

    return False


def fetch_yc_companies(
    source: DataSourceConfig,
    client: httpx.Client,
) -> list[YCCompany]:
    """Fetch YC companies from the public API/directory.

    Args:
        source: Data source configuration.
        client: HTTP client.

    Returns:
        List of YCCompany objects.
    """
    url = source.url or YC_COMPANIES_URL

    try:
        response = client.get(
            url,
            headers={"Accept": "application/json"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        logger.error("Timeout fetching YC companies")
        return []
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching YC companies: %s", e)
        return []
    except Exception as e:
        logger.error("Error fetching YC companies: %s", e)
        return []

    # Handle various response formats
    items = data if isinstance(data, list) else data.get("companies", data.get("results", data.get("hits", [])))

    companies: list[YCCompany] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name", "").strip()
        if not name:
            continue

        slug = item.get("slug", name.lower().replace(" ", "-"))

        company = YCCompany(
            name=name,
            slug=slug,
            batch=item.get("batch", item.get("batch_name", "")),
            vertical=item.get("vertical", item.get("industry", item.get("top_company_keyword", ""))),
            city=item.get("city", item.get("location", "")),
            country=item.get("country", ""),
            region=item.get("region", ""),
            website=item.get("website", item.get("url", "")),
            description=item.get("one_liner", item.get("description", item.get("long_description", ""))),
            status=item.get("status", "Active"),
            source_url=f"https://www.ycombinator.com/companies/{slug}",
            team_size=item.get("team_size"),
        )
        companies.append(company)

    logger.info("YC companies fetched: %d total", len(companies))
    return companies


def filter_latam(companies: list[YCCompany]) -> list[YCCompany]:
    """Filter YC companies to only LATAM-based ones.

    Args:
        companies: List of all YC companies.

    Returns:
        Filtered list of LATAM companies only.
    """
    latam = [
        c for c in companies
        if _is_latam_location(country=c.country, city=c.city, region=c.region)
    ]

    logger.info(
        "YC LATAM filter: %d total -> %d LATAM companies",
        len(companies),
        len(latam),
    )

    return latam
