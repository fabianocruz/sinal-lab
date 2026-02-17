"""Tests for output formatting module."""

import pytest
from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput, format_markdown_output


class TestAgentOutput:
    """Test AgentOutput dataclass."""

    def _make_output(self, **kwargs) -> AgentOutput:
        defaults = {
            "title": "Test Report",
            "body_md": "This is a test report with enough words to pass validation. " * 5,
            "agent_name": "test",
            "run_id": "test-001",
            "confidence": ConfidenceScore(data_quality=0.8, analysis_confidence=0.7),
            "sources": ["https://example.com"],
        }
        defaults.update(kwargs)
        return AgentOutput(**defaults)

    def test_create_output(self):
        output = self._make_output()
        assert output.title == "Test Report"
        assert output.agent_name == "test"

    def test_to_markdown_has_frontmatter(self):
        output = self._make_output()
        md = output.to_markdown()
        assert md.startswith("---")
        assert "title: \"Test Report\"" in md
        assert "agent: test" in md
        assert "confidence_dq: 0.8" in md
        assert "confidence_ac: 0.7" in md
        assert "confidence_grade: B" in md

    def test_to_markdown_has_body(self):
        output = self._make_output(body_md="# Hello\n\nWorld")
        md = output.to_markdown()
        assert "# Hello" in md
        assert "World" in md

    def test_to_markdown_has_sources(self):
        output = self._make_output(
            sources=["https://hn.com", "https://github.com"]
        )
        md = output.to_markdown()
        assert "sources:" in md
        assert "https://hn.com" in md
        assert "https://github.com" in md

    def test_to_dict(self):
        output = self._make_output()
        d = output.to_dict()
        assert d["title"] == "Test Report"
        assert d["agent_name"] == "test"
        assert "confidence" in d
        assert d["confidence"]["data_quality"] == 0.8

    def test_validate_valid_output(self):
        output = self._make_output()
        errors = output.validate()
        assert errors == []

    def test_validate_empty_title(self):
        output = self._make_output(title="")
        errors = output.validate()
        assert any("Title" in e for e in errors)

    def test_validate_empty_body(self):
        output = self._make_output(body_md="")
        errors = output.validate()
        assert any("Body" in e for e in errors)

    def test_validate_short_body(self):
        output = self._make_output(body_md="Too short")
        errors = output.validate()
        assert any("too short" in e.lower() for e in errors)

    def test_validate_no_sources(self):
        output = self._make_output(sources=[])
        errors = output.validate()
        assert any("source" in e.lower() for e in errors)

    def test_validate_low_confidence(self):
        output = self._make_output(
            confidence=ConfidenceScore(data_quality=0.05, analysis_confidence=0.05)
        )
        errors = output.validate()
        assert any("confidence" in e.lower() for e in errors)

    def test_agent_category_default(self):
        output = self._make_output()
        assert output.agent_category == "content"

    def test_agent_category_explicit(self):
        output = self._make_output(agent_category="data")
        assert output.agent_category == "data"

    def test_to_markdown_has_agent_category(self):
        output = self._make_output(agent_category="data")
        md = output.to_markdown()
        assert "agent_category: data" in md

    def test_to_dict_has_agent_category(self):
        output = self._make_output(agent_category="data")
        d = output.to_dict()
        assert d["agent_category"] == "data"


class TestFormatMarkdownOutput:
    """Test the format_markdown_output helper."""

    def test_basic_formatting(self):
        output = format_markdown_output(
            title="Weekly Report",
            sections=[
                {"heading": "Trends", "content": "AI is growing fast."},
                {"heading": "Funding", "content": "Lots of deals this week."},
            ],
            agent_name="radar",
            run_id="radar-001",
            confidence=ConfidenceScore(data_quality=0.7, analysis_confidence=0.6),
            sources=["https://hn.com"],
        )
        assert output.title == "Weekly Report"
        assert "# Weekly Report" in output.body_md
        assert "## Trends" in output.body_md
        assert "AI is growing fast." in output.body_md
        assert "## Funding" in output.body_md

    def test_with_summary(self):
        output = format_markdown_output(
            title="Test",
            sections=[{"heading": "A", "content": "B"}],
            agent_name="test",
            run_id="test-001",
            confidence=ConfidenceScore(data_quality=0.5, analysis_confidence=0.5),
            sources=["src"],
            summary="This is the summary.",
        )
        assert "*This is the summary.*" in output.body_md

    def test_empty_sections(self):
        output = format_markdown_output(
            title="Empty",
            sections=[],
            agent_name="test",
            run_id="test-001",
            confidence=ConfidenceScore(data_quality=0.5, analysis_confidence=0.5),
            sources=["src"],
        )
        assert "# Empty" in output.body_md

    def test_format_with_agent_category(self):
        output = format_markdown_output(
            title="Test",
            sections=[{"heading": "A", "content": "B"}],
            agent_name="funding",
            run_id="funding-001",
            confidence=ConfidenceScore(data_quality=0.5, analysis_confidence=0.5),
            sources=["src"],
            agent_category="data",
        )
        assert output.agent_category == "data"

    def test_format_default_agent_category(self):
        output = format_markdown_output(
            title="Test",
            sections=[],
            agent_name="test",
            run_id="test-001",
            confidence=ConfidenceScore(data_quality=0.5, analysis_confidence=0.5),
            sources=["src"],
        )
        assert output.agent_category == "content"
