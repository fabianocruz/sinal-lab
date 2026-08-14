"""RSS/Atom feed collector for FUNDING agent.

Fetches and parses VC announcement feeds and investment news sources,
extracts funding events, and returns structured FundingEvent objects
with provenance tracking.

Extraction strategy (per item):
    1. Regex on the title (fast, free, high precision, low recall).
    2. If the title regex misses, a cheap keyword pre-filter decides
       whether the item is plausibly about funding at all.
    3. Only items that pass the pre-filter are sent to the LLM for
       structured extraction (``LLMFundingExtractor``), under a
       per-run call budget.

Step 3 exists because the title regex requires a rigid
``Company raises $XM Series Y`` shape, which almost no real headline
follows — before it was added, 23 configured sources produced ~0-1
usable events per week.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.llm import LLMClient, LLMConfig, strip_code_fences
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.dedup import compute_composite_hash, deduplicate_by_hash
from apps.agents.sources.http import create_http_client
from apps.agents.sources.rss import parse_feed_date as _parse_feed_date_dt

logger = logging.getLogger(__name__)

# How the fields of a FundingEvent were obtained. Stored on the event so
# downstream scoring can weight regex/LLM/API extractions differently.
EXTRACTION_METHOD_REGEX = "rss_regex"
EXTRACTION_METHOD_LLM = "llm_fallback"
EXTRACTION_METHOD_API = "api"
EXTRACTION_METHOD_DATABASE = "database"
EXTRACTION_METHOD_GROK = "grok_live_search"

# Maximum LLM extraction calls per collection run (cost guard).
DEFAULT_LLM_EXTRACTION_BUDGET = 40

# API sources collected outside the main source loop (they need the list of
# companies gathered by the other sources first).
_API_SOURCES_HANDLED_SEPARATELY = frozenset({"sec_form_d"})


@dataclass
class FundingEvent:
    """A single funding event collected from a source.

    Represents a funding round announcement with company info,
    round details, and investor information.

    Amount conventions (legacy, handled downstream by
    ``funding.synthesizer.normalize_amount_usd``):
        - Title-regex extraction stores *millions* (``15.0`` = $15M).
        - LLM/API/database extraction stores *absolute* units
          (``15_000_000`` = $15M).
    Anything below 1000 is interpreted as millions when normalizing, so
    both conventions round-trip correctly.

    ``extraction_method`` records how the fields were obtained
    (``rss_regex``, ``llm_fallback``, ``api``, ``database``,
    ``grok_live_search``).
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
    extraction_method: str = "unknown"
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


# ---------------------------------------------------------------------------
# LLM fallback extraction
# ---------------------------------------------------------------------------

# Cheap pre-filter: only items matching one of these patterns are worth an
# LLM call. Deliberately multilingual (pt/en/es) and deliberately narrow —
# generic words like "round" or "million" would let most tech news through.
_FUNDING_SIGNAL_PATTERNS: tuple = (
    r"\brais(?:e|es|ed|ing)\b",
    r"\bfunding\b",
    r"\bfundrais\w*\b",
    r"\bpre[- ]?seed\b",
    r"\bseed\b",
    r"\b(?:series|série|serie)\s+[a-g]\b",
    r"\bventure\s+round\b",
    r"\bcapt(?:a|am|ou|ar|ando|ação|acao)\b",
    r"\blevant(?:a|am|ou|ar|ando)\b",
    r"\baportes?\b",
    r"\brodada\b",
    r"\bronda\b",
    r"\binvestimento\b",
    r"\binvers(?:ión|ion)\b",
    r"\brecaud\w+\b",
    r"\bfinanciamento\b",
    r"\bfinanciaci(?:ón|on)\b",
    r"\bled\s+by\b",
    r"\bliderad[oa]\s+por\b",
    r"\bvaluation\b",
    r"\bmega[- ]?round\b",
)

_FUNDING_SIGNAL_RE = re.compile("|".join(_FUNDING_SIGNAL_PATTERNS), re.IGNORECASE)

