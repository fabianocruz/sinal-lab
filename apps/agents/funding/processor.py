"""Processing pipeline for FUNDING agent.

Normalizes currency, matches company names to slugs, deduplicates
funding events from multiple sources, and flags amount conflicts.
"""

import logging
import re
from typing import Optional

from fuzzywuzzy import fuzz

from apps.agents.funding.collector import FundingEvent

logger = logging.getLogger(__name__)

# Fixed exchange rates for MVP (hardcoded fallback)
# In production, use live exchange rate API
EXCHANGE_RATES = {
    "BRL": 0.20,  # 1 BRL = 0.20 USD (approx 5.0 BRL/USD)
    "MXN": 0.058,  # 1 MXN = 0.058 USD (approx 17.2 MXN/USD)
    "ARS": 0.0010,  # 1 ARS = 0.001 USD (approx 1000 ARS/USD)
    "CLP": 0.0011,  # 1 CLP = 0.0011 USD (approx 900 CLP/USD)
    "COP": 0.00025,  # 1 COP = 0.00025 USD (approx 4000 COP/USD)
    "PEN": 0.27,  # 1 PEN = 0.27 USD (approx 3.7 PEN/USD)
    "UYU": 0.025,  # 1 UYU = 0.025 USD (approx 40 UYU/USD)
    "USD": 1.0,
}


def normalize_currency(event: FundingEvent) -> FundingEvent:
    """Convert local currency amounts to USD using exchange rates.

    Args:
        event: FundingEvent with amount_local and currency

    Returns:
        FundingEvent with amount_usd populated
    """
    if event.amount_usd is not None:
        # Already in USD
        return event

    if event.amount_local is None:
        # No amount to convert
        return event

    currency = event.currency.upper()
    if currency not in EXCHANGE_RATES:
        logger.warning(
            "Unknown currency %s for %s, cannot convert to USD",
            currency,
            event.company_name,
        )
        return event

    rate = EXCHANGE_RATES[currency]
    event.amount_usd = event.amount_local * rate

    logger.debug(
        "Converted %s %s %.2f to USD %.2f (rate: %.4f)",
        event.company_name,
        currency,
        event.amount_local,
        event.amount_usd,
        rate,
    )

    return event


def normalize_round_type(round_type: str) -> str:
    """Normalize round type strings to canonical format.

    Examples:
        "Seed Round" -> "seed"
        "Serie A" -> "series_a"
        "Series B" -> "series_b"

    Args:
        round_type: Raw round type string

    Returns:
        Normalized round type
    """
    round_lower = round_type.lower().strip()

    # Remove common noise words
    round_lower = re.sub(r"\s*(round|rodada|ronda)\s*", "", round_lower)

    # Map variations to canonical names
    if round_lower in ("pre-seed", "pre seed", "preseed"):
        return "pre_seed"
    if round_lower in ("seed", "semente"):
        return "seed"

    # Series A-G
    match = re.search(r"(series|série|serie)\s*([a-g])", round_lower)
    if match:
        letter = match.group(2)
        return f"series_{letter}"

    # IPO, debt, grant, etc.
    if "ipo" in round_lower:
        return "ipo"
    if "debt" in round_lower or "dívida" in round_lower:
        return "debt"
    if "grant" in round_lower:
        return "grant"

    # Default: return as-is (lowercase, underscores)
    return round_lower.replace(" ", "_").replace("-", "_")


def slugify(name: str) -> str:
    """Convert company name to URL-safe slug.

    Args:
        name: Company name

    Returns:
        Slugified version (lowercase, hyphens, no special chars)
    """
    # Lowercase and strip
    slug = name.lower().strip()

    # Remove common suffixes (Inc., Ltd., S.A., etc.)
    slug = re.sub(r"\s+(inc\.?|ltd\.?|llc|s\.a\.?|ltda\.?)$", "", slug, flags=re.IGNORECASE)

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove special characters
    slug = re.sub(r"[^\w\-]", "", slug)

    # Remove multiple hyphens
    slug = re.sub(r"\-+", "-", slug)

    return slug.strip("-")


