"""RSS/Atom feed collector for FUNDING agent.

Fetches and parses VC announcement feeds and investment news sources,
extracts funding events, and returns structured FundingEvent objects
with provenance tracking.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, List, Optional

import feedparser

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.dedup import compute_composite_hash, deduplicate_by_hash
from apps.agents.sources.http import create_http_client
from apps.agents.sources.rss import parse_feed_date as _parse_feed_date_dt

logger = logging.getLogger(__name__)


@dataclass
class FundingEvent:
    """A single funding event collected from a source.

    Represents a funding round announcement with company info,
    round details, and investor information.
    """

    company_name: str
    round_type: str
    source_url: str
    source_name: str
    company_slug: Optional[str] = None
    amount_usd: Optional[float] = None
    amount_local: Optional[float] = None
    currency: str = "USD"
    announced_date: Optional[date] = None
    lead_investors: List[str] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    valuation_usd: Optional[float] = None
    notes: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        """Generate content hash if not provided.

        Hash is based on (company_name, round_type) only — not source_url —
        so the same company+round from different RSS sources deduplicates.
        """
        if not self.content_hash:
            self.content_hash = compute_composite_hash(
                self.company_name.lower().strip(), self.round_type
            )


def parse_feed_date(entry: Any) -> Optional[date]:
    """Extract and parse the publication date from a feed entry.

    Delegates to shared parse_feed_date (returns datetime), then converts
    to date for FUNDING's date-only model.

    Args:
        entry: feedparser entry object

    Returns:
        date object or None
    """
    dt = _parse_feed_date_dt(entry)
    if dt is not None:
        return dt.date()
    return None


def clean_rss_notes(text: str) -> str:
    """Strip common RSS boilerplate patterns from notes.

    Many RSS feeds (WordPress, LatamList, etc.) append attribution
    boilerplate to every entry summary. This function removes those
    trailing patterns so notes contain only editorial content.

    Patterns removed:
        - English: ``"The post {title} appeared first on {site}."``
        - Portuguese: ``"O post {title} apareceu primeiro em {site}."``

    Both patterns are matched case-insensitively and anchored to the
    end of the string (``$``). The result is stripped of leading/trailing
    whitespace.

    Examples:
        >>> clean_rss_notes("Great funding round. The post Avenia raises $17M appeared first on LatamList.")
        'Great funding round.'
        >>> clean_rss_notes("Rodada seed. O post Lebane apareceu primeiro em Startupi.")
        'Rodada seed.'
        >>> clean_rss_notes("No boilerplate here")
        'No boilerplate here'

    Args:
        text: Raw RSS summary text (already truncated to 500 chars
            by the caller ``parse_funding_event``).

    Returns:
        Cleaned text with boilerplate removed and whitespace trimmed.
        Returns empty string if the input is only boilerplate.
    """
    # "The post X appeared first on Y."
    cleaned = re.sub(
        r"\s*The post\s+.+?\s+appeared first on\s+.+?\.?\s*$",
        "", text, flags=re.IGNORECASE,
    )
    # "O post X apareceu primeiro em Y."
    cleaned = re.sub(
        r"\s*O post\s+.+?\s+apareceu primeiro em\s+.+?\.?\s*$",
        "", cleaned, flags=re.IGNORECASE,
    )
    return cleaned.strip()


def extract_funding_from_title(title: str) -> Optional[dict]:
    """Extract funding information from title using regex patterns.

    Common patterns:
    - "Nubank raises $500M Series G"
    - "Stone recebe aporte de R$ 50 milhoes"
    - "Creditas levanta US$ 15M em rodada Serie A"

    Args:
        title: Article or post title

    Returns:
        Dictionary with extracted info or None
    """
    # Pattern 1: Company + action + amount + round type
    pattern1 = r"^([\w\s]+?)\s+(?:raises?|recebe|levanta|anuncia)\s+(?:aporte de\s+)?(?:US\$|R\$|\$)\s*(\d+(?:\.\d+)?)\s*(?:million|milhão|milhões|M|mi)?\s*(?:em\s+)?(?:rodada\s+)?(?:Series|Série)\s+([A-G])"

    match = re.search(pattern1, title, re.IGNORECASE)
    if match:
        company_name = match.group(1).strip()
        amount = float(match.group(2))
        currency_symbol = "BRL" if "R$" in title else "USD"
        round_type_letter = match.group(3)
        round_type = "series_{}".format(round_type_letter.lower())

        return {
            "company_name": company_name,
            "amount": amount,
            "currency": currency_symbol,
            "round_type": round_type,
        }

    # Pattern 2: Seed rounds (no letter)
    pattern2 = r"^([\w\s]+?)\s+(?:raises?|recebe|levanta|anuncia)\s+(?:aporte de\s+)?(?:US\$|R\$|\$)\s*(\d+(?:\.\d+)?)\s*(?:million|milhão|milhões|M|mi)?\s*(?:em\s+)?(?:rodada\s+)?(?:seed|pre-seed|pré-seed)"

    match = re.search(pattern2, title, re.IGNORECASE)
    if match:
        company_name = match.group(1).strip()
        amount = float(match.group(2))
        currency_symbol = "BRL" if "R$" in title else "USD"

        round_type = "pre_seed" if "pre" in title.lower() or "pré" in title.lower() else "seed"

        return {
            "company_name": company_name,
            "amount": amount,
            "currency": currency_symbol,
            "round_type": round_type,
        }

    return None


def extract_funding_from_content(content: str) -> dict:
    """Extract funding details from article content.

    Looks for patterns like:
    - Amount: "$10M", "R$ 50 milhoes"
    - Round type: "Series A", "Serie B", "seed round"
    - Investors: names following "led by", "liderado por"

    Args:
        content: Article content or summary

    Returns:
        Dictionary with extracted details
    """
    details = {}

    # Extract round type
    round_patterns = [
        (r"series\s+([a-g])", lambda m: "series_{}".format(m.group(1).lower())),
        (r"série\s+([a-g])", lambda m: "series_{}".format(m.group(1).lower())),
        (r"\b(seed|pre-seed|pre seed)\b", lambda m: m.group(1).lower().replace(" ", "_").replace("-", "_")),
        (r"rodada\s+(seed|série\s+[a-g])", lambda m: "seed" if "seed" in m.group(1).lower() else "series_{}".format(m.group(1)[-1].lower())),
    ]

    for pattern, transform in round_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            details["round_type"] = transform(match)
            break

    # Extract investors
    investor_patterns = [
        r"led by\s+([\w\s,&]+?)(?:\.|,|and|with)",
        r"liderado por\s+([\w\s,&]+?)(?:\.|,|e\s)",
        r"participation of\s+([\w\s,&]+?)(?:\.|,)",
    ]

    for pattern in investor_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            investors_str = match.group(1).strip()
            investors = re.split(r",\s*|\s+and\s+|\s+e\s+", investors_str)
            details["lead_investors"] = [inv.strip() for inv in investors if inv.strip()]
            break

    return details


def parse_funding_event(
    entry: Any, source_name: str
) -> Optional[FundingEvent]:
    """Parse a single RSS feed entry into a FundingEvent.

    Extracts company name, funding amount, round type, investors,
    and dates from the entry title and content.

    Args:
        entry: feedparser entry object
        source_name: Name of the data source

    Returns:
        FundingEvent or None if parsing fails
    """
    title = getattr(entry, "title", "")
    link = getattr(entry, "link", "")
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

    if not title or not link:
        return None

    # Extract from title first
    title_info = extract_funding_from_title(title)
    if not title_info:
        logger.debug("No funding info in title: %s", title)
        return None

    # Extract additional details from content
    content_info = extract_funding_from_content(summary)

    # Merge information
    company_name = title_info.get("company_name", "Unknown Company")
    amount = title_info.get("amount")
    currency = title_info.get("currency", "USD")
    round_type = title_info.get("round_type") or content_info.get("round_type", "unknown")
    lead_investors = content_info.get("lead_investors", [])

    announced_date = parse_feed_date(entry)

    return FundingEvent(
        company_name=company_name,
        round_type=round_type,
        amount_usd=amount if currency == "USD" else None,
        amount_local=amount if currency != "USD" else None,
        currency=currency,
        announced_date=announced_date,
        lead_investors=lead_investors,
        source_url=link,
        source_name=source_name,
        notes=clean_rss_notes(summary[:500]) if summary else None,
    )


def fetch_feed(
    source: DataSourceConfig,
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[FundingEvent]:
    """Fetch and parse a single RSS/Atom feed.

    Args:
        source: Data source configuration
        provenance: Provenance tracker
        agent_name: Name of the agent
        run_id: Current run ID

    Returns:
        List of FundingEvent objects
    """
    if not source.url:
        logger.warning("Source %s has no URL, skipping", source.name)
        return []

    logger.info("Fetching feed: %s", source.name)

    try:
        with create_http_client() as client:
            response = client.get(source.url)
            response.raise_for_status()
            content = response.text

        feed = feedparser.parse(content)

        if feed.bozo:
            logger.warning("Feed %s has parsing errors: %s", source.name, feed.bozo_exception)

        events: List[FundingEvent] = []
        for entry in feed.entries:
            event = parse_funding_event(entry, source.name)
            if event:
                events.append(event)

                provenance.track(
                    source_url=event.source_url,
                    source_name=source.name,
                    extraction_method="rss",
                )

        logger.info("Collected %d funding events from %s", len(events), source.name)
        return events

    except Exception as e:
        logger.error("Error fetching/parsing feed %s: %s", source.name, e, exc_info=True)
        return []


def collect_all_sources(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> List[FundingEvent]:
    """Collect funding events from all configured sources.

    Args:
        sources: List of data source configurations
        provenance: Provenance tracker
        agent_name: Name of the agent
        run_id: Current run ID

    Returns:
        List of all collected FundingEvent objects
    """
    all_events: List[FundingEvent] = []

    for source in sources:
        if source.source_type == "rss" and "gnews" in source.name:
            # Google News: URL built from params at fetch time
            from apps.agents.sources.google_news import fetch_google_news

            with create_http_client() as client:
                rss_items = fetch_google_news(source, client)

            for rss_item in rss_items:
                title_info = extract_funding_from_title(rss_item.title)
                if title_info:
                    event = FundingEvent(
                        company_name=title_info.get("company_name", ""),
                        round_type=title_info.get("round_type", "unknown"),
                        amount_usd=title_info.get("amount") if title_info.get("currency") == "USD" else None,
                        amount_local=title_info.get("amount") if title_info.get("currency") != "USD" else None,
                        currency=title_info.get("currency", "USD"),
                        source_url=rss_item.url,
                        source_name=source.name,
                        notes=clean_rss_notes(rss_item.summary[:500]) if rss_item.summary else None,
                    )
                    all_events.append(event)
                    provenance.track(
                        source_url=rss_item.url,
                        source_name=source.name,
                        extraction_method="rss",
                    )
        elif source.source_type == "rss":
            events = fetch_feed(source, provenance, agent_name, run_id)
            all_events.extend(events)
        elif source.source_type == "api" and "crunchbase" in source.name:
            from apps.agents.sources.crunchbase import fetch_funding_rounds

            locations_str = source.params.get("locations", "")
            locations = [loc.strip() for loc in locations_str.split(",") if loc.strip()] if locations_str else None
            limit = source.params.get("limit", 25)

            with create_http_client() as cb_client:
                rounds = fetch_funding_rounds(source, cb_client, locations=locations, limit=limit)

            for r in rounds:
                event = FundingEvent(
                    company_name=r.company_name,
                    round_type=r.round_type,
                    source_url=r.source_url,
                    source_name=source.name,
                    amount_usd=r.amount_usd,
                    announced_date=r.announced_date,
                    lead_investors=r.lead_investors,
                )
                all_events.append(event)
                provenance.track(
                    source_url=r.source_url,
                    source_name=source.name,
                    extraction_method="api",
                )
        elif source.source_type == "api":
            logger.info("API source %s not yet implemented, skipping", source.name)
        else:
            logger.warning("Unknown source type %s for %s", source.source_type, source.name)

    unique_events = deduplicate_by_hash(all_events, hash_fn=lambda e: e.content_hash)

    logger.info(
        "Collected %d unique funding events from %d sources (removed %d duplicates)",
        len(unique_events),
        len(sources),
        len(all_events) - len(unique_events),
    )

    return unique_events
