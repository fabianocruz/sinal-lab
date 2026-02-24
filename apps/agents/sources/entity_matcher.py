"""Cross-source entity matching for company deduplication.

Pure functions that match company entities across data sources using a
priority cascade: CNPJ exact -> domain exact -> Crunchbase permalink ->
fuzzy name + city.

No database dependency in matching logic -- works with in-memory indices
built from DB or test fixtures.
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class CandidateCompany:
    """Normalized intermediate format from any source."""

    name: str
    slug: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Brasil"
    cnpj: Optional[str] = None
    domain: Optional[str] = None
    crunchbase_permalink: Optional[str] = None
    github_login: Optional[str] = None
    source_name: str = ""
    confidence: float = 0.5
    # Extra fields for merging
    founded_date: Optional[str] = None
    team_size: Optional[int] = None
    business_model: Optional[str] = None
    tech_stack: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    twitter_url: Optional[str] = None
    # Funding fields (sourced from Crunchbase; propagated through pipeline)
    funding_stage: Optional[str] = None  # Canonical stage: pre_seed, seed, series_a … ipo
    total_funding_usd: Optional[float] = None  # Cumulative USD raised


@dataclass
class MatchResult:
    """Result of a match attempt."""

    matched_slug: Optional[str]
    match_type: str  # "cnpj", "domain", "permalink", "fuzzy_name", "new"
    match_confidence: float
    is_new: bool


@dataclass
class DedupIndices:
    """In-memory lookup indices for deduplication."""

    cnpj_to_slug: dict[str, str] = field(default_factory=dict)
    domain_to_slug: dict[str, str] = field(default_factory=dict)
    permalink_to_slug: dict[str, str] = field(default_factory=dict)
    name_city_to_slug: dict[str, str] = field(default_factory=dict)  # "name_lower|city_lower" -> slug


def normalize_domain(url: Optional[str]) -> Optional[str]:
    """Extract and normalize domain from a URL.

    Strips protocol, www prefix, trailing slash, and query params.
    Returns lowercase domain or None if invalid.

    Examples:
        >>> normalize_domain("https://www.nubank.com.br/about")
        'nubank.com.br'
        >>> normalize_domain("http://stone.co")
        'stone.co'
        >>> normalize_domain(None)
        None
    """
    if not url:
        return None

    url = url.strip()
    if not url:
        return None

    # Add scheme if missing for urlparse to work
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return None

        # Strip www prefix
        if host.startswith("www."):
            host = host[4:]

        return host.lower()
    except Exception:
        return None


def normalize_cnpj(cnpj: Optional[str]) -> Optional[str]:
    """Strip formatting from CNPJ and return 14-digit string.

    Args:
        cnpj: CNPJ string, possibly with dots/slashes/dashes.

    Returns:
        14-digit string or None if invalid.

    Examples:
        >>> normalize_cnpj("18.236.120/0001-58")
        '18236120000158'
        >>> normalize_cnpj("18236120000158")
        '18236120000158'
        >>> normalize_cnpj("123")
        None
    """
    if not cnpj:
        return None

    digits = re.sub(r"[^0-9]", "", cnpj)
    if len(digits) != 14:
        return None

    return digits


# Canonical country names (Portuguese) used in the frontend CountryFilter.
# Maps common English/variant spellings to the canonical form.
_COUNTRY_ALIASES: dict[str, str] = {
    "brazil": "Brasil",
    "brasil": "Brasil",
    "mexico": "México",
    "méxico": "México",
    "colombia": "Colômbia",
    "colômbia": "Colômbia",
    "argentina": "Argentina",
    "chile": "Chile",
    "peru": "Peru",
    "perú": "Peru",
    "uruguay": "Uruguai",
    "uruguai": "Uruguai",
    "ecuador": "Equador",
    "equador": "Equador",
    "costa rica": "Costa Rica",
    "panama": "Panamá",
    "panamá": "Panamá",
    "dominican republic": "Rep. Dominicana",
    "rep. dominicana": "Rep. Dominicana",
    "paraguay": "Paraguai",
    "paraguai": "Paraguai",
    "bolivia": "Bolívia",
    "bolívia": "Bolívia",
    "puerto rico": "Porto Rico",
    "porto rico": "Porto Rico",
    "venezuela": "Venezuela",
    "el salvador": "El Salvador",
    "guatemala": "Guatemala",
    "honduras": "Honduras",
    "nicaragua": "Nicarágua",
    "cuba": "Cuba",
    "haiti": "Haiti",
}


def normalize_country(country: Optional[str]) -> str:
    """Normalize a country name to the canonical Portuguese form.

    Returns 'Brasil' as default for empty/None values.

    Examples:
        >>> normalize_country("Brazil")
        'Brasil'
        >>> normalize_country("México")
        'México'
        >>> normalize_country(None)
        'Brasil'
    """
    if not country or not country.strip():
        return "Brasil"
    return _COUNTRY_ALIASES.get(country.strip().lower(), country.strip())


def _name_similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two company names.

    Uses SequenceMatcher on lowercased, stripped names.

    Returns:
        Float 0-1 representing similarity.
    """
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _name_city_key(name: str, city: Optional[str]) -> str:
    """Build a lookup key from name + city."""
    name_part = name.lower().strip()
    city_part = (city or "").lower().strip()
    return f"{name_part}|{city_part}"


