"""Tests for shared LLM client (base/llm.py)."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from unittest.mock import patch, MagicMock

from apps.agents.base.llm import LLMClient, LLMConfig


class TestLLMConfig:
    """Test LLMConfig dataclass."""

    def test_default_values(self):
        config = LLMConfig()
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.max_tokens == 1024
        assert config.temperature == 0.7
        assert config.api_key_env == "ANTHROPIC_API_KEY"

    def test_custom_values(self):
        config = LLMConfig(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            temperature=0.3,
            api_key_env="CUSTOM_KEY",
        )
        assert config.model == "claude-haiku-4-5-20251001"
        assert config.max_tokens == 512
        assert config.temperature == 0.3
        assert config.api_key_env == "CUSTOM_KEY"


class TestLLMClientAvailability:
    """Test LLMClient.is_available property."""

    def test_is_available_true_when_api_key_set(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            client = LLMClient()
            assert client.is_available is True

    def test_is_available_false_when_api_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient()
            assert client.is_available is False

    def test_is_available_false_when_api_key_empty(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            client = LLMClient()
            assert client.is_available is False


class TestLLMClientGenerate:
    """Test LLMClient.generate() method."""

    def test_generate_returns_text_on_success(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated text")]

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            client = LLMClient()
            result = client.generate("test prompt")

        assert result == "Generated text"

    def test_generate_returns_none_when_not_available(self):
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient()
            result = client.generate("test prompt")
            assert result is None

    def test_generate_returns_none_on_api_error(self):
        import anthropic

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.side_effect = anthropic.APIError(
            message="Server error",
            request=MagicMock(),
            body=None,
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            mock_module.APIError = anthropic.APIError
            client = LLMClient()
            result = client.generate("test prompt")

        assert result is None

    def test_generate_returns_none_on_auth_error(self):
        import anthropic

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.side_effect = anthropic.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            mock_module.APIError = anthropic.APIError
            client = LLMClient()
            result = client.generate("test prompt")

        assert result is None

    def test_generate_returns_none_on_rate_limit(self):
        import anthropic

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.side_effect = anthropic.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            mock_module.APIError = anthropic.APIError
            client = LLMClient()
            result = client.generate("test prompt")

        assert result is None

    def test_generate_returns_none_on_connection_error(self):
        import anthropic

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.side_effect = anthropic.APIConnectionError(
            request=MagicMock(),
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            mock_module.APIError = anthropic.APIError
            client = LLMClient()
            result = client.generate("test prompt")

        assert result is None

    def test_generate_passes_system_prompt(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            client = LLMClient()
            client.generate("user msg", system_prompt="system msg")

        call_kwargs = mock_anthropic_cls.return_value.messages.create.call_args[1]
        assert call_kwargs["system"] == "system msg"

    def test_generate_uses_config_defaults(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response

        config = LLMConfig(model="test-model", max_tokens=256, temperature=0.5)

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            client = LLMClient(config=config)
            client.generate("prompt")

        call_kwargs = mock_anthropic_cls.return_value.messages.create.call_args[1]
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["max_tokens"] == 256
        assert call_kwargs["temperature"] == 0.5

    def test_generate_overrides_per_call(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            client = LLMClient()
            client.generate("prompt", max_tokens=500, temperature=0.3)

        call_kwargs = mock_anthropic_cls.return_value.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["temperature"] == 0.3

    def test_generate_returns_none_on_empty_response(self):
        mock_response = MagicMock()
        mock_response.content = []

        mock_anthropic_cls = MagicMock()
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("apps.agents.base.llm.anthropic") as mock_module:
            mock_module.Anthropic = mock_anthropic_cls
            client = LLMClient()
            result = client.generate("prompt")

        assert result is None
