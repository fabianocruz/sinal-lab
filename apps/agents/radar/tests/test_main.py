"""Unit tests for RADAR agent CLI entry point.

Tests that radar/main.py correctly delegates to the shared CLI module
with the right agent-specific configuration.
"""

from io import StringIO
from unittest.mock import Mock, patch, mock_open

import pytest

from apps.agents.radar.main import main


class TestMainDelegation:
    """Test that main() delegates to run_agent_cli correctly."""

    @patch("apps.agents.radar.main.run_agent_cli")
    def test_delegates_to_run_agent_cli(self, mock_run):
        main()

        mock_run.assert_called_once()

    @patch("apps.agents.radar.main.run_agent_cli")
    def test_passes_radar_agent_class(self, mock_run):
        from apps.agents.radar.agent import RadarAgent

        main()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["agent_class"] is RadarAgent

    @patch("apps.agents.radar.main.run_agent_cli")
    def test_passes_correct_description(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        assert "RADAR" in call_kwargs["description"]

    @patch("apps.agents.radar.main.run_agent_cli")
    def test_passes_output_dir(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        assert "radar" in call_kwargs["default_output_dir"]

    @patch("apps.agents.radar.main.run_agent_cli")
    def test_slug_fn_generates_correct_slug(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        slug_fn = call_kwargs["slug_fn"]

        mock_agent = Mock()
        mock_args = Mock()
        mock_args.week = 7

        assert slug_fn(mock_agent, mock_args) == "radar-week-7"

    @patch("apps.agents.radar.main.run_agent_cli")
    def test_filename_fn_generates_correct_name(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        filename_fn = call_kwargs["filename_fn"]

        mock_agent = Mock()
        mock_args = Mock()
        mock_args.week = 8

        assert filename_fn(mock_agent, mock_args) == "radar-week-8.md"