def fuzzy_match_company(
    company_name: str,
    known_companies: Optional[dict[str, str]] = None,
) -> Optional[str]:
    """Fuzzy match company name to a known company slug.

    Args:
        company_name: Raw company name from feed
        known_companies: Dict mapping company slugs to canonical names

    Returns:
        Matched slug or None
    """
    if not known_companies:
        # No companies to match against, return generated slug
        return slugify(company_name)

    # Try exact match first (slug)
    candidate_slug = slugify(company_name)
    if candidate_slug in known_companies:
        return candidate_slug

    # Fuzzy match against canonical names
    best_match_slug: Optional[str] = None
    best_score = 0

    for slug, canonical_name in known_companies.items():
        score = fuzz.ratio(company_name.lower(), canonical_name.lower())
        if score > best_score:
            best_score = score
            best_match_slug = slug

    # Accept match if score >= 85
    if best_score >= 85:
        logger.info(
            "Fuzzy matched '%s' to '%s' (score: %d)",
            company_name,
            known_companies[best_match_slug],
            best_score,
        )
        return best_match_slug

    # No good match, return generated slug
    return candidate_slug


def merge_duplicate_events(events: list[FundingEvent]) -> list[FundingEvent]:
    """Merge duplicate events from different sources.

    Groups events by (company_slug, round_type, announced_date).
    For each group:
    - Keep amount from highest-confidence source (API > RSS)
    - Merge investor lists (union)
    - Flag if amounts differ by >20% (amount_conflict)

    Args:
        events: List of FundingEvent objects

    Returns:
        List of merged FundingEvent objects
    """
    # Group by (company_slug, round_type, date)
    groups: dict[tuple, list[FundingEvent]] = {}

    for event in events:
        # Skip if no company_slug (can't group)
        if not event.company_slug:
            continue

        # Use announced_date or None
        key = (event.company_slug, event.round_type, event.announced_date)
        if key not in groups:
            groups[key] = []
        groups[key].append(event)

    merged_events: list[FundingEvent] = []

    for key, group in groups.items():
        if len(group) == 1:
            # No duplicates, keep as-is
            merged_events.append(group[0])
            continue

        # Merge multiple events
        logger.info(
            "Merging %d events for %s %s on %s",
            len(group),
            key[0],  # company_slug
            key[1],  # round_type
            key[2],  # date
        )

        # Select "best" event (prefer API sources over RSS)
        # For MVP, just take first event as base
        base_event = group[0]

        # Collect all amounts
        amounts = [e.amount_usd for e in group if e.amount_usd is not None]

        # Check for amount conflicts
        amount_conflict = False
        if len(amounts) > 1:
            amounts_sorted = sorted(amounts)
            min_amount = amounts_sorted[0]
            max_amount = amounts_sorted[-1]
            if max_amount > 0 and (max_amount - min_amount) / max_amount > 0.2:
                # Amounts differ by >20%
                amount_conflict = True
                logger.warning(
                    "Amount conflict for %s: amounts range from $%.2fM to $%.2fM",
                    base_event.company_name,
                    min_amount,
                    max_amount,
                )

        # Merge investor lists (union)
        all_leads = set()
        all_participants = set()
        for e in group:
            all_leads.update(e.lead_investors)
            all_participants.update(e.participants)

        base_event.lead_investors = sorted(list(all_leads))
        base_event.participants = sorted(list(all_participants))

        # Add conflict flag to notes
        if amount_conflict:
            conflict_note = f" [AMOUNT_CONFLICT: {len(amounts)} sources report different amounts]"
            if base_event.notes:
                base_event.notes += conflict_note
            else:
                base_event.notes = conflict_note.strip()

        merged_events.append(base_event)

    logger.info(
        "Merged %d events into %d unique funding rounds",
        len(events),
        len(merged_events),
    )

    return merged_events


def process_events(
    events: list[FundingEvent],
    known_companies: Optional[dict[str, str]] = None,
) -> list[FundingEvent]:
    """Process all funding events.

    Pipeline:
    1. Currency normalization (local → USD)
    2. Round type normalization
    3. Company name → slug matching
    4. Deduplication and merging

    Args:
        events: List of raw FundingEvent objects
        known_companies: Optional dict of known companies (slug → name)

    Returns:
        List of processed FundingEvent objects
    """
    logger.info("Processing %d raw funding events", len(events))

    processed: list[FundingEvent] = []

    for event in events:
        # Step 1: Normalize currency
        event = normalize_currency(event)

        # Step 2: Normalize round type
        event.round_type = normalize_round_type(event.round_type)

        # Step 3: Match company slug
        if not event.company_slug:
            event.company_slug = fuzzy_match_company(event.company_name, known_companies)

        processed.append(event)

    # Step 4: Merge duplicates
    merged = merge_duplicate_events(processed)

    logger.info("Processing complete: %d events ready for scoring", len(merged))

    return merged
