"""Tests for shared LLM client (base/llm.py)."""

import os

import pytest
from unittest.mock import patch, MagicMock

from apps.agents.base.llm import LLMClient, LLMConfig, strip_code_fences, strip_html


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


class TestStripCodeFences:
    """Test strip_code_fences utility."""

    def test_strips_json_code_fence(self):
        text = '```json\n{"key": "value"}\n```'
        assert strip_code_fences(text) == '{"key": "value"}'

    def test_strips_plain_code_fence(self):
        text = '```\nsome content\n```'
        assert strip_code_fences(text) == "some content"

    def test_leaves_non_fenced_text_alone(self):
        text = '{"key": "value"}'
        assert strip_code_fences(text) == '{"key": "value"}'

    def test_handles_whitespace_around_fences(self):
        text = '  ```json\n{"key": "value"}\n```  '
        assert strip_code_fences(text) == '{"key": "value"}'

    def test_handles_empty_string(self):
        assert strip_code_fences("") == ""


class TestStripHtml:
    """Test strip_html utility."""

    def test_strips_html_tags(self):
        text = "<p>Hello <b>world</b></p>"
        assert strip_html(text) == "Hello world"

    def test_strips_anchor_tags(self):
        text = '<a href="https://example.com">Link text</a>'
        assert strip_html(text) == "Link text"

    def test_strips_img_tags(self):
        text = '<img src="photo.jpg" style="display: block;"> After image'
        assert strip_html(text) == "After image"

    def test_truncates_to_max_length(self):
        text = "A" * 500
        result = strip_html(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_no_truncation_when_under_limit(self):
        text = "Short text"
        assert strip_html(text, max_length=300) == "Short text"

    def test_no_truncation_when_max_length_zero(self):
        text = "A" * 500
        assert strip_html(text, max_length=0) == "A" * 500

    def test_collapses_whitespace(self):
        text = "<p>Hello</p>\n\n  <p>World</p>"
        assert strip_html(text) == "Hello World"

    def test_handles_empty_string(self):
        assert strip_html("") == ""

    def test_handles_nested_tags(self):
        text = "<div><p>Text <span>here</span></p></div>"
        assert strip_html(text) == "Text here"

    def test_real_funding_html(self):
        """Test with actual HTML that was leaking in FUNDING output."""
        text = (
            '<p><a href="https://startupi.com.br" rel="nofollow">Startupi</a><br />'
            '<img src="https://startupi.com.br/wp-content/uploads/2026/02/photo.jpeg" '
            'style="display: block; margin: 1em auto;"> Brazilian fintech raised $17M</p>'
        )
        result = strip_html(text)
        assert "<" not in result
        assert ">" not in result
        assert "Brazilian fintech raised $17M" in result

    def test_decodes_numeric_html_entities(self):
        """Test that numeric HTML entities like &#8230; are decoded."""
        text = "Some text&#8230; more text"
        result = strip_html(text)
        assert "&#" not in result
        assert "\u2026" in result  # ellipsis character

    def test_decodes_named_html_entities(self):
        """Test that named HTML entities like &amp; are decoded."""
        text = "A &amp; B &lt; C"
        result = strip_html(text)
        assert result == "A & B < C"

    def test_decodes_entities_and_strips_tags(self):
        """Test combined HTML tag stripping and entity decoding."""
        text = "<p>Grupo Colorado&#8230; The post BemAgro raises $5.8M</p>"
        result = strip_html(text)
        assert "&#" not in result
        assert "<" not in result
        assert "Grupo Colorado" in result
