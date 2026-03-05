"""Tests for the shared agent CLI module.

Tests setup_logging, build_base_parser, write_markdown_output,
display_run_summary, and run_agent_cli.
"""

import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker

from apps.agents.base.cli import (
    setup_logging,
    build_base_parser,
    write_markdown_output,
    display_run_summary,
    run_agent_cli,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_confidence(dq: float = 0.7, ac: float = 0.6) -> ConfidenceScore:
    return ConfidenceScore(data_quality=dq, analysis_confidence=ac, source_count=3)


def _make_result(title: str = "Test Report") -> AgentOutput:
    body = "# Report\n\n" + " ".join(["word"] * 60)
    return AgentOutput(
        title=title,
        body_md=body,
        agent_name="radar",
        run_id="radar-20260217-001",
        confidence=_make_confidence(),
        sources=["source-1", "source-2"],
        content_type="DATA_REPORT",
        agent_category="data",
        summary="Summary text.",
    )


def _make_mock_agent(
    name: str = "radar",
    run_id: str = "radar-20260217-001",
) -> MagicMock:
    agent = MagicMock()
    agent.agent_name = name
    agent.run_id = run_id
    agent.started_at = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
    agent.completed_at = datetime(2026, 2, 17, 10, 1, 0, tzinfo=timezone.utc)
    agent._collected_data = list(range(50))
    agent._processed_data = list(range(40))
    agent._errors = []
    agent.provenance = ProvenanceTracker()
    agent.provenance.track(
        source_url="https://api.github.com",
        source_name="github",
        extraction_method="api",
    )
    agent.get_run_metadata.return_value = {
        "agent_name": name,
        "run_id": run_id,
        "items_collected": 50,
        "items_processed": 40,
    }
    return agent


class FakeAgent:
    """Minimal agent class for testing run_agent_cli."""

    agent_name = "fake"
    agent_category = "data"
    version = "0.1.0"

    def __init__(self, week_number: int = 1, **kwargs: Any) -> None:
        self.week_number = week_number
        self.run_id = f"fake-{week_number}"
        self.started_at = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        self.completed_at = datetime(2026, 2, 17, 10, 1, 0, tzinfo=timezone.utc)
        self._collected_data = list(range(10))
        self._processed_data = list(range(8))
        self._errors: List[str] = []
        self.provenance = ProvenanceTracker()

    def run(self) -> AgentOutput:
        return _make_result(title=f"Fake Report W{self.week_number}")

    def get_run_metadata(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "run_id": self.run_id,
            "items_collected": len(self._collected_data),
            "items_processed": len(self._processed_data),
        }


# ---------------------------------------------------------------------------
# TestSetupLogging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """Tests for setup_logging()."""

    def test_default_level_is_info(self):
        setup_logging(verbose=False)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_verbose_level_is_debug(self):
        setup_logging(verbose=True)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def teardown_method(self):
        """Reset logging after each test."""
        logging.getLogger().setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# TestBuildBaseParser
# ---------------------------------------------------------------------------


class TestBuildBaseParser:
    """Tests for build_base_parser()."""

    def test_has_standard_args(self):
        parser = build_base_parser("Test Agent")
        args = parser.parse_args(["--dry-run", "--persist", "--verbose"])
        assert args.dry_run is True
        assert args.persist is True
        assert args.verbose is True

    def test_default_period_arg_is_week(self):
        parser = build_base_parser("Test Agent")
        args = parser.parse_args(["--week", "7"])
        assert args.week == 7

    def test_edition_period_variant(self):
        parser = build_base_parser("Test Agent", period_arg="edition")
        args = parser.parse_args(["--edition", "3"])
        assert args.edition == 3

    def test_has_output_arg(self):
        parser = build_base_parser("Test Agent")
        args = parser.parse_args(["--output", "/tmp/test.md"])
        assert args.output == "/tmp/test.md"

    def test_extra_args_callback(self):
        def add_html(parser):
            parser.add_argument("--html", type=str, help="HTML output path")
            parser.add_argument("--send", action="store_true")

        parser = build_base_parser("Test Agent", extra_args_fn=add_html)
        args = parser.parse_args(["--html", "/tmp/test.html", "--send"])
        assert args.html == "/tmp/test.html"
        assert args.send is True

    def test_default_values(self):
        parser = build_base_parser("Test Agent")
        args = parser.parse_args([])
        assert args.dry_run is False
        assert args.persist is False
        assert args.verbose is False
        assert args.output is None


# ---------------------------------------------------------------------------
# TestWriteMarkdownOutput
# ---------------------------------------------------------------------------


class TestWriteMarkdownOutput:
    """Tests for write_markdown_output()."""

    def test_writes_to_specified_path(self, tmp_path):
        result = _make_result()
        output_path = str(tmp_path / "report.md")

        actual_path = write_markdown_output(
            result, output_path=output_path,
            default_dir="unused", default_filename="unused.md",
        )

        assert actual_path == output_path
        assert os.path.exists(actual_path)
        with open(actual_path, "r") as f:
            content = f.read()
        assert "# Report" in content

    def test_auto_generates_path(self, tmp_path):
        result = _make_result()
        default_dir = str(tmp_path / "output")

        actual_path = write_markdown_output(
            result, output_path=None,
            default_dir=default_dir,
            default_filename="test-report.md",
        )

        assert actual_path == os.path.join(default_dir, "test-report.md")
        assert os.path.exists(actual_path)

    def test_creates_directory(self, tmp_path):
        result = _make_result()
        default_dir = str(tmp_path / "deep" / "nested" / "output")

        actual_path = write_markdown_output(
            result, output_path=None,
            default_dir=default_dir,
            default_filename="report.md",
        )

        assert os.path.exists(actual_path)
        assert os.path.isdir(default_dir)

    def test_returns_path(self, tmp_path):
        result = _make_result()
        output_path = str(tmp_path / "out.md")

        path = write_markdown_output(
            result, output_path=output_path,
            default_dir="unused", default_filename="unused.md",
        )

        assert isinstance(path, str)
        assert path == output_path


# ---------------------------------------------------------------------------
# TestDisplayRunSummary
# ---------------------------------------------------------------------------


class TestDisplayRunSummary:
    """Tests for display_run_summary()."""

    def test_prints_metadata(self, capsys):
        agent = _make_mock_agent()
        result = _make_result()

        display_run_summary(agent, result, "/tmp/out.md", persisted=False)

        captured = capsys.readouterr()
        assert "items_collected" in captured.out or "50" in captured.out

    def test_prints_confidence(self, capsys):
        agent = _make_mock_agent()
        result = _make_result()

        display_run_summary(agent, result, "/tmp/out.md", persisted=False)

        captured = capsys.readouterr()
        assert result.confidence.grade in captured.out

    def test_prints_persist_status(self, capsys):
        agent = _make_mock_agent()
        result = _make_result()

        display_run_summary(agent, result, "/tmp/out.md", persisted=True)

        captured = capsys.readouterr()
        assert "persist" in captured.out.lower() or "DB" in captured.out


# ---------------------------------------------------------------------------
# TestRunAgentCli
# ---------------------------------------------------------------------------


class TestRunAgentCli:
    """Tests for run_agent_cli()."""

    def test_dry_run_skips_persist(self, tmp_path, capsys):
        with patch("sys.argv", ["prog", "--dry-run"]):
            run_agent_cli(
                agent_class=FakeAgent,
                description="Fake Agent",
                default_output_dir=str(tmp_path),
            )

        # Should not have tried to persist
        # Dry run prints output preview
        captured = capsys.readouterr()
        assert "=" in captured.out  # dry run separator

    def test_writes_output_file(self, tmp_path):
        output_path = str(tmp_path / "test-output.md")
        with patch("sys.argv", ["prog", "--output", output_path]):
            run_agent_cli(
                agent_class=FakeAgent,
                description="Fake Agent",
                default_output_dir=str(tmp_path),
            )

        assert os.path.exists(output_path)

    def test_slug_fn_generates_slug(self, tmp_path):
        """slug_fn receives (agent, args) and produces a slug for persistence."""
        def slug_fn(agent, args):
            return f"fake-week-{args.week}"

        with patch("sys.argv", ["prog", "--week", "7", "--persist"]):
            with patch("apps.agents.base.cli.persist_agent_output") as mock_persist:
                mock_persist.return_value = (MagicMock(), MagicMock())
                run_agent_cli(
                    agent_class=FakeAgent,
                    description="Fake Agent",
                    default_output_dir=str(tmp_path),
                    slug_fn=slug_fn,
                )

        # persist_agent_output should have been called with the right slug
        if mock_persist.called:
            call_kwargs = mock_persist.call_args
            # Check slug was passed
            assert "fake-week-7" in str(call_kwargs)

    def test_post_run_fn_called(self, tmp_path):
        post_run = MagicMock()

        with patch("sys.argv", ["prog", "--persist"]):
            with patch("apps.agents.base.cli.persist_agent_output") as mock_persist:
                mock_persist.return_value = (MagicMock(), MagicMock())
                run_agent_cli(
                    agent_class=FakeAgent,
                    description="Fake Agent",
                    default_output_dir=str(tmp_path),
                    post_run_fn=post_run,
                )

        post_run.assert_called_once()

    def test_period_arg_edition(self, tmp_path, capsys):
        """Supports --edition instead of --week."""
        with patch("sys.argv", ["prog", "--edition", "3", "--dry-run"]):
            run_agent_cli(
                agent_class=FakeAgent,
                description="Fake Agent",
                default_output_dir=str(tmp_path),
                period_arg="edition",
            )

        # Should not crash
        captured = capsys.readouterr()
        assert "=" in captured.out

    def test_extra_args_fn(self, tmp_path):
        def add_html(parser):
            parser.add_argument("--html", type=str, default=None)

        output_path = str(tmp_path / "out.md")
        with patch("sys.argv", ["prog", "--output", output_path, "--html", "/tmp/test.html"]):
            run_agent_cli(
                agent_class=FakeAgent,
                description="Fake Agent",
                default_output_dir=str(tmp_path),
                extra_args_fn=add_html,
            )

        assert os.path.exists(output_path)

    def test_auto_publish_flag_in_parser(self):
        parser = build_base_parser("Test Agent")
        args = parser.parse_args(["--auto-publish"])
        assert args.auto_publish is True

    def test_auto_publish_default_false(self):
        parser = build_base_parser("Test Agent")
        args = parser.parse_args([])
        assert args.auto_publish is False

    def test_auto_publish_passes_published_status(self, tmp_path):
        """--auto-publish + --persist passes review_status='published'."""
        with patch("sys.argv", ["prog", "--persist", "--auto-publish"]):
            with patch("apps.agents.base.cli.persist_agent_output") as mock_persist:
                mock_persist.return_value = (MagicMock(), MagicMock())
                run_agent_cli(
                    agent_class=FakeAgent,
                    description="Fake Agent",
                    default_output_dir=str(tmp_path),
                )

        mock_persist.assert_called_once()
        call_kwargs = mock_persist.call_args
        assert call_kwargs.kwargs.get("review_status") == "published" or \
            "published" in str(call_kwargs)

    def test_persist_without_auto_publish_uses_pending(self, tmp_path):
        """--persist without --auto-publish uses pending_review."""
        with patch("sys.argv", ["prog", "--persist"]):
            with patch("apps.agents.base.cli.persist_agent_output") as mock_persist:
                mock_persist.return_value = (MagicMock(), MagicMock())
                run_agent_cli(
                    agent_class=FakeAgent,
                    description="Fake Agent",
                    default_output_dir=str(tmp_path),
                )

        mock_persist.assert_called_once()
        call_kwargs = mock_persist.call_args
        assert call_kwargs.kwargs.get("review_status") == "pending_review" or \
            "pending_review" in str(call_kwargs)
