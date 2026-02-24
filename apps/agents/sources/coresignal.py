"""CoreSignal company data collector for LATAM companies.

Fetches B2B company data via the CoreSignal REST API, which provides
LinkedIn-sourced company profiles. The flow is two-step:

1. Search (POST) -- returns list of company IDs matching filters (max 1000 per query).
2. Collect (GET) -- returns full company data for each ID.

Data source: CoreSignal Company Database API (cdapi/v2/company_base)
Confidence: 0.8 (LinkedIn-sourced, large coverage, API-verified).

API docs: https://docs.coresignal.com/
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

CORESIGNAL_SEARCH_URL = (
    "https://api.coresignal.com/cdapi/v2/company_base/search/filter"
)
CORESIGNAL_COLLECT_URL = (
    "https://api.coresignal.com/cdapi/v2/company_base/collect"
)
DEFAULT_CONFIDENCE = 0.8
COLLECT_DELAY_SECONDS = 0.5

# Tech/startup-relevant industries on CoreSignal (LinkedIn industry names).
# Searched per country to focus on startup-like companies.
TECH_INDUSTRIES: List[str] = [
    "Computer Software",
    "Internet",
    "Financial Services",
    "Information Technology & Services",
]

# LATAM countries as CoreSignal search filter strings.
# Each entry is a single-country filter value for the "country" field.
LATAM_COUNTRIES: List[str] = [
    "Brazil",
    "Mexico",
    "Argentina",
    "Colombia",
    "Chile",
    "Peru",
    "Uruguay",
    "Ecuador",
    "Bolivia",
    "Paraguay",
    "Venezuela",
    "Costa Rica",
    "Panama",
    "Guatemala",
    "Honduras",
    "El Salvador",
    "Dominican Republic",
    "Cuba",
    "Nicaragua",
    "Puerto Rico",
]


@dataclass
class CoreSignalCompany:
    """A company from the CoreSignal Company Database API."""

    name: str
    slug: str
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    employees_count: Optional[int] = None
    founded_year: Optional[int] = None
    linkedin_url: Optional[str] = None
    logo_url: Optional[str] = None
    company_type: Optional[str] = None
    source_url: str = ""
    coresignal_id: int = 0


def _build_search_filters(
    country: str,
    industry: Optional[str] = None,
    employees_count_gte: Optional[int] = None,
    employees_count_lte: Optional[int] = None,
    founded_year_gte: Optional[int] = None,
    founded_year_lte: Optional[int] = None,
) -> Dict:
    """Build a CoreSignal search filter payload.

    Args:
        country: Country filter string (e.g., "Brazil").
        industry: Industry filter string (e.g., "Information Technology").
        employees_count_gte: Minimum number of employees.
        employees_count_lte: Maximum number of employees.
        founded_year_gte: Minimum founding year.
        founded_year_lte: Maximum founding year.

    Returns:
        Dict suitable for JSON POST body.
    """
    filters: Dict = {
        "country": f"({country})",
    }

    if industry:
        filters["industry"] = f"({industry})"

    if employees_count_gte is not None:
        filters["employees_count_gte"] = employees_count_gte

    if employees_count_lte is not None:
        filters["employees_count_lte"] = employees_count_lte

    if founded_year_gte is not None:
        filters["founded_year_gte"] = founded_year_gte

    if founded_year_lte is not None:
        filters["founded_year_lte"] = founded_year_lte

    return filters


def search_companies(
    client: httpx.Client,
    api_key: str,
    country: str,
    industry: Optional[str] = None,
    employees_count_gte: Optional[int] = None,
    employees_count_lte: Optional[int] = None,
    founded_year_gte: Optional[int] = None,
    founded_year_lte: Optional[int] = None,
) -> List[int]:
    """Search CoreSignal for company IDs matching the given filters.

    Args:
        client: Pre-configured httpx.Client (caller manages lifecycle).
        api_key: CoreSignal API key.
        country: Country filter string (e.g., "Brazil").
        industry: Industry filter string (e.g., "Information Technology").
        employees_count_gte: Minimum number of employees.
        employees_count_lte: Maximum number of employees.
        founded_year_gte: Minimum founding year.
        founded_year_lte: Maximum founding year.

    Returns:
        List of integer company IDs. Empty list on error.
    """
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
    }

    filters = _build_search_filters(
        country=country,
        industry=industry,
        employees_count_gte=employees_count_gte,
        employees_count_lte=employees_count_lte,
        founded_year_gte=founded_year_gte,
        founded_year_lte=founded_year_lte,
    )

    try:
        response = client.post(
            CORESIGNAL_SEARCH_URL,
            headers=headers,
            json=filters,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        logger.error(
            "Timeout searching CoreSignal for country=%s", country
        )
        return []
    except httpx.HTTPError as e:
        logger.error(
            "HTTP error searching CoreSignal for country=%s: %s",
            country,
            e,
        )
        return []
    except Exception as e:
        logger.error(
            "Error searching CoreSignal for country=%s: %s", country, e
        )
        return []

    if not isinstance(data, list):
        logger.warning(
            "CoreSignal search returned non-list response for country=%s: %s",
            country,
            type(data).__name__,
        )
        return []

    # Filter to valid integers only
    ids = [item for item in data if isinstance(item, int)]

    logger.info(
        "CoreSignal search: %d IDs for country=%s", len(ids), country
    )
    return ids


def _parse_city(address: Optional[str]) -> Optional[str]:
    """Extract city from CoreSignal headquarters_new_address.

    The address field is typically "City, State" or "City, State, Country".

    Args:
        address: Raw address string from API.

    Returns:
        City name or None if address is empty/missing.
    """
    if not address:
        return None
    parts = [p.strip() for p in address.split(",")]
    return parts[0] if parts else None


def _parse_company(data: Dict, company_id: int) -> CoreSignalCompany:
    """Parse a CoreSignal API response into a CoreSignalCompany.

    Args:
        data: Raw JSON dict from the collect endpoint.
        company_id: The CoreSignal company ID used in the collect request.

    Returns:
        CoreSignalCompany dataclass instance.
    """
    name = (data.get("name") or "").strip()
    slug = (data.get("company_shorthand_name") or "").strip()
    if not slug and name:
        slug = name.lower().replace(" ", "-")

    # Truncate very long descriptions
    raw_description = (data.get("description") or "").strip()
    description: Optional[str] = raw_description or None
    if description and len(description) > 1000:
        description = description[:997] + "..."

    city = _parse_city(data.get("headquarters_new_address"))

    website = (data.get("website") or "").strip() or None
    industry = (data.get("industry") or "").strip() or None
    country = (data.get("headquarters_country_parsed") or "").strip() or None
    linkedin_url = (data.get("linkedin_url") or data.get("url") or "").strip() or None
    logo_url = (data.get("logo_url") or "").strip() or None
    company_type = (data.get("type") or "").strip() or None

    # source_url is the collect endpoint URL for this company
    source_url = f"{CORESIGNAL_COLLECT_URL}/{company_id}"

    return CoreSignalCompany(
        name=name,
        slug=slug,
        website=website,
        description=description,
        industry=industry,
        country=country,
        city=city,
        employees_count=data.get("employees_count"),
        founded_year=data.get("founded"),
        linkedin_url=linkedin_url,
        logo_url=logo_url,
        company_type=company_type,
        source_url=source_url,
        coresignal_id=data.get("id", 0),
    )


def collect_company(
    client: httpx.Client,
    api_key: str,
    company_id: int,
) -> Optional[CoreSignalCompany]:
    """Fetch full data for a single company from CoreSignal.

    Args:
        client: Pre-configured httpx.Client (caller manages lifecycle).
        api_key: CoreSignal API key.
        company_id: CoreSignal company ID.

    Returns:
        CoreSignalCompany or None on error (404, timeout, deleted, etc.).
    """
    headers = {"apikey": api_key}
    url = f"{CORESIGNAL_COLLECT_URL}/{company_id}"

    try:
        response = client.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        logger.error(
            "Timeout collecting CoreSignal company id=%d", company_id
        )
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(
                "CoreSignal company id=%d not found (404)", company_id
            )
        else:
            logger.error(
                "HTTP %d collecting CoreSignal company id=%d: %s",
                e.response.status_code,
                company_id,
                e,
            )
        return None
    except httpx.HTTPError as e:
        logger.error(
            "HTTP error collecting CoreSignal company id=%d: %s",
            company_id,
            e,
        )
        return None
    except Exception as e:
        logger.error(
            "Error collecting CoreSignal company id=%d: %s",
            company_id,
            e,
        )
        return None

    if not isinstance(data, dict):
        logger.warning(
            "CoreSignal collect returned non-dict for id=%d", company_id
        )
        return None

    # Skip deleted companies
    if data.get("deleted") == 1:
        logger.info(
            "CoreSignal company id=%d is deleted, skipping", company_id
        )
        return None

    company = _parse_company(data, company_id)
    if not company.name:
        logger.warning(
            "CoreSignal company id=%d has no name, skipping", company_id
        )
        return None

    return company


def fetch_coresignal_companies(
    source: DataSourceConfig,
    client: httpx.Client,
    max_collect: int = 200,
) -> List[CoreSignalCompany]:
    """Fetch LATAM companies from CoreSignal API.

    Runs search queries per LATAM country to build a deduplicated set of
    company IDs, then collects full data for up to ``max_collect`` companies.

    Adds a 0.5s delay between collect calls to respect rate limits.

    Args:
        source: Data source configuration (used for provenance).
        client: Pre-configured httpx.Client (caller manages lifecycle).
        max_collect: Maximum number of companies to collect full data for.
            Controls API credit usage.

    Returns:
        List of CoreSignalCompany objects. Empty list when the API key is
        missing, on errors, or when no results are found.
    """
    api_key = os.getenv("CORESIGNAL_API_KEY")
    if not api_key:
        logger.warning(
            "CORESIGNAL_API_KEY not set, skipping CoreSignal for %s",
            source.name,
        )
        return []

    # Phase 1: Search across LATAM countries x tech industries, deduplicating IDs.
    # Uses founded_year_gte=2010 and employees_count_lte=500 to focus on startups.
    all_ids: Set[int] = set()

    for country in LATAM_COUNTRIES:
        for industry in TECH_INDUSTRIES:
            ids = search_companies(
                client=client,
                api_key=api_key,
                country=country,
                industry=industry,
                founded_year_gte=2010,
                employees_count_lte=500,
            )
            all_ids.update(ids)

    if not all_ids:
        logger.info("CoreSignal: no company IDs found across LATAM searches")
        return []

    logger.info(
        "CoreSignal: %d unique IDs across %d country searches",
        len(all_ids),
        len(LATAM_COUNTRIES),
    )

    # Phase 2: Collect full data, up to max_collect.
    # Sort descending so newest companies (higher IDs) are collected first —
    # older IDs are more likely to be deleted/stale.
    ids_to_collect = sorted(all_ids, reverse=True)[:max_collect]
    companies: List[CoreSignalCompany] = []

    for i, company_id in enumerate(ids_to_collect):
        company = collect_company(client, api_key, company_id)
        if company:
            companies.append(company)

        # Rate limiting: delay between calls (skip after last call)
        if i < len(ids_to_collect) - 1:
            time.sleep(COLLECT_DELAY_SECONDS)

    logger.info(
        "CoreSignal: collected %d companies out of %d IDs (max_collect=%d)",
        len(companies),
        len(all_ids),
        max_collect,
    )
    return companies
