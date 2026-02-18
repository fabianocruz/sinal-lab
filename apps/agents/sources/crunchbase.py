"""Shared Crunchbase Basic API source for agent collectors.

Fetches funding rounds and company profiles via the Crunchbase Basic API.
Requires a CRUNCHBASE_API_KEY environment variable (maps to the
``X-cb-user-key`` header).

Falls back gracefully (returns []) when the key is missing, the API
returns an error, or the response is malformed.

Usage:
    from apps.agents.sources.crunchbase import (
        fetch_funding_rounds,
        fetch_companies,
    )

    rounds = fetch_funding_rounds(source_config, client, limit=50)
    companies = fetch_companies(source_config, client, limit=30)
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

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