# Round types the LLM is allowed to return (anything else becomes "unknown").
_VALID_ROUND_TYPES = frozenset(
    {
        "pre_seed",
        "seed",
        "series_a",
        "series_b",
        "series_c",
        "series_d",
        "series_e",
        "series_f",
        "series_g",
        "venture",
        "angel",
        "bridge",
        "extension",
        "debt",
        "grant",
        "ipo",
        "unknown",
    }
)

_LLM_EXTRACTION_SYSTEM_PROMPT = (
    "Você extrai dados estruturados de notícias sobre investimento em startups. "
    "Responde SEMPRE com um único objeto JSON, sem texto ao redor e sem markdown."
)

_LLM_EXTRACTION_PROMPT = """Analise a notícia abaixo e diga se ela anuncia uma rodada de investimento (funding round) concreta de UMA empresa.

TÍTULO: {title}

TEXTO: {body}

Responda apenas com JSON neste formato:
{{"is_funding_event": true|false,
 "company_name": "nome da empresa que captou",
 "amount": número absoluto captado na moeda informada (ex.: 6500000 para US$ 6,5 milhões) ou null,
 "currency": "USD"|"BRL"|"MXN"|"ARS"|"COP"|"CLP"|"EUR",
 "round_type": "pre_seed"|"seed"|"series_a"|"series_b"|"series_c"|"series_d"|"series_e"|"series_f"|"series_g"|"venture"|"angel"|"bridge"|"extension"|"debt"|"grant"|"ipo"|"unknown",
 "investors": ["fundos que participaram"]}}

Regras:
- is_funding_event = false para análises de mercado, listas, opiniões, relatórios agregados, lançamentos de fundos de VC (fund raising do próprio fundo) e aquisições.
- Nunca invente valores: use null quando o valor não for informado.
- company_name deve ser apenas o nome da empresa, sem descrição."""


def looks_like_funding_news(title: str, body: str = "") -> bool:
    """Cheap keyword pre-filter for "is this item plausibly about funding?".

    Runs before any LLM call so the hundreds of unrelated tech-news items
    each feed returns never cost money.

    Args:
        title: Item title.
        body: Item summary/body (optional).

    Returns:
        True if the text contains at least one funding signal.
    """
    haystack = f"{title or ''} {body or ''}".strip()
    if not haystack:
        return False
    return bool(_FUNDING_SIGNAL_RE.search(haystack))


