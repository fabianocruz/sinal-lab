"""Shared Crunchbase source for agent collectors.

Provides both Crunchbase Basic API access and Crunchbase Open Data CSV parsing.

API mode:
    Fetches funding rounds and company profiles via the Crunchbase Basic API.
    Requires a CRUNCHBASE_API_KEY environment variable.

CSV mode:
    Parses the Crunchbase Open Data CSV export (organizations.csv).
    No API key required.

Usage:
    from apps.agents.sources.crunchbase import (
        fetch_funding_rounds,
        fetch_companies,
        fetch_crunchbase_open_data,
    )

    rounds = fetch_funding_rounds(source_config, client, limit=50)
    companies = fetch_companies(source_config, client, limit=30)
    open_data = fetch_crunchbase_open_data("/path/to/organizations.csv")
"""

from __future__ import annotations

import csv
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

CRUNCHBASE_API_BASE = "https://api.crunchbase.com/api/v4"


@dataclass
class CrunchbaseFundingRound:
    """A single funding round from the Crunchbase Basic API.

    Content hash uses the FUNDING agent dedup pattern:
    MD5 of ``"{company_name.lower().strip()}-{round_type}"``.
    """

    company_name: str
    round_type: str
    source_url: str
    source_name: str
    amount_usd: Optional[float] = None
    announced_date: Optional[date] = None
    lead_investors: List[str] = field(default_factory=list)
    num_investors: int = 0
    company_permalink: Optional[str] = None
    company_location: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            hash_key = (
                f"{self.company_name.lower().strip()}-{self.round_type}"
            )
            self.content_hash = hashlib.md5(hash_key.encode()).hexdigest()


@dataclass
class CrunchbaseCompany:
    """A company profile from the Crunchbase Basic API.

    Content hash is MD5 of the Crunchbase organization URL (source_url).
    """

    name: str
    permalink: str
    source_url: str
    source_name: str
    short_description: Optional[str] = None
    headquarters_location: Optional[str] = None
    founded_on: Optional[date] = None
    num_employees: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    total_funding_usd: Optional[float] = None
    website_url: Optional[str] = None
    last_equity_funding_type: Optional[str] = None  # Raw Crunchbase value (e.g. "series_b")
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(
                self.source_url.encode()
            ).hexdigest()


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO date string (YYYY-MM-DD) into a date object."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, AttributeError):
        return None


