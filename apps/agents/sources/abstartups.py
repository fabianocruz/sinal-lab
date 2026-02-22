"""ABStartups StartupBase collector.

Collects startup data from ABStartups (Associação Brasileira de Startups)
public API. Returns structured company data with Brazilian startup focus.

Data source: https://startupbase.com.br
Confidence: 0.7 (industry association data, self-reported).
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

ABSTARTUPS_BASE_URL = "https://startupbase.com.br/api/v1"
DEFAULT_CONFIDENCE = 0.7


@dataclass
class ABStartupsCompany:
    """A company record from ABStartups StartupBase."""

    name: str
    slug: str
    sector: str = ""
    city: str = ""
    state: str = ""
    website: str = ""
    business_model: str = ""
    description: str = ""
    source_url: str = ""


def fetch_abstartups(
    source: DataSourceConfig,
    client: httpx.Client,
    page: int = 1,
    per_page: int = 50,
) -> list[ABStartupsCompany]:
    """Fetch a single page of startups from ABStartups API.

    Args:
        source: Data source configuration.
        client: HTTP client for making requests.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        List of ABStartupsCompany objects.
    """
    url = source.url or f"{ABSTARTUPS_BASE_URL}/startups"

    try:
        response = client.get(
            url,
            params={"page": page, "per_page": per_page},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        logger.error("Timeout fetching ABStartups page %d", page)
        return []
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching ABStartups page %d: %s", page, e)
        return []
    except Exception as e:
        logger.error("Error fetching ABStartups page %d: %s", page, e)
        return []

    # Handle both list and paginated response formats
    items = data if isinstance(data, list) else data.get("results", data.get("data", []))

    companies: list[ABStartupsCompany] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name", "").strip()
        if not name:
            continue

        slug = item.get("slug", name.lower().replace(" ", "-"))

        company = ABStartupsCompany(
            name=name,
            slug=slug,
            sector=item.get("sector", item.get("vertical", "")),
            city=item.get("city", ""),
            state=item.get("state", item.get("uf", "")),
            website=item.get("website", item.get("url", "")),
            business_model=item.get("business_model", item.get("modelo_negocio", "")),
            description=item.get("description", item.get("descricao", "")),
            source_url=f"https://startupbase.com.br/startup/{slug}",
        )
        companies.append(company)

    logger.info("ABStartups page %d: %d startups fetched", page, len(companies))
    return companies


def fetch_all_abstartups(
    source: DataSourceConfig,
    client: httpx.Client,
    max_pages: int = 10,
    per_page: int = 50,
) -> list[ABStartupsCompany]:
    """Fetch all startups from ABStartups with auto-pagination.

    Stops when an empty page is returned or max_pages is reached.

    Args:
        source: Data source configuration.
        client: HTTP client.
        max_pages: Maximum pages to fetch.
        per_page: Items per page.

    Returns:
        Combined list of all ABStartupsCompany objects.
    """
    all_companies: list[ABStartupsCompany] = []

    for page in range(1, max_pages + 1):
        companies = fetch_abstartups(source, client, page=page, per_page=per_page)

        if not companies:
            logger.info("ABStartups: empty page %d, stopping pagination", page)
            break

        all_companies.extend(companies)

        if len(companies) < per_page:
            logger.info("ABStartups: partial page %d (%d items), stopping", page, len(companies))
            break

    logger.info("ABStartups total: %d startups fetched", len(all_companies))
    return all_companies