def _coerce_amount(raw: Any) -> Optional[float]:
    """Coerce an LLM-provided amount into a positive float, or None."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if value > 0 else None
    if isinstance(raw, str):
        digits = re.sub(r"[^\d.]", "", raw.replace(",", "."))
        # Keep only the first decimal separator (e.g. "6.500.000" -> "6.500000")
        parts = digits.split(".")
        if len(parts) > 2:
            digits = parts[0] + "".join(parts[1:])
        try:
            value = float(digits)
        except ValueError:
            return None
        return value if value > 0 else None
    return None


def _normalize_llm_round_type(raw: Any) -> str:
    """Map an LLM round_type string onto the canonical vocabulary."""
    if not isinstance(raw, str) or not raw.strip():
        return "unknown"

    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"_(round|rodada|ronda)$", "", normalized)
    normalized = normalized.replace("é", "e")

    match = re.match(r"^(?:series|serie)_([a-g])$", normalized)
    if match:
        return f"series_{match.group(1)}"

    if normalized in ("preseed",):
        return "pre_seed"

    return normalized if normalized in _VALID_ROUND_TYPES else "unknown"


def _parse_llm_extraction(raw_response: str) -> Optional[Dict[str, Any]]:
    """Parse and validate the LLM's JSON extraction payload.

    Returns None when the response is unparseable, when the LLM rejects
    the item (``is_funding_event`` false), or when the extracted fields
    are too incomplete to be useful (company + amount OR company +
    known round type are the minimum).
    """
    try:
        data = json.loads(strip_code_fences(raw_response))
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.debug("LLM extraction returned non-JSON payload: %s", raw_response[:200])
        return None

    if not isinstance(data, dict):
        return None

    if not data.get("is_funding_event"):
        return None

    company_name = str(data.get("company_name") or "").strip()
    if len(company_name) < 2:
        return None

    amount = _coerce_amount(data.get("amount"))
    round_type = _normalize_llm_round_type(data.get("round_type"))
    if amount is None and round_type == "unknown":
        logger.debug("LLM extraction too incomplete for %s, dropping", company_name)
        return None

    currency = str(data.get("currency") or "USD").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        currency = "USD"

    raw_investors = data.get("investors")
    investors: List[str] = []
    if isinstance(raw_investors, list):
        investors = [str(i).strip() for i in raw_investors if str(i).strip()][:8]

    return {
        "company_name": company_name,
        "amount": amount,
        "currency": currency,
        "round_type": round_type,
        "lead_investors": investors,
        "extraction_method": EXTRACTION_METHOD_LLM,
    }


@dataclass
class LLMFundingExtractor:
    """Budgeted LLM extraction of funding events from free-form text.

    Wraps :class:`~apps.agents.base.llm.LLMClient` with two guards:

    1. A keyword pre-filter (``looks_like_funding_news``) so unrelated
       items never reach the API.
    2. A per-run call budget (``max_calls``) so a noisy feed cannot burn
       an unbounded number of tokens.

    All failures (missing API key, budget exhausted, API error, bad JSON)
    degrade to ``None`` — collection continues without the item.
    """

    client: Optional[LLMClient] = None
    max_calls: int = DEFAULT_LLM_EXTRACTION_BUDGET
    calls_used: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = LLMClient(LLMConfig(max_tokens=400, temperature=0.0))

    @property
    def is_available(self) -> bool:
        """True when an LLM call can still be made in this run."""
        return bool(
            self.client is not None
            and self.client.is_available
            and self.calls_used < self.max_calls
        )

    def extract(self, title: str, body: str = "") -> Optional[Dict[str, Any]]:
        """Extract funding fields from an item, or None.

        Args:
            title: Item title.
            body: Item summary/body text (truncated before sending).

        Returns:
            Dict with company_name, amount, currency, round_type,
            lead_investors and extraction_method — or None.
        """
        if not self.is_available:
            return None
        if not looks_like_funding_news(title, body):
            return None

        self.calls_used += 1
        prompt = _LLM_EXTRACTION_PROMPT.format(
            title=title[:300], body=(body or "")[:2000]
        )

        try:
            raw = self.client.generate(  # type: ignore[union-attr]
                user_prompt=prompt,
                system_prompt=_LLM_EXTRACTION_SYSTEM_PROMPT,
                max_tokens=400,
                temperature=0.0,
            )
        except Exception as e:  # noqa: BLE001 — one bad item must not stop the run
            logger.warning("LLM funding extraction failed for %r: %s", title[:80], e)
            return None

        if not raw:
            return None

        fields = _parse_llm_extraction(raw)
        if fields is not None:
            logger.info(
                "LLM fallback extracted funding event: %s (%s)",
                fields["company_name"],
                fields["round_type"],
            )
        return fields


def extract_funding_fields(
    title: str,
    body: str = "",
    extractor: Optional["LLMFundingExtractor"] = None,
) -> Optional[Dict[str, Any]]:
    """Extract funding fields from an item: regex first, LLM second.

    Args:
        title: Item title.
        body: Item summary/body text.
        extractor: Optional budgeted LLM extractor used when the title
            regex misses. Without it, behaviour is the legacy
            regex-only one.

    Returns:
        Dict with company_name, amount, currency, round_type,
        lead_investors, extraction_method — or None if nothing usable
        could be extracted.
    """
    title_info = extract_funding_from_title(title)
    if title_info:
        content_info = extract_funding_from_content(body or "")
        return {
            "company_name": title_info.get("company_name", "Unknown Company"),
            "amount": title_info.get("amount"),
            "currency": title_info.get("currency", "USD"),
            "round_type": (
                title_info.get("round_type") or content_info.get("round_type", "unknown")
            ),
            "lead_investors": content_info.get("lead_investors", []),
            "extraction_method": EXTRACTION_METHOD_REGEX,
        }

    if extractor is None:
        logger.debug("No funding info in title: %s", title)
        return None

    return extractor.extract(title, body or "")


def build_funding_event(
    title: str,
    body: str,
    url: str,
    source_name: str,
    announced_date: Optional[date] = None,
    extractor: Optional["LLMFundingExtractor"] = None,
) -> Optional[FundingEvent]:
    """Build a FundingEvent from raw item text (shared by all source types).

    Args:
        title: Item title.
        body: Item summary/body text.
        url: Canonical item URL (used as source_url).
        source_name: Name of the data source.
        announced_date: Publication/announcement date, if known.
        extractor: Optional LLM extractor for the regex-miss fallback.

    Returns:
        FundingEvent or None when the item is not a usable funding event.
    """
    if not title or not url:
        return None

    fields = extract_funding_fields(title, body, extractor)
    if fields is None:
        return None

    amount = fields.get("amount")
    currency = fields.get("currency", "USD")

    return FundingEvent(
        company_name=fields["company_name"],
        round_type=fields.get("round_type") or "unknown",
        amount_usd=amount if currency == "USD" else None,
        amount_local=amount if currency != "USD" else None,
        currency=currency,
        announced_date=announced_date,
        lead_investors=fields.get("lead_investors", []),
        source_url=url,
        source_name=source_name,
        notes=clean_rss_notes(body[:500]) if body else None,
        extraction_method=fields["extraction_method"],
    )


def parse_funding_event(
    entry: Any,
    source_name: str,
    extractor: Optional[LLMFundingExtractor] = None,
) -> Optional[FundingEvent]:
    """Parse a single RSS feed entry into a FundingEvent.

    Extracts company name, funding amount, round type, investors,
    and dates from the entry title and content. Falls back to LLM
    extraction when the title regex misses and ``extractor`` is given.

    Args:
        entry: feedparser entry object
        source_name: Name of the data source
        extractor: Optional budgeted LLM extractor

    Returns:
        FundingEvent or None if parsing fails
    """
    title = getattr(entry, "title", "")
    link = getattr(entry, "link", "")
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

    if not title or not link:
        return None

    return build_funding_event(
        title=title,
        body=summary,
        url=link,
        source_name=source_name,
        announced_date=parse_feed_date(entry),
        extractor=extractor,
    )


def fetch_feed(
    source: DataSourceConfig,
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
    extractor: Optional[LLMFundingExtractor] = None,
) -> List[FundingEvent]:
    """Fetch and parse a single RSS/Atom feed.

    Args:
        source: Data source configuration
        provenance: Provenance tracker
        agent_name: Name of the agent
        run_id: Current run ID
        extractor: Optional budgeted LLM extractor for regex misses

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
            event = parse_funding_event(entry, source.name, extractor=extractor)
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