def fetch_funding_rounds(
    source: DataSourceConfig,
    client: httpx.Client,
    locations: Optional[List[str]] = None,
    limit: int = 25,
) -> List[CrunchbaseFundingRound]:
    """Fetch funding rounds from the Crunchbase Basic API.

    Args:
        source: DataSourceConfig with endpoint URL and provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        locations: Optional list of location names to filter by.
        limit: Maximum number of results to request from the API.

    Returns:
        List of CrunchbaseFundingRound. Empty list when the API key is
        missing, on HTTP/timeout errors, or when the response is malformed.
    """
    api_key = os.getenv("CRUNCHBASE_API_KEY")
    if not api_key:
        logger.warning(
            "CRUNCHBASE_API_KEY not set, skipping funding rounds for %s",
            source.name,
        )
        return []

    headers: Dict[str, str] = {"X-cb-user-key": api_key}

    params: Dict[str, Any] = {"limit": limit}
    if locations:
        params["location_identifiers"] = ",".join(locations)

    try:
        response = client.get(
            source.url,
            headers=headers,
            params=params,
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(
            "Crunchbase funding rounds API error for %s: %s",
            source.name,
            exc,
        )
        return []

    try:
        data = response.json()
    except Exception as exc:
        logger.warning(
            "Crunchbase funding rounds JSON decode error for %s: %s",
            source.name,
            exc,
        )
        return []

    entities = data.get("entities", [])

    rounds: List[CrunchbaseFundingRound] = []
    for entity in entities:
        props = entity.get("properties", {})

        try:
            funded_org = props.get("funded_organization_identifier", {})
            company_name = funded_org.get("value", "")
            company_permalink = funded_org.get("permalink")

            round_type = props.get("investment_type", "unknown")

            identifier = props.get("identifier", {})
            permalink = identifier.get("permalink", "")
            source_url = (
                f"https://www.crunchbase.com/funding_round/{permalink}"
            )

            money_raised = props.get("money_raised") or {}
            amount_usd: Optional[float] = None
            raw_amount = money_raised.get("value")
            if raw_amount is not None:
                amount_usd = float(raw_amount)

            announced_date = _parse_date(props.get("announced_on"))

            lead_investor_ids = props.get("lead_investor_identifiers") or []
            lead_investors = [
                inv.get("value", "")
                for inv in lead_investor_ids
                if inv.get("value")
            ]

            num_investors = props.get("num_investors", 0)

            rounds.append(
                CrunchbaseFundingRound(
                    company_name=company_name,
                    round_type=round_type,
                    source_url=source_url,
                    source_name=source.name,
                    amount_usd=amount_usd,
                    announced_date=announced_date,
                    lead_investors=lead_investors,
                    num_investors=num_investors,
                    company_permalink=company_permalink,
                )
            )
        except Exception as exc:
            logger.debug(
                "Skipping malformed Crunchbase funding round: %s", exc
            )
            continue

    logger.info(
        "Fetched %d funding rounds from %s", len(rounds), source.name
    )
    return rounds


def fetch_companies(
    source: DataSourceConfig,
    client: httpx.Client,
    locations: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    limit: int = 25,
) -> List[CrunchbaseCompany]:
    """Fetch company profiles from the Crunchbase Basic API.

    Args:
        source: DataSourceConfig with endpoint URL and provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        locations: Optional list of location names to filter by.
        categories: Optional list of category names to filter by.
        limit: Maximum number of results to request from the API.

    Returns:
        List of CrunchbaseCompany. Empty list when the API key is
        missing, on HTTP/timeout errors, or when the response is malformed.
    """
    api_key = os.getenv("CRUNCHBASE_API_KEY")
    if not api_key:
        logger.warning(
            "CRUNCHBASE_API_KEY not set, skipping companies for %s",
            source.name,
        )
        return []

    headers: Dict[str, str] = {"X-cb-user-key": api_key}

    params: Dict[str, Any] = {"limit": limit}
    if locations:
        params["location_identifiers"] = ",".join(locations)
    if categories:
        params["category_groups"] = ",".join(categories)

    try:
        response = client.get(
            source.url,
            headers=headers,
            params=params,
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(
            "Crunchbase companies API error for %s: %s",
            source.name,
            exc,
        )
        return []

    try:
        data = response.json()
    except Exception as exc:
        logger.warning(
            "Crunchbase companies JSON decode error for %s: %s",
            source.name,
            exc,
        )
        return []

    entities = data.get("entities", [])

    companies: List[CrunchbaseCompany] = []
    for entity in entities:
        props = entity.get("properties", {})

        try:
            identifier = props.get("identifier", {})
            name = identifier.get("value", "")
            permalink = identifier.get("permalink", "")

            source_url = (
                f"https://www.crunchbase.com/organization/{permalink}"
            )

            short_description = props.get("short_description") or None

            location_ids = props.get("location_identifiers") or []
            headquarters_location: Optional[str] = None
            if location_ids:
                headquarters_location = location_ids[0].get("value")

            founded_on = _parse_date(props.get("founded_on"))

            num_employees = props.get("num_employees_enum") or None

            category_groups = props.get("category_groups") or []
            categories_list = [
                cg.get("value", "")
                for cg in category_groups
                if cg.get("value")
            ]

            funding_total = props.get("funding_total") or {}
            total_funding_usd: Optional[float] = None
            raw_funding = funding_total.get("value")
            if raw_funding is not None:
                total_funding_usd = float(raw_funding)

            website_url = props.get("website_url") or None

            last_equity_funding_type = props.get("last_equity_funding_type") or None

            companies.append(
                CrunchbaseCompany(
                    name=name,
                    permalink=permalink,
                    source_url=source_url,
                    source_name=source.name,
                    short_description=short_description,
                    headquarters_location=headquarters_location,
                    founded_on=founded_on,
                    num_employees=num_employees,
                    categories=categories_list,
                    total_funding_usd=total_funding_usd,
                    website_url=website_url,
                    last_equity_funding_type=last_equity_funding_type,
                )
            )
        except Exception as exc:
            logger.debug(
                "Skipping malformed Crunchbase company: %s", exc
            )
            continue

    logger.info(
        "Fetched %d companies from %s", len(companies), source.name
    )
    return companies


# ---------------------------------------------------------------------------
# Crunchbase Open Data CSV parser
# ---------------------------------------------------------------------------

_CRUNCHBASE_LATAM_COUNTRIES = {
    "Argentina",
    "Bolivia",
    "Brazil",
    "Chile",
    "Colombia",
    "Costa Rica",
    "Cuba",
    "Dominican Republic",
    "Ecuador",
    "El Salvador",
    "Guatemala",
    "Haiti",
    "Honduras",
    "Mexico",
    "Nicaragua",
    "Panama",
    "Paraguay",
    "Peru",
    "Puerto Rico",
    "Uruguay",
    "Venezuela",
}


@dataclass
class CrunchbaseOpenCompany:
    """A company parsed from the Crunchbase Open Data CSV export."""

    name: str
    permalink: str
    domain: Optional[str] = None
    homepage_url: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    short_description: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    founded_on: Optional[date] = None
    cb_url: Optional[str] = None
    employee_count: Optional[str] = None
    total_funding_usd: Optional[float] = None


def fetch_crunchbase_open_data(
    csv_path: Union[str, Path],
    filter_latam: bool = True,
    max_rows: Optional[int] = None,
) -> list[CrunchbaseOpenCompany]:
    """Parse the Crunchbase Open Data organizations CSV.

    Args:
        csv_path: Path to the organizations.csv file.
        filter_latam: If True, only return LATAM companies.
        max_rows: Maximum number of rows to return (None = no limit).

    Returns:
        List of CrunchbaseOpenCompany. Empty list if file not found.
    """
    path = Path(csv_path)
    if not path.exists():
        logger.warning("Crunchbase CSV not found: %s", csv_path)
        return []

    companies: list[CrunchbaseOpenCompany] = []

    try:
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only include companies (not investors, schools, etc.)
                roles = row.get("roles", "")
                if "company" not in roles.lower():
                    continue

                country = row.get("country_code", "").strip()

                if filter_latam and country not in _CRUNCHBASE_LATAM_COUNTRIES:
                    continue

                # Parse categories
                category_str = row.get("category_list", "")
                categories_list = [
                    c.strip() for c in category_str.split(",") if c.strip()
                ]

                # Parse founded date
                founded_on = _parse_date(row.get("founded_on"))

                # Parse total funding
                total_funding: Optional[float] = None
                raw_funding = row.get("total_funding_usd", "").strip()
                if raw_funding:
                    try:
                        total_funding = float(raw_funding)
                    except ValueError:
                        total_funding = None

                companies.append(
                    CrunchbaseOpenCompany(
                        name=row.get("name", "").strip(),
                        permalink=row.get("permalink", "").strip(),
                        domain=row.get("domain", "").strip() or None,
                        homepage_url=row.get("homepage_url", "").strip() or None,
                        country=country or None,
                        city=row.get("city", "").strip() or None,
                        region=row.get("region", "").strip() or None,
                        short_description=row.get("short_description", "").strip() or None,
                        categories=categories_list,
                        founded_on=founded_on,
                        cb_url=row.get("cb_url", "").strip() or None,
                        employee_count=row.get("employee_count", "").strip() or None,
                        total_funding_usd=total_funding,
                    )
                )

                if max_rows and len(companies) >= max_rows:
                    break

    except Exception as exc:
        logger.error("Error parsing Crunchbase CSV %s: %s", csv_path, exc)
        return []

    logger.info("Parsed %d companies from Crunchbase CSV", len(companies))
    return companies
