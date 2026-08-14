"""Tests for the Grok Live Search funding source.

The payload fixtures mirror a real xAI ``POST /v1/responses`` response
captured on 2026-08-13: ``output`` is a list mixing ``reasoning``,
``web_search_call`` and ``message`` items; the message content carries
``output_text`` plus ``url_citation`` annotations.
"""

import json
import os
from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.grok_search import (
    GROK_RESPONSES_ENDPOINT,
    GrokFundingEvent,
    build_funding_query,
    fetch_grok_funding_rounds,
)

VALID_EVENTS_JSON = json.dumps({
    "events": [
        {
            "company_name": "Kesh",
            "amount": 110000000,
            "currency": "USD",
            "round_type": "Series B",
            "investors": ["Grupo Leste", "BR Angels"],
            "source_url": "https://www.thesaasnews.com/news/kesh-raises-110m/",
            "country": "BR",
            "announced_date": "2026-08-06",
        },
        {
            "company_name": "Plinq",
            "amount": 254000,
            "currency": "USD",
            "round_type": "seed",
            "investors": ["Spectra Investments"],
            "source_url": "",
            "country": "BR",
            "announced_date": "2026-08-07",
        },
    ]
})


def _response_payload(
    text: str = VALID_EVENTS_JSON,
    citations: Optional[List[str]] = None,
    include_message: bool = True,
) -> Dict[str, Any]:
    """Build a Grok responses payload around a message text."""
    citations = citations if citations is not None else [
        "https://latamlist.com/kesh-raises-110m/",
    ]
    output: List[Dict[str, Any]] = [
        {"id": "rs_1", "type": "reasoning", "summary": [], "status": "completed"},
        {
            "id": "ws_1",
            "type": "web_search_call",
            "status": "completed",
            "action": {"type": "search", "query": "latam funding"},
        },
    ]
    if include_message:
        output.append({
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{
                "type": "output_text",
                "text": text,
                "logprobs": [],
                "annotations": [
                    {"type": "url_citation", "url": url, "title": url}
                    for url in citations
                ],
            }],
        })
    return {
        "id": "resp_1",
        "model": "grok-4.3",
        "status": "completed",
        "output": output,
        "usage": {"total_tokens": 32493},
    }


def _mock_client(
    payload: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    side_effect: Optional[Exception] = None,
    json_error: bool = False,
) -> MagicMock:
    """Build a mock httpx.Client for the Grok endpoint."""
    client = MagicMock(spec=httpx.Client)
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code

    if json_error:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = payload if payload is not None else _response_payload()

    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status.return_value = None

    if side_effect is not None:
        client.post.side_effect = side_effect
    else:
        client.post.return_value = response
    return client


def _source() -> DataSourceConfig:
    return DataSourceConfig(
        name="grok_live_search",
        source_type="api",
        url=GROK_RESPONSES_ENDPOINT,
        api_key_env="XAI_API_KEY",
        params={"model": "grok-4.3", "days_back": 7},
    )


@pytest.fixture
def with_api_key():
    with patch.dict(os.environ, {"XAI_API_KEY": "xai-test-key"}):
        yield


class TestBuildFundingQuery:
    """The prompt must ask for LATAM rounds and a strict JSON answer."""

    def test_mentions_latam_countries_and_window(self) -> None:
        query = build_funding_query(days_back=7)

        assert "7" in query
        assert "Brasil" in query
        assert "México" in query or "Mexico" in query

    def test_requests_json_only(self) -> None:
        query = build_funding_query(days_back=7)

        assert "JSON" in query
        assert "events" in query