def _load_from_funding_rounds_table(days_back: int = 14) -> List[FundingEvent]:
    """Load pre-collected funding events from the funding_rounds DB table.

    The collect_funding.py daemon populates this table from Coresignal,
    NeoFeed, Bloomberg, etc. This function reads recent entries and
    converts them to FundingEvent objects for the FUNDING agent pipeline.
    """
    try:
        from packages.database.session import get_session
        from packages.database.models.funding_round import FundingRound
        from datetime import timedelta

        session = get_session()
        cutoff = date.today() - timedelta(days=days_back)

        rows = (
            session.query(FundingRound)
            .filter(FundingRound.announced_date >= cutoff)
            .order_by(FundingRound.announced_date.desc())
            .limit(50)
            .all()
        )

        events = []
        for row in rows:
            events.append(FundingEvent(
                company_name=row.company_name,
                company_slug=row.company_slug,
                round_type=row.round_type,
                amount_usd=row.amount_usd,
                amount_local=row.amount_local,
                currency=row.currency or "USD",
                announced_date=row.announced_date,
                lead_investors=row.lead_investors or [],
                participants=row.participants or [],
                source_url=row.source_url or "",
                source_name=row.source_name or "funding_rounds_db",
                notes=row.notes,
                extraction_method=EXTRACTION_METHOD_DATABASE,
            ))

        session.close()
        logger.info("Loaded %d events from funding_rounds table (last %d days)", len(events), days_back)
        return events

    except Exception as e:
        logger.warning("Could not load from funding_rounds table: %s", e)
        return []


