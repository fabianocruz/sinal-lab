"""Briefing data composer -- bridges agent ContentPiece records to BriefingData.

Reads the latest published ContentPiece for each agent, extracts structured
metadata, and builds the BriefingData dict expected by send_newsletter_email().
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from packages.database.models.content_piece import ContentPiece

logger = logging.getLogger(__name__)

# Base URL for building canonical links.
_BASE_URL = "https://sinal.tech"

# Portuguese month abbreviations (1-indexed: index 0 unused).
_PT_MONTHS = [
    "",
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
]

# All agent names queried for a complete briefing.
_AGENT_NAMES = ["sintese", "radar", "codigo", "funding", "mercado"]

# Round-type display mapping for funding deals.
_ROUND_TYPE_LABELS = {
    "seed": "Seed",
    "pre_seed": "Pre-Seed",
    "series_a": "Serie A",
    "series_b": "Serie B",
    "series_c": "Serie C",
    "series_d": "Serie D",
    "series_e": "Serie E",
    "bridge": "Bridge",
    "debt": "Debt",
    "grant": "Grant",
    "undisclosed": "N/D",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_latest_published(
    session: Session, agent_name: str
) -> Optional[ContentPiece]:
    """Return the most recently published ContentPiece for an agent.

    Args:
        session: SQLAlchemy database session.
        agent_name: Agent identifier (e.g. "sintese", "radar").

    Returns:
        The latest published ContentPiece, or None if none exists.
    """
    return (
        session.query(ContentPiece)
        .filter(
            ContentPiece.agent_name == agent_name,
            ContentPiece.review_status == "published",
        )
        .order_by(desc(ContentPiece.published_at))
        .first()
    )


def _compute_date_range(week: int) -> str:
    """Build a Portuguese date range string from an ISO week number.

    Uses the current year. Returns a string like "3-10 Fev 2026".

    Args:
        week: ISO week number (1-53).

    Returns:
        Formatted date range in Portuguese.
    """
    year = datetime.utcnow().year
    # Monday of the given ISO week.
    monday = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
    sunday = monday + timedelta(days=6)

    start_month = _PT_MONTHS[monday.month]
    end_month = _PT_MONTHS[sunday.month]

    if monday.month == sunday.month:
        return "{0}\u2013{1} {2} {3}".format(
            monday.day, sunday.day, end_month, year
        )
    return "{0} {1}\u2013{2} {3} {4}".format(
        monday.day, start_month, sunday.day, end_month, year
    )


def _format_amount(amount_usd: Optional[float]) -> str:
    """Format a USD amount into a compact human-readable string.

    Args:
        amount_usd: Dollar amount (e.g. 50_000_000). May be None or zero.

    Returns:
        Compact string like "$50M", "$2.8M", "$500K", or "N/A".
    """
    if not amount_usd:
        return "N/A"

    if amount_usd >= 1_000_000_000:
        value = amount_usd / 1_000_000_000
        if value == int(value):
            return "${0}B".format(int(value))
        return "${0:.1f}B".format(value)

    if amount_usd >= 1_000_000:
        value = amount_usd / 1_000_000
        if value == int(value):
            return "${0}M".format(int(value))
        return "${0:.1f}M".format(value)

    if amount_usd >= 1_000:
        value = amount_usd / 1_000
        if value == int(value):
            return "${0}K".format(int(value))
        return "${0:.1f}K".format(value)

    return "${0}".format(int(amount_usd))


def _extract_radar_trends(metadata: dict) -> List[dict]:
    """Extract radar trend dicts from agent metadata.

    Maps each item in metadata["items"] to a dict compatible with the
    RadarTrend TypedDict. Limits output to the first 5 items.

    Args:
        metadata: The ContentPiece.metadata_ dict for a radar agent.

    Returns:
        List of trend dicts with arrow, arrow_color, title, context, and
        optional url, source_name, metrics fields.
    """
    items = metadata.get("items", [])
    trends = []  # type: List[dict]

    for item in items[:5]:
        momentum = item.get("momentum_score", 0.0) or 0.0
        if momentum >= 0.3:
            arrow = "\u2191"
            arrow_color = "#59FFB4"
        else:
            arrow = "\u2193"
            arrow_color = "#FF8A59"

        trend = {
            "arrow": arrow,
            "arrow_color": arrow_color,
            "title": item.get("title", ""),
            "context": item.get("summary", ""),
        }  # type: Dict[str, object]

        url = item.get("url")
        if url:
            trend["url"] = url

        source_name = item.get("source_name")
        if source_name:
            trend["source_name"] = source_name

        item_metrics = item.get("metrics")
        if item_metrics:
            trend["metrics"] = item_metrics

        trends.append(trend)

    return trends


def _extract_funding_deals(metadata: dict) -> List[dict]:
    """Extract funding deal dicts from agent metadata.

    Maps each item in metadata["items"] to a dict compatible with the
    FundingDeal TypedDict. Limits output to the first 5 items.

    Args:
        metadata: The ContentPiece.metadata_ dict for a funding agent.

    Returns:
        List of deal dicts with stage, description, and optional
        source_url, company_name, lead_investors, country fields.
    """
    items = metadata.get("items", [])
    deals = []  # type: List[dict]

    for item in items[:5]:
        raw_round = item.get("round_type", "undisclosed") or "undisclosed"
        stage = _ROUND_TYPE_LABELS.get(raw_round, raw_round.replace("_", " ").title())

        company_name = item.get("company_name", "N/A")
        # Funding agent stores amounts in millions (8.0 = $8M).
        raw_amount = item.get("amount_usd")
        abs_amount = raw_amount * 1_000_000 if raw_amount else None
        amount_str = _format_amount(abs_amount)
        investors = item.get("lead_investors", []) or []
        investors_str = " + ".join(investors) if investors else "N/D"

        description = "{0} \u00b7 {1} \u00b7 {2}".format(
            company_name, amount_str, investors_str
        )

        deal = {
            "stage": stage,
            "description": description,
        }  # type: Dict[str, object]

        source_url = item.get("source_url")
        if source_url:
            deal["source_url"] = source_url

        if company_name != "N/A":
            deal["company_name"] = company_name

        if investors:
            deal["lead_investors"] = investors

        country = item.get("country")
        if country:
            deal["country"] = country

        deals.append(deal)

    return deals


def _extract_mercado_movements(metadata: dict) -> List[dict]:
    """Extract market movement dicts from agent metadata.

    Maps each item in metadata["items"] to a dict compatible with the
    MercadoMovement TypedDict. Limits output to the first 5 items.

    Args:
        metadata: The ContentPiece.metadata_ dict for a mercado agent.

    Returns:
        List of movement dicts with type, description, and optional
        source_url, company_name, sector, country fields.
    """
    items = metadata.get("items", [])
    movements = []  # type: List[dict]

    for item in items[:5]:
        company_name = item.get("company_name", "N/A")
        country = item.get("country", "")
        sector = item.get("sector", "")

        parts = [company_name]
        if country:
            parts[0] = "{0} ({1})".format(company_name, country)
        if sector:
            parts.append(sector)
        description = " \u00b7 ".join(parts)

        movement = {
            "type": "Discovery",
            "description": description,
        }  # type: Dict[str, object]

        source_url = item.get("source_url")
        if source_url:
            movement["source_url"] = source_url

        if company_name != "N/A":
            movement["company_name"] = company_name

        if sector:
            movement["sector"] = sector

        if country:
            movement["country"] = country

        website = item.get("website")
        if website:
            movement["company_url"] = website

        movements.append(movement)

    return movements


def _extract_sintese_paragraphs(body_md: str) -> List[str]:
    """Extract the first 3 content paragraphs from a Markdown body.

    Splits on double newlines and filters out headings (lines starting with
    '#'), emphasis-only lines (lines starting with '*'), horizontal rules
    ('---'), blockquotes ('>'), images ('!['), and bold-prefixed numbered
    items ('**1.').

    Args:
        body_md: Markdown content body.

    Returns:
        Up to 3 non-empty paragraph strings.
    """
    if not body_md:
        return []

    blocks = body_md.split("\n\n")
    paragraphs = []  # type: List[str]

    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        # Skip markdown structural elements and non-prose blocks.
        if stripped.startswith("#"):
            continue
        if stripped.startswith("*") and not stripped.startswith("* "):
            continue
        if stripped == "---" or stripped == "***" or stripped == "___":
            continue
        if stripped.startswith(">"):
            continue
        if stripped.startswith("!["):
            continue
        if stripped.startswith("**") and len(stripped) > 3 and stripped[2].isdigit():
            continue
        paragraphs.append(stripped)
        if len(paragraphs) >= 3:
            break

    return paragraphs


def _extract_sintese_sources(metadata: dict) -> List[Dict[str, str]]:
    """Extract source attribution list from sintese agent metadata.

    Maps top items to [{"name": source_name, "url": url}] for the
    sintese_source_urls optional field.

    Args:
        metadata: The ContentPiece.metadata_ dict for a sintese agent.

    Returns:
        List of dicts with "name" and "url" keys.
    """
    items = metadata.get("items", [])
    sources = []  # type: List[Dict[str, str]]

    for item in items:
        name = item.get("source_name", "")
        url = item.get("url", "")
        if name and url:
            sources.append({"name": name, "url": url})

    return sources


# ---------------------------------------------------------------------------
# Main composer
# ---------------------------------------------------------------------------


def compose_briefing_data(
    session: Session,
    edition: int,
    week: int,
    date_range: str = "",
) -> Optional[dict]:
    """Compose a BriefingData-compatible dict from published ContentPieces.

    Queries the latest published ContentPiece for each of the 5 agents
    (sintese, radar, codigo, funding, mercado). SINTESE is required --
    returns None if no published sintese piece exists. Other agents degrade
    gracefully with sensible defaults.

    Args:
        session: SQLAlchemy database session.
        edition: Edition number for the briefing (e.g. 48).
        week: ISO week number (e.g. 7).
        date_range: Pre-formatted date range string. When empty, one is
            computed from the week number.

    Returns:
        A dict conforming to the BriefingData structure, or None if no
        published SINTESE piece is available.
    """
    # Fetch latest published piece for each agent.
    pieces = {}  # type: Dict[str, ContentPiece]
    for agent in _AGENT_NAMES:
        piece = _get_latest_published(session, agent)
        if piece:
            pieces[agent] = piece

    sintese = pieces.get("sintese")
    if not sintese:
        logger.warning(
            "No published SINTESE piece found; cannot compose briefing #%d",
            edition,
        )
        return None

    paragraphs = _extract_sintese_paragraphs(sintese.body_md)

    data = {
        "edition_number": edition,
        "week_number": week,
        "date_range": date_range or _compute_date_range(week),
        "preview_text": sintese.summary or sintese.title[:100],
        "opening_headline": sintese.title,
        "opening_body": paragraphs[0] if paragraphs else "",
        # SINTESE
        "sintese_title": sintese.title,
        "sintese_paragraphs": paragraphs,
        "sintese_dq": "{0:.1f}/5".format(sintese.confidence_dq or 0),
        "sintese_sources": len(sintese.sources or []),
    }  # type: Dict[str, object]

    # CTA link to the full article on the site.
    data["sintese_cta_url"] = "{0}/newsletter/{1}".format(
        _BASE_URL, sintese.slug
    )
    data["sintese_cta_label"] = "Ler edicao completa"

    # Sintese rich fields from metadata.
    if sintese.metadata_:
        source_urls = _extract_sintese_sources(sintese.metadata_)
        if source_urls:
            data["sintese_source_urls"] = source_urls

    # -----------------------------------------------------------------
    # RADAR
    # -----------------------------------------------------------------
    radar = pieces.get("radar")
    if radar:
        radar_meta = radar.metadata_ or {}
        data["radar_title"] = radar.title
        data["radar_trends"] = (
            _extract_radar_trends(radar_meta) if radar_meta else []
        )
        data["radar_dq"] = "{0:.1f}/5".format(radar.confidence_dq or 0)
        data["radar_sources"] = len(radar.sources or [])
    else:
        data["radar_title"] = "Tendencias da semana"
        data["radar_trends"] = []
        data["radar_dq"] = "N/A"
        data["radar_sources"] = 0

    # -----------------------------------------------------------------
    # CODIGO
    # -----------------------------------------------------------------
    codigo = pieces.get("codigo")
    if codigo:
        data["codigo_title"] = codigo.title
        data["codigo_body"] = codigo.summary or (
            paragraphs[0] if paragraphs else ""
        )
        data["codigo_url"] = "{0}/codigo/{1}".format(_BASE_URL, codigo.slug)
        if codigo.metadata_:
            items = codigo.metadata_.get("items", [])
            if items:
                top = items[0]
                if top.get("metrics"):
                    data["codigo_metrics"] = top["metrics"]
                if top.get("language"):
                    data["codigo_language"] = top["language"]
                if top.get("url"):
                    data["codigo_repo_url"] = top["url"]
    else:
        data["codigo_title"] = "Codigo & Infraestrutura"
        data["codigo_body"] = ""
        data["codigo_url"] = "{0}/newsletter".format(_BASE_URL)

    # -----------------------------------------------------------------
    # FUNDING
    # -----------------------------------------------------------------
    funding = pieces.get("funding")
    if funding:
        f_meta = funding.metadata_ or {}
        deals = _extract_funding_deals(f_meta) if f_meta else []
        item_count = f_meta.get("item_count", len(deals))
        # Funding agent stores amounts in millions (8.0 = $8M).
        # Convert to absolute USD so _format_amount displays correctly.
        total_millions = f_meta.get("funding_total_usd", 0) or 0
        total_usd = total_millions * 1_000_000
        data["funding_count"] = item_count
        data["funding_total"] = _format_amount(total_usd)
        data["funding_score"] = "{0:.1f}/5".format(
            funding.confidence_dq or 0
        )
        data["funding_deals"] = deals
        data["funding_remaining"] = max(0, item_count - len(deals))
        data["funding_url"] = "{0}/funding/{1}".format(
            _BASE_URL, funding.slug
        )
    else:
        data["funding_count"] = 0
        data["funding_total"] = "$0"
        data["funding_score"] = "N/A"
        data["funding_deals"] = []
        data["funding_remaining"] = 0
        data["funding_url"] = "{0}/newsletter".format(_BASE_URL)

    # -----------------------------------------------------------------
    # MERCADO
    # -----------------------------------------------------------------
    mercado = pieces.get("mercado")
    if mercado:
        m_meta = mercado.metadata_ or {}
        movements = _extract_mercado_movements(m_meta) if m_meta else []
        item_count = m_meta.get("item_count", len(movements))
        data["mercado_count"] = item_count
        data["mercado_score"] = "{0:.1f}/5".format(
            mercado.confidence_dq or 0
        )
        data["mercado_movements"] = movements
        data["mercado_remaining"] = max(0, item_count - len(movements))
        data["mercado_url"] = "{0}/mercado/{1}".format(
            _BASE_URL, mercado.slug
        )
    else:
        data["mercado_count"] = 0
        data["mercado_score"] = "N/A"
        data["mercado_movements"] = []
        data["mercado_remaining"] = 0
        data["mercado_url"] = "{0}/newsletter".format(_BASE_URL)

    return data
