"""Y Combinator portfolio collector for LATAM companies.

Fetches YC companies from the Algolia-powered public directory and
filters for LATAM region. Returns structured data for the INDEX agent.

Data source: YC Startup Directory (Algolia search index)
Confidence: 0.85 (well-known accelerator, verified data).
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

# Algolia search backend powering ycombinator.com/companies
YC_ALGOLIA_APP_ID = "45BWZJ1SGC"
YC_ALGOLIA_API_KEY = (
    "ZjA3NWMwMmNhMzEwZmMxOThkZDlkMjFmNDAwNTNjNjdkZjdhNWJkOWRjMThiODQwMjUyZTVkYjA4"
    "YjFlMmU2YnJlc3RyaWN0SW5kaWNlcz0lNUIlMjJZQ0NvbXBhbnlfcHJvZHVjdGlvbiUyMiUyQyUy"
    "MllDQ29tcGFueV9CeV9MYXVuY2hfRGF0ZV9wcm9kdWN0aW9uJTIyJTVEJnRhZ0ZpbHRlcnM9JTVC"
    "JTIyeWNkY19wdWJsaWMlMjIlNUQmYW5hbHl0aWNzVGFncz0lNUIlMjJ5Y2RjJTIyJTVE"
)
YC_ALGOLIA_INDEX = "YCCompany_production"
YC_ALGOLIA_URL = f"https://{YC_ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{YC_ALGOLIA_INDEX}/query"

# Legacy URL (kept for reference / DataSourceConfig compat)
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


def _parse_location(hit: dict) -> tuple:
    """Extract city and country from an Algolia hit.

    Algolia returns ``all_locations`` (e.g., "Bogotá, Bogota, Colombia")
    and ``regions`` (list like ["Colombia", "Latin America"]).

    Returns:
        (city, country) tuple.
    """
    # Try regions list for country
    regions = hit.get("regions") or []
    country = ""
    for r in regions:
        if r in LATAM_COUNTRIES:
            country = r
            break

    # Parse all_locations for city
    city = ""
    all_locations = hit.get("all_locations", "")
    if all_locations:
        parts = [p.strip() for p in all_locations.split(",")]
        if parts:
            city = parts[0]

    return city, country


def _hit_to_company(hit: dict) -> YCCompany:
    """Convert an Algolia hit to a YCCompany dataclass."""
    name = hit.get("name", "").strip()
    slug = hit.get("slug", name.lower().replace(" ", "-"))
    city, country = _parse_location(hit)

    # Algolia uses "industry" / "subindustry" instead of "vertical"
    vertical = hit.get("industry", hit.get("vertical", hit.get("top_company_keyword", "")))

    # regions is a list — join for the region field
    regions = hit.get("regions") or []
    region = ", ".join(regions) if regions else ""

    return YCCompany(
        name=name,
        slug=slug,
        batch=hit.get("batch", ""),
        vertical=vertical,
        city=city,
        country=country,
        region=region,
        website=hit.get("website", ""),
        description=hit.get("one_liner", hit.get("long_description", "")),
        status=hit.get("status", "Active"),
        source_url=f"https://www.ycombinator.com/companies/{slug}",
        team_size=hit.get("team_size"),
    )


def fetch_yc_companies(
    source: DataSourceConfig,
    client: httpx.Client,
) -> list[YCCompany]:
    """Fetch YC companies from the Algolia search index.

    Paginates through all results (1000 hits per page max).
    Falls back to the legacy HTML endpoint if Algolia fails.

    Args:
        source: Data source configuration.
        client: HTTP client.

    Returns:
        List of YCCompany objects.
    """
    companies = _fetch_via_algolia(client)
    if companies:
        return companies

    # Fallback: try legacy endpoint (may return JSON on some configs)
    logger.warning("Algolia failed, trying legacy endpoint")
    return _fetch_via_legacy(source, client)


def _fetch_via_algolia(
    client: httpx.Client,
    hits_per_page: int = 1000,
    latam_only: bool = True,
) -> list[YCCompany]:
    """Fetch YC companies via Algolia search API.

    Uses facetFilters to request only LATAM companies server-side,
    avoiding the 1000-hit search cap. Paginates if needed.

    Args:
        client: HTTP client.
        hits_per_page: Results per page (max 1000).
        latam_only: If True, filter for Latin America / South America regions.

    Returns:
        List of YCCompany objects.
    """
    headers = {
        "X-Algolia-Application-Id": YC_ALGOLIA_APP_ID,
        "X-Algolia-API-Key": YC_ALGOLIA_API_KEY,
        "Content-Type": "application/json",
    }

    all_companies: list[YCCompany] = []
    page = 0

    while True:
        payload = {
            "query": "",
            "hitsPerPage": hits_per_page,
            "page": page,
        }
        if latam_only:
            # OR filter: regions contains "Latin America" OR "South America"
            payload["facetFilters"] = [
                ["regions:Latin America", "regions:South America"],
            ]

        try:
            response = client.post(
                YC_ALGOLIA_URL,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            logger.error("Timeout fetching YC Algolia page %d", page)
            break
        except httpx.HTTPError as e:
            logger.error("HTTP error fetching YC Algolia page %d: %s", page, e)
            break
        except Exception as e:
            logger.error("Error fetching YC Algolia page %d: %s", page, e)
            break

        hits = data.get("hits", [])
        if not hits:
            break

        for hit in hits:
            name = hit.get("name", "").strip()
            if not name:
                continue
            all_companies.append(_hit_to_company(hit))

        nb_pages = data.get("nbPages", 1)
        page += 1
        if page >= nb_pages:
            break

    logger.info("YC Algolia: fetched %d companies across %d pages", len(all_companies), page)
    return all_companies


def _fetch_via_legacy(
    source: DataSourceConfig,
    client: httpx.Client,
) -> list[YCCompany]:
    """Fallback: fetch from the legacy HTML/JSON endpoint."""
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
        logger.error("Timeout fetching YC companies (legacy)")
        return []
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching YC companies (legacy): %s", e)
        return []
    except Exception as e:
        logger.error("Error fetching YC companies (legacy): %s", e)
        return []

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

    logger.info("YC legacy: fetched %d companies", len(companies))
    return companies


def filter_latam(companies: list[YCCompany]) -> list[YCCompany]:
    """Filter YC companies to only LATAM-based ones.

    Uses country, region, and city fields to determine LATAM presence.

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