def collect_all_sources(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
    extractor: Optional[LLMFundingExtractor] = None,
) -> List[FundingEvent]:
    """Collect funding events from all configured sources.

    Args:
        sources: List of data source configurations
        provenance: Provenance tracker
        agent_name: Name of the agent
        run_id: Current run ID
        extractor: Optional LLM extractor (one per run so the call
            budget is shared across every source). Defaults to a new
            budgeted extractor, which is inert without ANTHROPIC_API_KEY.

    Returns:
        List of all collected FundingEvent objects
    """
    all_events: List[FundingEvent] = []
    if extractor is None:
        extractor = LLMFundingExtractor()

    # Source 0: Pre-collected events from funding_rounds table
    # (populated by collect_funding.py daemon running 24/7)
    db_events = _load_from_funding_rounds_table(days_back=14)
    all_events.extend(db_events)
    for e in db_events:
        provenance.track(
            source_url=e.source_url,
            source_name=e.source_name,
            extraction_method="database",
        )

    for source in sources:
        if source.source_type == "rss" and "gnews" in source.name:
            # Google News: URL built from params at fetch time
            from apps.agents.sources.google_news import fetch_google_news

            with create_http_client() as client:
                rss_items = fetch_google_news(source, client)

            for rss_item in rss_items:
                event = build_funding_event(
                    title=rss_item.title,
                    body=rss_item.summary or "",
                    url=rss_item.url,
                    source_name=source.name,
                    announced_date=(
                        rss_item.published_at.date() if rss_item.published_at else None
                    ),
                    extractor=extractor,
                )
                if event:
                    all_events.append(event)
                    provenance.track(
                        source_url=rss_item.url,
                        source_name=source.name,
                        extraction_method="rss",
                    )
        elif source.source_type == "rss":
            events = fetch_feed(source, provenance, agent_name, run_id, extractor=extractor)
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
                    extraction_method=EXTRACTION_METHOD_API,
                )
                all_events.append(event)
                provenance.track(
                    source_url=r.source_url,
                    source_name=source.name,
                    extraction_method="api",
                )
        elif source.source_type == "api" and source.name in _API_SOURCES_HANDLED_SEPARATELY:
            # Collected after the main loop (needs the full company list).
            continue
        elif source.source_type == "api":
            logger.info("API source %s not yet implemented, skipping", source.name)
        else:
            logger.warning("Unknown source type %s for %s", source.source_type, source.name)

    # --- Verified Source: SEC Form D (needs company names from initial collection) ---
    sec_sources = [s for s in sources if s.name == "sec_form_d" and s.source_type == "api"]
    if sec_sources and all_events:
        company_names = list({e.company_name for e in all_events})[:20]
        try:
            from apps.agents.sources.sec_form_d import fetch_sec_form_d

            with create_http_client() as sec_client:
                filings = fetch_sec_form_d(sec_sources[0], sec_client, company_names)
            for f in filings:
                event = FundingEvent(
                    company_name=f.company_name,
                    round_type="unknown",
                    source_url=f.source_url,
                    source_name="sec_form_d",
                    amount_usd=f.amount_sold,
                    announced_date=f.date_filed,
                    notes=f"SEC CIK: {f.cik}",
                    extraction_method=EXTRACTION_METHOD_API,
                )
                all_events.append(event)
                provenance.track(
                    source_url=f.source_url,
                    source_name="sec_form_d",
                    extraction_method="api",
                )
            logger.info("Collected %d SEC Form D filings", len(filings))
        except Exception as e:
            logger.warning("SEC Form D collection failed (graceful degradation): %s", e)

    unique_events = deduplicate_by_hash(all_events, hash_fn=lambda e: e.content_hash)

    logger.info(
        "Collected %d unique funding events from %d sources (removed %d duplicates)",
        len(unique_events),
        len(sources),
        len(all_events) - len(unique_events),
    )

    return unique_events
