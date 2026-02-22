"""Shared BCB (Banco Central do Brasil) institutions source for agent collectors.

Fetches authorized financial institutions from the BCB OData API (DASFN).
This is a regulatory data source (VerificationLevel.REGULATORY) providing
the official registry of all authorized institutions in Brazil.

Falls back gracefully (returns []) when the API returns an error, times out,
or the response is malformed.

Usage:
    from apps.agents.sources.bcb_institutions import (
        fetch_bcb_institutions,
        detect_new_authorizations,
    )

    institutions = fetch_bcb_institutions(source_config, client, segments=["b4"])
    new = detect_new_authorizations(current=institutions, previous=old_institutions)
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.verification import SourceAuthority, VerificationLevel

logger = logging.getLogger(__name__)

BCB_ODATA_BASE = (
    "https://olinda.bcb.gov.br/olinda/servico/DASFN/versao/v1/odata/IfDataDes662"
)

# Sentinel object to detect when authority was not provided
_AUTHORITY_SENTINEL = object()


def _normalize_cnpj(cnpj: str) -> str:
    """Strip all non-digit characters from a CNPJ string.

    CNPJ can arrive formatted ("12.345.678/0001-90") or already clean
    ("12345678000190"). This normalizes to digits only.

    Args:
        cnpj: Raw CNPJ string, possibly with punctuation.

    Returns:
        Digits-only string. Empty string if input is empty.
    """
    return re.sub(r"\D", "", cnpj)


@dataclass
class BCBInstitution:
    """A financial institution from the BCB authorized institutions registry.

    Content hash is MD5 of the normalized CNPJ (digits only), ensuring
    deduplication across different CNPJ format representations.
    """

    name: str
    cnpj: str
    segment: str
    situation: str
    authorization_date: Optional[str] = None
    municipality: Optional[str] = None
    state: Optional[str] = None
    authority: Optional[SourceAuthority] = field(default=None)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if self.authority is None:
            self.authority = SourceAuthority(
                verification_level=VerificationLevel.REGULATORY,
                institution_name="BCB",
            )
        if not self.content_hash:
            normalized = _normalize_cnpj(self.cnpj)
            self.content_hash = hashlib.md5(normalized.encode()).hexdigest()


def fetch_bcb_institutions(
    source: DataSourceConfig,
    client: httpx.Client,
    segments: Optional[List[str]] = None,
) -> List[BCBInstitution]:
    """Fetch authorized financial institutions from the BCB OData API.

    Args:
        source: DataSourceConfig with endpoint URL and provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        segments: Optional list of segment codes to filter by (e.g., ["b1", "b4"]).
            When provided, a separate filtered request is made per segment.
            When None, a single unfiltered request is made.

    Returns:
        List of BCBInstitution. Empty list on HTTP/timeout errors or
        when the response is malformed.
    """
    if segments:
        all_institutions: List[BCBInstitution] = []
        for segment in segments:
            filter_param = f"Segmento eq '{segment}'"
            institutions = _fetch_page(source, client, filter_param=filter_param)
            all_institutions.extend(institutions)
        logger.info(
            "Fetched %d institutions from %s (segments: %s)",
            len(all_institutions),
            source.name,
            segments,
        )
        return all_institutions

    institutions = _fetch_page(source, client)
    logger.info(
        "Fetched %d institutions from %s", len(institutions), source.name
    )
    return institutions


def _fetch_page(
    source: DataSourceConfig,
    client: httpx.Client,
    filter_param: Optional[str] = None,
) -> List[BCBInstitution]:
    """Fetch all pages from the BCB OData API, following @odata.nextLink.

    Args:
        source: DataSourceConfig with endpoint URL.
        client: Pre-configured httpx.Client.
        filter_param: Optional OData $filter expression.

    Returns:
        List of BCBInstitution from all pages. Empty list on errors.
    """
    url = source.url or BCB_ODATA_BASE
    params: dict[str, str] = {"$format": "json"}
    if filter_param:
        params["$filter"] = filter_param

    all_institutions: List[BCBInstitution] = []

    while url:
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning(
                "BCB institutions API error for %s: %s",
                source.name,
                exc,
            )
            return all_institutions if all_institutions else []

        try:
            data = response.json()
        except Exception as exc:
            logger.warning(
                "BCB institutions JSON decode error for %s: %s",
                source.name,
                exc,
            )
            return all_institutions if all_institutions else []

        entities = data.get("value", [])
        for entity in entities:
            try:
                institution = BCBInstitution(
                    name=entity.get("Nome", ""),
                    cnpj=entity.get("Cnpj", ""),
                    segment=entity.get("Segmento", ""),
                    authorization_date=entity.get("DtAutorizacao"),
                    situation=entity.get("Situacao", ""),
                    municipality=entity.get("Municipio"),
                    state=entity.get("UF"),
                )
                all_institutions.append(institution)
            except Exception as exc:
                logger.debug(
                    "Skipping malformed BCB institution record: %s", exc
                )
                continue

        # OData pagination: follow @odata.nextLink if present
        next_link = data.get("@odata.nextLink")
        if next_link:
            url = next_link
            # On subsequent pages, params are already encoded in nextLink URL
            params = {}
        else:
            url = None  # type: ignore[assignment]

    return all_institutions


def detect_new_authorizations(
    current: List[BCBInstitution],
    previous: List[BCBInstitution],
) -> List[BCBInstitution]:
    """Detect newly authorized institutions by comparing two snapshots.

    Pure function -- no HTTP calls. Compares by normalized CNPJ (digits only)
    to handle format differences between snapshots.

    Args:
        current: Latest snapshot of institutions.
        previous: Previous snapshot to compare against.

    Returns:
        Institutions in ``current`` whose CNPJ does not appear in ``previous``.
    """
    previous_cnpjs = {_normalize_cnpj(inst.cnpj) for inst in previous}

    return [
        inst
        for inst in current
        if _normalize_cnpj(inst.cnpj) not in previous_cnpjs
    ]
