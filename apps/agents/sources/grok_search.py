"""Shared Grok Live Search source for funding collection.

Uses xAI's Responses API with the server-side ``web_search`` tool to ask
Grok for LATAM funding rounds announced in the last N days, and parses
the answer into structured events.

Why this exists: the free RSS/HTML sources only see what a handful of
outlets publish in a feed. Grok's live search reaches the long tail
(regional outlets, press releases) without a paid deals database.

Response shape (verified against the live API on 2026-08-13)::

    {
      "status": "completed",
      "output": [
        {"type": "reasoning", ...},
        {"type": "web_search_call", "action": {"type": "search", ...}},
        {"type": "message", "role": "assistant", "content": [
            {"type": "output_text",
             "text": "<model answer>",
             "annotations": [
                {"type": "url_citation", "url": "https://...", "title": "..."}
             ]}
        ]}
      ],
      "usage": {...}
    }

The model is asked to answer with strict JSON, and the ``url_citation``
annotations are used as the source URL fallback when it omits one.

Requires ``XAI_API_KEY``. Without it the source skips itself with a
warning, like the other key-gated sources.

Usage:
    from apps.agents.sources.grok_search import fetch_grok_funding_rounds

    events = fetch_grok_funding_rounds(source_config, client)
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.llm import strip_code_fences
from apps.agents.sources.funding_normalize import (
    coerce_amount,
    normalize_round_type_token,
)

logger = logging.getLogger(__name__)

GROK_RESPONSES_ENDPOINT = "https://api.x.ai/v1/responses"

#: grok-4.3 supports the web_search tool and is the cheaper tier
#: ($1.25-2.50/1M input) compared to grok-4.6.
DEFAULT_GROK_MODEL = "grok-4.3"

#: Live search with tool calls takes ~60-120s; the shared client default
#: (15s) is far too short, so every request overrides it.
GROK_REQUEST_TIMEOUT = 240.0

_LATAM_COUNTRIES = "Brasil, México, Colômbia, Argentina, Chile, Peru e Uruguai"


@dataclass
class GrokFundingEvent:
    """A funding round reported by Grok Live Search.

    Mirrors the field set produced by FUNDING's LLM extraction so the
    collector can build a FundingEvent without extra mapping.
    ``amount`` is absolute in ``currency`` units (6_500_000 = US$ 6.5M).
    """

    company_name: str
    source_name: str
    amount: Optional[float] = None
    currency: str = "USD"
    round_type: str = "unknown"
    investors: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    announced_date: Optional[date] = None
    country: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            key = f"{self.company_name.lower().strip()}|{self.round_type}"
            self.content_hash = hashlib.md5(key.encode()).hexdigest()


def build_funding_query(days_back: int = 7) -> str:
    """Build the Live Search prompt for LATAM funding rounds.

    Args:
        days_back: Size of the lookback window, in days.

    Returns:
        Prompt string asking for a strict JSON answer.
    """
    return (
        f"Rodadas de investimento (funding rounds) anunciadas nos últimos {days_back} "
        f"dias envolvendo startups da América Latina ({_LATAM_COUNTRIES}). "
        "Para cada uma, informe: nome da empresa, valor captado, tipo de rodada "
        "(seed/Series A/B/C), investidores e a URL da notícia.\n\n"
        "Responda APENAS com JSON válido neste formato, sem texto ao redor:\n"
        '{"events": [{"company_name": "...", "amount": 6500000, "currency": "USD", '
        '"round_type": "seed|series_a|series_b|series_c|unknown", '
        '"investors": ["..."], "source_url": "https://...", "country": "BR", '
        '"announced_date": "2026-08-10"}]}\n\n'
        "Regras: use o valor absoluto na moeda informada (6500000 para US$ 6,5 milhões); "
        "use null quando o valor não for divulgado; não inclua rodadas fora da América "
        "Latina; não invente dados. Se não encontrar nada, responda {\"events\": []}."
    )


def _extract_message_content(payload: Dict[str, Any]) -> tuple:
    """Pull the assistant text and citation URLs out of a response payload.

    Args:
        payload: Parsed JSON body of the Responses API call.

    Returns:
        Tuple of (text, citation_urls). Text is "" when the payload has
        no assistant message (e.g. the run stopped at a tool call).
    """
    output = payload.get("output")
    if not isinstance(output, list):
        return "", []

    texts: List[str] = []
    citations: List[str] = []

    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)
            for annotation in block.get("annotations") or []:
                if not isinstance(annotation, dict):
                    continue
                url = annotation.get("url")
                if annotation.get("type") == "url_citation" and url:
                    citations.append(str(url))

    return "\n".join(texts), citations


def _parse_announced_date(raw: Any) -> Optional[date]:
    """Parse an ISO-ish date string, or None."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.strip().replace("Z", "+00:00")).date()
    except ValueError:
        logger.debug("Grok returned unparseable date: %r", raw)
        return None


