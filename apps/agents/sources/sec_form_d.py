"""Shared SEC EDGAR Form D source for agent collectors.

Fetches Form D filings (Regulation D private placement notices) from the
SEC EDGAR full-text search API.  Form D filings are public records that
disclose private fund-raising by US-registered entities — a strong
cross-validation signal for LATAM companies with US subsidiaries.

Uses the EFTS search endpoint (no API key required) with a mandatory
0.1 s delay between requests to respect SEC fair-access guidelines.

Falls back gracefully (returns []) when the API returns an error,
times out, or the response is malformed.

Usage:
    from apps.agents.sources.sec_form_d import (
        SECFormDFiling,
        fetch_sec_form_d,
    )

    filings = fetch_sec_form_d(source_config, client, ["Nubank", "Creditas"])
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from difflib import SequenceMatcher
from typing import List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.dedup import compute_composite_hash
from apps.agents.sources.verification import SourceAuthority, VerificationLevel

logger = logging.getLogger(__name__)

SEC_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"

_FUZZY_MATCH_THRESHOLD = 0.90


@dataclass
class SECFormDFiling:
    """A single Form D filing from SEC EDGAR.

    Content hash uses ``compute_composite_hash(cik, str(date_filed))``
    so that two filings by the same entity on the same date collapse
    during deduplication.
    """

    company_name: str
    cik: str
    source_url: str
    date_filed: date
    amount_sold: Optional[float] = None
    related_persons: List[str] = field(default_factory=list)
    authority: SourceAuthority = field(init=False)
    content_hash: str = ""

    def __post_init__(self) -> None:
        self.authority = SourceAuthority(
            verification_level=VerificationLevel.REGULATORY,
            institution_name="SEC",
            regulatory_id=f"CIK-{self.cik}",
        )
        if not self.content_hash:
            self.content_hash = compute_composite_hash(
                self.cik, str(self.date_filed)
            )


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO date string (YYYY-MM-DD) into a date object."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, AttributeError):
        return None


def _fuzzy_match(query: str, candidate: str) -> bool:
    """Return True when *candidate* is a fuzzy match for *query*.

    Comparison is case-insensitive.  The threshold (0.90) is deliberately
    high to avoid false positives — better to miss a filing than to
    attribute it to the wrong company.
    """
    ratio = SequenceMatcher(
        None, query.lower().strip(), candidate.lower().strip()
    ).ratio()
    return ratio >= _FUZZY_MATCH_THRESHOLD


def fetch_sec_form_d(
    source: DataSourceConfig,
    client: httpx.Client,
    company_names: List[str],
    date_range_days: int = 30,
) -> List[SECFormDFiling]:
    """Fetch Form D filings from the SEC EDGAR full-text search API.

    Each company name triggers a separate HTTP request with a 0.1 s
    sleep between requests to respect SEC fair-access policy.

    Args:
        source: DataSourceConfig with endpoint URL and provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        company_names: Company names to search for.
        date_range_days: How many days back to search (default 30).

    Returns:
        List of SECFormDFiling.  Empty list when *company_names* is empty,
        on HTTP/timeout errors, or when the response is malformed.
    """
    if not company_names:
        return []

    end_date = date.today()
    start_date = end_date - timedelta(days=date_range_days)

    filings: List[SECFormDFiling] = []

    for idx, name in enumerate(company_names):
        if idx > 0:
            time.sleep(0.1)

        params = {
            "q": name,
            "dateRange": "custom",
            "startdt": start_date.isoformat(),
            "enddt": end_date.isoformat(),
            "forms": "D",
        }

        try:
            response = client.get(source.url, params=params)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning(
                "SEC EDGAR Form D search error for '%s': %s", name, exc
            )
            continue

        try:
            data = response.json()
        except Exception as exc:
            logger.warning(
                "SEC EDGAR Form D JSON decode error for '%s': %s", name, exc
            )
            continue

        hits = data.get("hits", {}).get("hits", [])

        for hit in hits:
            try:
                src = hit.get("_source", {})
                accession_id = hit.get("_id", "")

                display_names = src.get("display_names", [])
                filing_company_name = display_names[0] if display_names else ""

                if not _fuzzy_match(name, filing_company_name):
                    continue

                filed_str = src.get("file_date") or src.get(
                    "display_date_filed"
                )
                filed_date = _parse_date(filed_str)
                if filed_date is None:
                    continue

                cik = src.get("entity_id", "")

                source_url = (
                    f"https://www.sec.gov/cgi-bin/browse-edgar"
                    f"?action=getcompany&CIK={cik}&type=D"
                    f"&dateb=&owner=include&count=10"
                )

                raw_amount = src.get("amount_sold")
                amount_sold: Optional[float] = None
                if raw_amount is not None:
                    try:
                        parsed = float(raw_amount)
                        amount_sold = None if parsed == 0 else parsed
                    except (ValueError, TypeError):
                        amount_sold = None

                related = src.get("related_persons", [])

                filings.append(
                    SECFormDFiling(
                        company_name=filing_company_name,
                        cik=cik,
                        source_url=source_url,
                        date_filed=filed_date,
                        amount_sold=amount_sold,
                        related_persons=related,
                    )
                )
            except Exception as exc:
                logger.debug(
                    "Skipping malformed SEC Form D hit: %s", exc
                )
                continue

    logger.info(
        "Fetched %d Form D filings from %s", len(filings), source.name
    )
    return filings
