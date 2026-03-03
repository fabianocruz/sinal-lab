"""Tests for cover image prompt generator."""

from unittest.mock import MagicMock

import pytest

from apps.agents.covers.config import AGENT_COLORS
from apps.agents.covers.prompt_generator import (
    CoverBriefing,
    CoverPromptGenerator,
    _truncate_to_max_words,
)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.is_available = True
    return client


@pytest.fixture
def briefing():
    return CoverBriefing(
        headline="Nubank testa agentes de AI para atendimento",
        lede="O maior banco digital da LATAM iniciou testes com agentes autonomos",
        agent="radar",
        edition=30,
        dq_score=4.0,
    )


def test_returns_prompt_on_success(mock_client, briefing):
    mock_client.generate.return_value = "Dark editorial illustration of a futuristic bank."
    gen = CoverPromptGenerator(client=mock_client)
    result = gen.generate_prompt(briefing)
    assert result == "Dark editorial illustration of a futuristic bank."
    mock_client.generate.assert_called_once()


def test_returns_none_when_client_unavailable(briefing):
    client = MagicMock()
    client.is_available = False
    gen = CoverPromptGenerator(client=client)
    assert gen.generate_prompt(briefing) is None


def test_returns_none_when_generate_fails(mock_client, briefing):
    mock_client.generate.return_value = None
    gen = CoverPromptGenerator(client=mock_client)
    assert gen.generate_prompt(briefing) is None


def test_returns_none_when_generate_returns_empty(mock_client, briefing):
    mock_client.generate.return_value = "   "
    gen = CoverPromptGenerator(client=mock_client)
    assert gen.generate_prompt(briefing) is None


def test_prompt_contains_headline(mock_client, briefing):
    mock_client.generate.return_value = "A prompt."
    gen = CoverPromptGenerator(client=mock_client)
    gen.generate_prompt(briefing)
    call_args = mock_client.generate.call_args
    assert briefing.headline in call_args.kwargs["user_prompt"]


def test_prompt_contains_agent_color(mock_client, briefing):
    mock_client.generate.return_value = "A prompt."
    gen = CoverPromptGenerator(client=mock_client)
    gen.generate_prompt(briefing)
    call_args = mock_client.generate.call_args
    assert AGENT_COLORS["radar"] in call_args.kwargs["user_prompt"]


def test_system_prompt_has_agent_color_resolved(mock_client, briefing):
    mock_client.generate.return_value = "A prompt."
    gen = CoverPromptGenerator(client=mock_client)
    gen.generate_prompt(briefing)
    call_args = mock_client.generate.call_args
    # The {agent_color} placeholder should be replaced
    assert "{agent_color}" not in call_args.kwargs["system_prompt"]
    assert AGENT_COLORS["radar"] in call_args.kwargs["system_prompt"]


def test_output_truncated_to_150_words(mock_client, briefing):
    long_text = " ".join(["word"] * 200)
    mock_client.generate.return_value = long_text
    gen = CoverPromptGenerator(client=mock_client)
    result = gen.generate_prompt(briefing)
    assert len(result.split()) <= 150


def test_empty_headline_returns_none(mock_client):
    briefing = CoverBriefing(headline="", lede="Some lede", agent="radar", edition=1)
    gen = CoverPromptGenerator(client=mock_client)
    assert gen.generate_prompt(briefing) is None


def test_unknown_agent_uses_default_color(mock_client):
    briefing = CoverBriefing(
        headline="Test", lede="Test lede", agent="unknown_agent", edition=1
    )
    mock_client.generate.return_value = "A prompt."
    gen = CoverPromptGenerator(client=mock_client)
    gen.generate_prompt(briefing)
    call_args = mock_client.generate.call_args
    assert "#FFFFFF" in call_args.kwargs["user_prompt"]


def test_truncate_to_max_words_short_text():
    assert _truncate_to_max_words("hello world", 5) == "hello world"


def test_truncate_to_max_words_long_text():
    text = " ".join(["word"] * 10)
    result = _truncate_to_max_words(text, 5)
    assert result == "word word word word word"