def match_single(
    candidate: CandidateCompany,
    indices: DedupIndices,
) -> MatchResult:
    """Match a single candidate against existing indices.

    Priority cascade:
    1. CNPJ exact match (confidence 1.0)
    2. Domain exact match (confidence 0.95)
    3. Crunchbase permalink exact match (confidence 0.9)
    4. Fuzzy name + same city (confidence = similarity * 0.85, threshold 0.85)

    Args:
        candidate: The candidate company to match.
        indices: Pre-built dedup indices.

    Returns:
        MatchResult with matched_slug, match_type, confidence, and is_new flag.
    """
    # 1. CNPJ exact
    cnpj = normalize_cnpj(candidate.cnpj)
    if cnpj and cnpj in indices.cnpj_to_slug:
        return MatchResult(
            matched_slug=indices.cnpj_to_slug[cnpj],
            match_type="cnpj",
            match_confidence=1.0,
            is_new=False,
        )

    # 2. Domain exact
    domain = normalize_domain(candidate.website) or candidate.domain
    if domain:
        domain = domain.lower()
        if domain in indices.domain_to_slug:
            return MatchResult(
                matched_slug=indices.domain_to_slug[domain],
                match_type="domain",
                match_confidence=0.95,
                is_new=False,
            )

    # 3. Crunchbase permalink exact
    permalink = candidate.crunchbase_permalink
    if permalink and permalink in indices.permalink_to_slug:
        return MatchResult(
            matched_slug=indices.permalink_to_slug[permalink],
            match_type="permalink",
            match_confidence=0.9,
            is_new=False,
        )

    # 4. Fuzzy name + city
    if candidate.name and candidate.city:
        best_similarity = 0.0
        best_slug = None

        for existing_key, slug in indices.name_city_to_slug.items():
            existing_name, existing_city = existing_key.split("|", 1)
            candidate_city = (candidate.city or "").lower().strip()

            if existing_city != candidate_city:
                continue

            similarity = _name_similarity(candidate.name, existing_name)
            if similarity > best_similarity:
                best_similarity = similarity
                best_slug = slug

        if best_similarity >= 0.85 and best_slug:
            return MatchResult(
                matched_slug=best_slug,
                match_type="fuzzy_name",
                match_confidence=round(best_similarity * 0.85, 3),
                is_new=False,
            )

    # No match -- new company
    return MatchResult(
        matched_slug=None,
        match_type="new",
        match_confidence=0.0,
        is_new=True,
    )