class TestFetchGrokFundingRounds:
    """Happy path, degradation and payload edge cases."""

    def test_parses_events_with_citations(self, with_api_key) -> None:
        client = _mock_client()

        events = fetch_grok_funding_rounds(_source(), client)

        assert len(events) == 2
        first = events[0]
        assert isinstance(first, GrokFundingEvent)
        assert first.company_name == "Kesh"
        assert first.amount == 110_000_000.0
        assert first.currency == "USD"
        assert first.round_type == "series_b"
        assert first.investors == ["Grupo Leste", "BR Angels"]
        assert first.source_url == "https://www.thesaasnews.com/news/kesh-raises-110m/"
        assert first.announced_date == date(2026, 8, 6)
        assert first.country == "BR"
        assert first.source_name == "grok_live_search"

    def test_falls_back_to_citation_url(self, with_api_key) -> None:
        """Events without their own URL inherit the first citation."""
        events = fetch_grok_funding_rounds(_source(), _mock_client())

        assert events[1].company_name == "Plinq"
        assert events[1].source_url == "https://latamlist.com/kesh-raises-110m/"

    def test_posts_to_the_responses_endpoint_with_web_search(self, with_api_key) -> None:
        client = _mock_client()

        fetch_grok_funding_rounds(_source(), client)

        args, kwargs = client.post.call_args
        assert args[0] == GROK_RESPONSES_ENDPOINT
        assert kwargs["headers"]["Authorization"] == "Bearer xai-test-key"
        body = kwargs["json"]
        assert body["model"] == "grok-4.3"
        assert body["input"][0]["role"] == "user"
        assert body["tools"][0]["type"] == "web_search"

    def test_missing_api_key_skips_gracefully(self) -> None:
        client = _mock_client()

        with patch.dict(os.environ, {}, clear=True):
            events = fetch_grok_funding_rounds(_source(), client)

        assert events == []
        client.post.assert_not_called()

    def test_network_error_returns_empty(self, with_api_key) -> None:
        client = _mock_client(side_effect=httpx.TimeoutException("timeout"))

        assert fetch_grok_funding_rounds(_source(), client) == []

    def test_http_status_error_returns_empty(self, with_api_key) -> None:
        client = _mock_client(status_code=429)

        assert fetch_grok_funding_rounds(_source(), client) == []

    def test_non_json_response_body_returns_empty(self, with_api_key) -> None:
        client = _mock_client(json_error=True)

        assert fetch_grok_funding_rounds(_source(), client) == []

    def test_missing_message_item_returns_empty(self, with_api_key) -> None:
        client = _mock_client(_response_payload(include_message=False))

        assert fetch_grok_funding_rounds(_source(), client) == []

    def test_non_json_message_text_returns_empty(self, with_api_key) -> None:
        client = _mock_client(_response_payload(text="Não encontrei rodadas."))

        assert fetch_grok_funding_rounds(_source(), client) == []

    def test_code_fenced_json_is_parsed(self, with_api_key) -> None:
        client = _mock_client(
            _response_payload(text=f"```json\n{VALID_EVENTS_JSON}\n```")
        )

        assert len(fetch_grok_funding_rounds(_source(), client)) == 2

    def test_empty_events_list_returns_empty(self, with_api_key) -> None:
        client = _mock_client(_response_payload(text=json.dumps({"events": []})))

        assert fetch_grok_funding_rounds(_source(), client) == []

    def test_events_without_company_name_are_dropped(self, with_api_key) -> None:
        payload_text = json.dumps({
            "events": [
                {"company_name": "", "amount": 1_000_000, "round_type": "seed"},
                {"company_name": "Zenpli", "amount": 6_500_000, "round_type": "seed"},
            ]
        })
        client = _mock_client(_response_payload(text=payload_text))

        events = fetch_grok_funding_rounds(_source(), client)

        assert [e.company_name for e in events] == ["Zenpli"]

    def test_events_without_amount_or_round_are_dropped(self, with_api_key) -> None:
        payload_text = json.dumps({
            "events": [
                {"company_name": "Vago", "amount": None, "round_type": "unknown"},
            ]
        })
        client = _mock_client(_response_payload(text=payload_text))

        assert fetch_grok_funding_rounds(_source(), client) == []

    def test_bad_announced_date_is_ignored(self, with_api_key) -> None:
        payload_text = json.dumps({
            "events": [{
                "company_name": "Zenpli",
                "amount": 6_500_000,
                "round_type": "seed",
                "announced_date": "semana passada",
            }]
        })
        client = _mock_client(_response_payload(text=payload_text))

        events = fetch_grok_funding_rounds(_source(), client)

        assert len(events) == 1
        assert events[0].announced_date is None

    def test_bare_list_payload_is_accepted(self, with_api_key) -> None:
        payload_text = json.dumps([
            {"company_name": "Zenpli", "amount": 6_500_000, "round_type": "seed"},
        ])
        client = _mock_client(_response_payload(text=payload_text))

        assert len(fetch_grok_funding_rounds(_source(), client)) == 1

    def test_custom_query_is_used(self, with_api_key) -> None:
        client = _mock_client()

        fetch_grok_funding_rounds(_source(), client, query="rodadas no Chile")

        body = client.post.call_args.kwargs["json"]
        assert body["input"][0]["content"] == "rodadas no Chile"
