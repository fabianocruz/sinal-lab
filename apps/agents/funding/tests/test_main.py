"""Unit tests for FUNDING agent CLI entry point.

Tests that funding/main.py correctly delegates to the shared CLI module
with the right agent-specific configuration.
"""

from unittest.mock import Mock, patch

from apps.agents.funding.main import main


class TestMainDelegation:
    """Test that main() delegates to run_agent_cli correctly."""

    @patch("apps.agents.funding.main.run_agent_cli")
    def test_delegates_to_run_agent_cli(self, mock_run):
        main()
        mock_run.assert_called_once()

    @patch("apps.agents.funding.main.run_agent_cli")
    def test_passes_funding_agent_class(self, mock_run):
        from apps.agents.funding.agent import FundingAgent

        main()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["agent_class"] is FundingAgent

    @patch("apps.agents.funding.main.run_agent_cli")
    def test_passes_correct_description(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        assert "FUNDING" in call_kwargs["description"]

    @patch("apps.agents.funding.main.run_agent_cli")
    def test_passes_output_dir(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        assert "funding" in call_kwargs["default_output_dir"]

    @patch("apps.agents.funding.main.run_agent_cli")
    def test_slug_fn_generates_correct_slug(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        slug_fn = call_kwargs["slug_fn"]

        mock_agent = Mock()
        mock_args = Mock()
        mock_args.week = 7

        assert slug_fn(mock_agent, mock_args) == "funding-semanal-7"

    @patch("apps.agents.funding.main.run_agent_cli")
    def test_has_post_run_fn(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["post_run_fn"] is not None

    @patch("apps.agents.funding.main.run_agent_cli")
    def test_filename_fn_generates_correct_name(self, mock_run):
        main()

        call_kwargs = mock_run.call_args[1]
        filename_fn = call_kwargs["filename_fn"]

        mock_agent = Mock()
        mock_args = Mock()
        mock_args.week = 7

        assert filename_fn(mock_agent, mock_args) == "funding-week-7.md"