def match_batch(
    candidates: list[CandidateCompany],
    indices: DedupIndices,
) -> list[tuple[CandidateCompany, MatchResult]]:
    """Match a batch of candidates with intra-batch deduplication.

    Uses a running copy of indices that grows as new companies are found,
    preventing duplicate inserts within the same batch.

    Args:
        candidates: List of candidate companies.
        indices: Pre-built dedup indices from DB.

    Returns:
        List of (candidate, match_result) tuples.
    """
    # Work on a copy to avoid mutating the original indices
    running = DedupIndices(
        cnpj_to_slug=dict(indices.cnpj_to_slug),
        domain_to_slug=dict(indices.domain_to_slug),
        permalink_to_slug=dict(indices.permalink_to_slug),
        name_city_to_slug=dict(indices.name_city_to_slug),
    )

    results: list[tuple[CandidateCompany, MatchResult]] = []

    for candidate in candidates:
        result = match_single(candidate, running)
        results.append((candidate, result))

        # Register candidate's identifiers in running indices.
        # For new candidates: use their own slug so later candidates can find them.
        # For matched candidates: register under the matched slug so additional
        # identifiers (e.g., domain from ABStartups) become discoverable.
        slug = (
            (candidate.slug or candidate.name.lower().replace(" ", "-"))
            if result.is_new
            else result.matched_slug
        )

        cnpj = normalize_cnpj(candidate.cnpj)
        if cnpj and cnpj not in running.cnpj_to_slug:
            running.cnpj_to_slug[cnpj] = slug

        domain = normalize_domain(candidate.website) or candidate.domain
        if domain and domain.lower() not in running.domain_to_slug:
            running.domain_to_slug[domain.lower()] = slug

        if candidate.crunchbase_permalink and candidate.crunchbase_permalink not in running.permalink_to_slug:
            running.permalink_to_slug[candidate.crunchbase_permalink] = slug

        if result.is_new and candidate.name:
            key = _name_city_key(candidate.name, candidate.city)
            running.name_city_to_slug[key] = slug

    new_count = sum(1 for _, r in results if r.is_new)
    matched_count = len(results) - new_count
    logger.info(
        "Batch match complete: %d candidates -> %d matched, %d new",
        len(candidates),
        matched_count,
        new_count,
    )

    return results


def build_dedup_indices_from_db(session) -> DedupIndices:
    """Build dedup lookup indices from existing database records.

    Queries Company and CompanyExternalId tables to build in-memory
    indices for fast matching.

    Args:
        session: SQLAlchemy session.

    Returns:
        DedupIndices populated from DB.
    """
    from packages.database.models.company import Company

    indices = DedupIndices()

    # Build name+city index and domain index from Company table
    companies = session.query(Company.slug, Company.name, Company.city, Company.website).all()
    for slug, name, city, website in companies:
        if name:
            key = _name_city_key(name, city)
            indices.name_city_to_slug[key] = slug

        if website:
            domain = normalize_domain(website)
            if domain:
                indices.domain_to_slug[domain] = slug

    # Build CNPJ index from Company table
    try:
        cnpj_companies = (
            session.query(Company.slug, Company.cnpj).filter(Company.cnpj.isnot(None)).all()
        )
        for slug, cnpj in cnpj_companies:
            normalized = normalize_cnpj(cnpj)
            if normalized:
                indices.cnpj_to_slug[normalized] = slug
    except Exception:
        logger.debug("cnpj column not available yet, skipping CNPJ index")

    # Build from CompanyExternalId if table exists
    try:
        from packages.database.models.company_external_id import CompanyExternalId

        ext_ids = session.query(
            CompanyExternalId.company_slug,
            CompanyExternalId.id_type,
            CompanyExternalId.id_value,
        ).all()

        for company_slug, id_type, id_value in ext_ids:
            if id_type == "cnpj":
                normalized = normalize_cnpj(id_value)
                if normalized:
                    indices.cnpj_to_slug[normalized] = company_slug
            elif id_type == "domain":
                indices.domain_to_slug[id_value.lower()] = company_slug
            elif id_type == "crunchbase_permalink":
                indices.permalink_to_slug[id_value] = company_slug
            elif id_type == "github_login":
                pass  # Could be added as an additional index later
    except Exception:
        logger.debug("company_external_ids table not available yet, skipping")

    logger.info(
        "Built dedup indices: %d CNPJ, %d domain, %d permalink, %d name+city",
        len(indices.cnpj_to_slug),
        len(indices.domain_to_slug),
        len(indices.permalink_to_slug),
        len(indices.name_city_to_slug),
    )

    return indices