def _parse_events(
    text: str,
    citations: List[str],
    source_name: str,
) -> List[GrokFundingEvent]:
    """Parse the model's JSON answer into GrokFundingEvent objects.

    Events missing a company name, or with neither an amount nor a known
    round type, are dropped — they carry no usable signal.
    """
    try:
        data = json.loads(strip_code_fences(text))
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning(
            "Grok returned a non-JSON answer for %s: %s", source_name, text[:200]
        )
        return []

    if isinstance(data, dict):
        raw_events = data.get("events")
    elif isinstance(data, list):
        raw_events = data
    else:
        raw_events = None

    if not isinstance(raw_events, list):
        logger.warning("Grok payload for %s has no events list", source_name)
        return []

    fallback_url = citations[0] if citations else None

    events: List[GrokFundingEvent] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue

        company_name = str(raw.get("company_name") or "").strip()
        if len(company_name) < 2:
            continue

        amount = coerce_amount(raw.get("amount"))
        round_type = normalize_round_type_token(raw.get("round_type"))
        if amount is None and round_type == "unknown":
            logger.debug("Grok event for %s has no usable data, skipping", company_name)
            continue

        currency = str(raw.get("currency") or "USD").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            currency = "USD"

        raw_investors = raw.get("investors")
        investors: List[str] = []
        if isinstance(raw_investors, list):
            investors = [str(i).strip() for i in raw_investors if str(i).strip()][:8]

        source_url = str(raw.get("source_url") or "").strip() or fallback_url

        events.append(GrokFundingEvent(
            company_name=company_name,
            source_name=source_name,
            amount=amount,
            currency=currency,
            round_type=round_type,
            investors=investors,
            source_url=source_url,
            announced_date=_parse_announced_date(raw.get("announced_date")),
            country=str(raw.get("country") or "").strip() or None,
        ))

    return events


def fetch_grok_funding_rounds(
    source: DataSourceConfig,
    client: httpx.Client,
    query: Optional[str] = None,
) -> List[GrokFundingEvent]:
    """Ask Grok Live Search for recent LATAM funding rounds.

    Never raises: a missing API key, a network failure, an HTTP error or
    an unparseable answer all return an empty list so the collection run
    continues.

    Args:
        source: DataSourceConfig. ``api_key_env`` names the env var
            (default XAI_API_KEY); ``params`` may set ``model`` and
            ``days_back``.
        client: Configured httpx.Client.
        query: Optional prompt override (defaults to
            :func:`build_funding_query`).

    Returns:
        List of GrokFundingEvent. Empty list on any failure.
    """
    api_key_env = source.api_key_env or "XAI_API_KEY"
    api_key = os.getenv(api_key_env)
    if not api_key:
        logger.warning(
            "%s not set, skipping Grok Live Search for %s", api_key_env, source.name
        )
        return []

    model = source.params.get("model", DEFAULT_GROK_MODEL)
    days_back = source.params.get("days_back", 7)
    prompt = query or build_funding_query(days_back=days_back)

    body = {
        "model": model,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{
            "type": "web_search",
            "enable_image_understanding": False,
            "enable_image_search": False,
        }],
    }
    allowed_domains = source.params.get("allowed_domains")
    if allowed_domains:
        body["tools"][0]["filters"] = {"allowed_domains": list(allowed_domains)}

    try:
        response = client.post(
            source.url or GROK_RESPONSES_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=GROK_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("Grok Live Search request failed for %s: %s", source.name, e)
        return []
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Grok Live Search returned invalid JSON for %s: %s", source.name, e)
        return []

    if not isinstance(payload, dict):
        logger.warning("Grok Live Search returned unexpected payload for %s", source.name)
        return []

    text, citations = _extract_message_content(payload)
    if not text:
        logger.warning(
            "Grok Live Search returned no assistant message for %s (status=%s)",
            source.name, payload.get("status"),
        )
        return []

    events = _parse_events(text, citations, source.name)
    logger.info(
        "Grok Live Search returned %d funding events for %s (%d citations)",
        len(events), source.name, len(citations),
    )
    return events
