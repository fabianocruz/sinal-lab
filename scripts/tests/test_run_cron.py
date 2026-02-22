"""Tests for scripts/run_cron.py — Railway cron service entry point.

Covers period auto-calculation, DB edition lookup, fallback behavior,
unknown agent handling, orchestrator integration, and services.toml
consistency with the AGENTS registry.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.run_agents import AGENTS
from scripts.run_cron import (
    _get_current_week,
    _get_next_edition,
    _get_period_value,
    main,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# TestGetCurrentWeek
# ---------------------------------------------------------------------------


class TestGetCurrentWeek:
    """Tests for _get_current_week()."""

    def test_returns_iso_week(self):
        week = _get_current_week()
        expected = datetime.now().isocalendar()[1]
        assert week == expected

    def test_returns_int(self):
        assert isinstance(_get_current_week(), int)


# ---------------------------------------------------------------------------
# TestGetNextEdition
# ---------------------------------------------------------------------------


class TestGetNextEdition:
    """Tests for _get_next_edition() DB lookup + fallback."""

    @patch("scripts.run_cron.get_session")
    def test_returns_last_edition_plus_one(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Simulate query returning slug "sinal-semanal-5"
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.first.return_value = (
            ("sinal-semanal-5",)
        )

        result = _get_next_edition()

        assert result == 6
        mock_session.close.assert_called_once()

    @patch("scripts.run_cron.get_session")
    def test_handles_multi_digit_edition(self, mock_get_session):
        """Slug 'sinal-semanal-10' must parse 10, not just the last char."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.first.return_value = (
            ("sinal-semanal-10",)
        )

        result = _get_next_edition()

        assert result == 11
        mock_session.close.assert_called_once()

    @patch("scripts.run_cron.get_session")
    def test_fallback_when_no_editions_in_db(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # No rows
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.first.return_value = None

        result = _get_next_edition()

        expected_week = datetime.now().isocalendar()[1]
        assert result == expected_week
        mock_session.close.assert_called_once()

    @patch("scripts.run_cron.get_session")
    def test_fallback_on_db_error(self, mock_get_session):
        mock_get_session.side_effect = Exception("Connection refused")

        result = _get_next_edition()

        expected_week = datetime.now().isocalendar()[1]
        assert result == expected_week

    @patch("scripts.run_cron.get_session")
    def test_fallback_on_non_numeric_slug(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Slug doesn't end in a number
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.first.return_value = (
            ("sinal-semanal-draft",)
        )

        result = _get_next_edition()

        expected_week = datetime.now().isocalendar()[1]
        assert result == expected_week
        mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# TestGetPeriodValue
# ---------------------------------------------------------------------------


class TestGetPeriodValue:
    """Tests for _get_period_value() dispatch."""

    @patch("scripts.run_cron._get_next_edition", return_value=7)
    def test_sintese_uses_edition(self, mock_edition):
        result = _get_period_value("sintese")
        assert result == 7
        mock_edition.assert_called_once()

    @patch("scripts.run_cron._get_current_week", return_value=12)
    def test_radar_uses_week(self, mock_week):
        result = _get_period_value("radar")
        assert result == 12
        mock_week.assert_called_once()

    @patch("scripts.run_cron._get_current_week", return_value=12)
    def test_funding_uses_week(self, mock_week):
        result = _get_period_value("funding")
        assert result == 12

    @patch("scripts.run_cron._get_current_week", return_value=12)
    def test_mercado_uses_week(self, mock_week):
        result = _get_period_value("mercado")
        assert result == 12

    @patch("scripts.run_cron._get_current_week", return_value=12)
    def test_codigo_uses_week(self, mock_week):
        result = _get_period_value("codigo")
        assert result == 12


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for main() entry point."""

    @patch("sys.argv", ["run_cron.py"])
    def test_no_args_exits_1(self):
        code = main()
        assert code == 1

    @patch("sys.argv", ["run_cron.py", "nonexistent"])
    def test_unknown_agent_exits_1(self):
        code = main()
        assert code == 1

    @patch("scripts.run_cron.orchestrate_single_agent", return_value=0)
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value", return_value=8)
    @patch("sys.argv", ["run_cron.py", "radar"])
    def test_calls_orchestrate_single_agent(
        self, mock_period, mock_get_session, mock_orchestrate
    ):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        code = main()

        assert code == 0
        mock_orchestrate.assert_called_once_with(
            "radar",
            period_value=8,
            session=mock_session,
            enable_editorial=True,
            enable_evidence=True,
        )
        mock_session.close.assert_called_once()

    @patch("scripts.run_cron.orchestrate_single_agent", return_value=1)
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value", return_value=8)
    @patch("sys.argv", ["run_cron.py", "radar"])
    def test_propagates_failure_exit_code(
        self, mock_period, mock_get_session, mock_orchestrate
    ):
        mock_get_session.return_value = MagicMock()

        code = main()

        assert code == 1

    @patch("scripts.run_cron.orchestrate_single_agent", side_effect=RuntimeError("Crash"))
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value", return_value=8)
    @patch("sys.argv", ["run_cron.py", "radar"])
    def test_closes_session_on_exception(
        self, mock_period, mock_get_session, mock_orchestrate
    ):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError):
            main()

        mock_session.close.assert_called_once()

    @patch("scripts.run_cron.orchestrate_single_agent", return_value=0)
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_next_edition", return_value=6)
    @patch("sys.argv", ["run_cron.py", "sintese"])
    def test_sintese_uses_edition_from_db(
        self, mock_edition, mock_get_session, mock_orchestrate
    ):
        mock_get_session.return_value = MagicMock()

        code = main()

        assert code == 0
        mock_orchestrate.assert_called_once()
        assert mock_orchestrate.call_args[1]["period_value"] == 6


# ---------------------------------------------------------------------------
# TestServicesToml — railway/services.toml consistency
# ---------------------------------------------------------------------------


class TestServicesToml:
    """Validate railway/services.toml documents all agents with correct commands."""

    @pytest.fixture
    def toml_content(self) -> str:
        path = PROJECT_ROOT / "railway" / "services.toml"
        assert path.exists(), f"railway/services.toml not found at {path}"
        return path.read_text()

    def test_every_agent_has_cron_service(self, toml_content: str):
        for agent_name in AGENTS:
            expected_cmd = f"python scripts/run_cron.py {agent_name}"
            assert expected_cmd in toml_content, (
                f"Missing cron service for agent '{agent_name}' in services.toml"
            )

    def test_api_service_declared(self, toml_content: str):
        assert "[services.api]" in toml_content

    def test_all_cron_services_have_schedule(self, toml_content: str):
        for agent_name in AGENTS:
            section = f"[services.cron-{agent_name}]"
            assert section in toml_content, (
                f"Missing section {section} in services.toml"
            )

    def test_no_extra_agents_in_toml(self, toml_content: str):
        """services.toml should not reference agents that don't exist in AGENTS."""
        import re

        commands = re.findall(r'python scripts/run_cron\.py (\w+)', toml_content)
        for agent_name in commands:
            assert agent_name in AGENTS, (
                f"services.toml references unknown agent '{agent_name}'"
            )
