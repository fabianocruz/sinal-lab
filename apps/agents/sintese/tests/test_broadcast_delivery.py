"""Tests for send_broadcast — the two-step Resend Broadcasts call.

Edition 65 (2026-08-19) was refused with a bare 422 on POST /broadcasts/{id}/send
right after the draft was created; the script logged only the status code and
gave up, while the draft itself was fine and went out from the dashboard. These
tests pin the behaviour that would have made that a non-event: surface Resend's
error message, retry /send on 422, and point the operator at the surviving draft.

Run: pytest apps/agents/sintese/tests/test_broadcast_delivery.py -v
"""

import logging
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

import apps.api.config as api_config
from apps.agents.sintese import newsletter

BROADCAST_ID = "df6b99c3-c010-4131-bcbd-efaa71d44150"
CREATE_URL = "https://api.resend.com/broadcasts"
SEND_URL = f"https://api.resend.com/broadcasts/{BROADCAST_ID}/send"


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or (str(payload) if payload is not None else "")

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.resend.com/x")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)


def _created() -> _FakeResponse:
    return _FakeResponse(200, {"object": "broadcast", "id": BROADCAST_ID})


def _sent() -> _FakeResponse:
    return _FakeResponse(200, {"object": "broadcast", "id": BROADCAST_ID})


def _refused(message: str = "The broadcast is not ready to be sent") -> _FakeResponse:
    return _FakeResponse(
        422, {"statusCode": 422, "name": "validation_error", "message": message}
    )


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        resend_api_key="re_test",
        resend_audience_id="aud_test",
        resend_from_email="Sinal Briefing <news@sinal.tech>",
    )
    monkeypatch.setattr(api_config, "get_settings", lambda: settings)
    # No real waiting between retries.
    monkeypatch.setattr(newsletter, "_SEND_RETRY_DELAYS", (0.0, 0.0))


@pytest.fixture
def posts(monkeypatch: pytest.MonkeyPatch):
    """Queue of fake responses for httpx.post, in call order; records calls."""
    queue: list[_FakeResponse] = []
    calls: list[str] = []

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        calls.append(url)
        if not queue:
            raise AssertionError(f"unexpected POST {url}")
        return queue.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)
    return SimpleNamespace(queue=queue, calls=calls)


class TestSendBroadcastHappyPath:
    def test_creates_then_sends(self, configured, posts) -> None:
        posts.queue.extend([_created(), _sent()])
        assert newsletter.send_broadcast("<p>hi</p>", "Subject") is True
        assert posts.calls == [CREATE_URL, SEND_URL]


class TestSendBroadcastRetriesOn422:
    def test_retries_send_until_resend_accepts(self, configured, posts, caplog) -> None:
        posts.queue.extend([_created(), _refused(), _refused(), _sent()])
        with caplog.at_level(logging.WARNING, logger=newsletter.logger.name):
            assert newsletter.send_broadcast("<p>hi</p>", "Subject") is True
        assert posts.calls == [CREATE_URL, SEND_URL, SEND_URL, SEND_URL]
        assert "not ready to be sent" in caplog.text

    def test_gives_up_and_points_at_the_surviving_draft(self, configured, posts, caplog) -> None:
        posts.queue.extend([_created(), _refused(), _refused(), _refused()])
        with caplog.at_level(logging.ERROR, logger=newsletter.logger.name):
            assert newsletter.send_broadcast("<p>hi</p>", "Subject") is False
        assert posts.calls.count(SEND_URL) == 3
        assert BROADCAST_ID in caplog.text
        assert "dashboard" in caplog.text.lower()

    def test_does_not_retry_other_send_errors(self, configured, posts, caplog) -> None:
        posts.queue.extend([_created(), _FakeResponse(500, text="upstream down")])
        with caplog.at_level(logging.ERROR, logger=newsletter.logger.name):
            assert newsletter.send_broadcast("<p>hi</p>", "Subject") is False
        assert posts.calls == [CREATE_URL, SEND_URL]
        assert "upstream down" in caplog.text


class TestSendBroadcastErrorReporting:
    def test_logs_resend_message_when_create_is_refused(self, configured, posts, caplog) -> None:
        posts.queue.append(_refused("Invalid `from` field."))
        with caplog.at_level(logging.ERROR, logger=newsletter.logger.name):
            assert newsletter.send_broadcast("<p>hi</p>", "Subject") is False
        assert "Invalid `from` field." in caplog.text
        assert posts.calls == [CREATE_URL]

    def test_skips_when_audience_not_configured(self, monkeypatch, posts) -> None:
        settings = SimpleNamespace(
            resend_api_key="re_test", resend_audience_id="", resend_from_email="x@y.z"
        )
        monkeypatch.setattr(api_config, "get_settings", lambda: settings)
        assert newsletter.send_broadcast("<p>hi</p>", "Subject") is False
        assert posts.calls == []
