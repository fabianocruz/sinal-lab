"""Tests for scripts/run_cron.py — Railway cron service entry point.

Covers period auto-calculation, DB edition lookup, fallback behavior,
unknown agent handling, orchestrator integration, daily schedule dispatch,
and services.toml consistency with the AGENTS registry.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from scripts.run_agents import AGENTS
from scripts.run_cron import (
    SCHEDULE,
    _get_current_week,
    _get_next_edition,
    _get_period_value,
    main,
    run_daily,
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

    @patch("scripts.run_cron.run_daily", return_value=0)
    @patch("sys.argv", ["run_cron.py"])
    def test_no_args_calls_run_daily(self, mock_daily):
        """No args → daily dispatch mode (Railway cron)."""
        code = main()
        assert code == 0
        mock_daily.assert_called_once()

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
# TestSchedule — SCHEDULE dict validation
# ---------------------------------------------------------------------------


class TestSchedule:
    """Validate the SCHEDULE mapping is consistent with AGENTS registry."""

    def test_all_weekdays_are_valid(self):
        """SCHEDULE keys must be valid ISO weekdays (1-7)."""
        for day in SCHEDULE:
            assert 1 <= day <= 7, f"Invalid weekday {day} in SCHEDULE"

    def test_all_scheduled_agents_exist_in_registry(self):
        """Every agent referenced in SCHEDULE must exist in AGENTS."""
        for day, agents in SCHEDULE.items():
            for agent_name in agents:
                assert agent_name in AGENTS, (
                    f"SCHEDULE day {day} references unknown agent '{agent_name}'"
                )

    def test_all_agents_appear_in_schedule(self):
        """Every agent in AGENTS must appear in SCHEDULE at least once."""
        scheduled = {a for agents in SCHEDULE.values() for a in agents}
        for agent_name in AGENTS:
            assert agent_name in scheduled, (
                f"Agent '{agent_name}' not found in any SCHEDULE day"
            )

    def test_no_duplicate_agents_on_same_day(self):
        """No agent should appear twice on the same day."""
        for day, agents in SCHEDULE.items():
            assert len(agents) == len(set(agents)), (
                f"Duplicate agents on day {day}: {agents}"
            )


# ---------------------------------------------------------------------------
# TestRunDaily — daily dispatch logic
# ---------------------------------------------------------------------------


class TestRunDaily:
    """Tests for run_daily() schedule-based dispatch."""

    @patch("scripts.run_cron.orchestrate_single_agent", return_value=0)
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value")
    @patch("scripts.run_cron.datetime")
    def test_dispatches_monday_agents_in_order(
        self, mock_dt, mock_period, mock_get_session, mock_orchestrate
    ):
        """On Monday (isoweekday=1), should run all Monday agents in order."""
        mock_dt.now.return_value.isoweekday.return_value = 1
        mock_period.return_value = 8
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        code = run_daily()

        assert code == 0
        expected_agents = SCHEDULE[1]
        assert mock_orchestrate.call_count == len(expected_agents)
        for i, agent_name in enumerate(expected_agents):
            assert mock_orchestrate.call_args_list[i] == call(
                agent_name,
                period_value=8,
                session=mock_session,
                enable_editorial=True,
                enable_evidence=True,
            )

    @patch("scripts.run_cron.orchestrate_single_agent", return_value=0)
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value")
    @patch("scripts.run_cron.datetime")
    def test_dispatches_wednesday_agents(
        self, mock_dt, mock_period, mock_get_session, mock_orchestrate
    ):
        """On Wednesday (isoweekday=3), should run Wednesday agents."""
        mock_dt.now.return_value.isoweekday.return_value = 3
        mock_period.return_value = 8
        mock_get_session.return_value = MagicMock()

        code = run_daily()

        assert code == 0
        expected_agents = SCHEDULE[3]
        assert mock_orchestrate.call_count == len(expected_agents)

    @patch("scripts.run_cron.datetime")
    def test_no_agents_scheduled_exits_0(self, mock_dt):
        """On days with no agents scheduled, should log and exit 0."""
        # Sunday (isoweekday=7) is not in SCHEDULE
        mock_dt.now.return_value.isoweekday.return_value = 7

        code = run_daily()

        assert code == 0

    @patch("scripts.run_cron.orchestrate_single_agent")
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value", return_value=8)
    @patch("scripts.run_cron.datetime")
    def test_partial_failure_returns_1(
        self, mock_dt, mock_period, mock_get_session, mock_orchestrate
    ):
        """If one agent fails, run_daily should still run remaining agents and return 1."""
        mock_dt.now.return_value.isoweekday.return_value = 1
        mock_get_session.return_value = MagicMock()
        # First agent succeeds, second fails, rest succeed
        mock_orchestrate.side_effect = [0, 1] + [0] * (len(SCHEDULE[1]) - 2)

        code = run_daily()

        assert code == 1
        # All agents should still be called despite the failure
        assert mock_orchestrate.call_count == len(SCHEDULE[1])

    @patch("scripts.run_cron.orchestrate_single_agent", return_value=0)
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value", return_value=8)
    @patch("scripts.run_cron.datetime")
    def test_closes_session_after_run(
        self, mock_dt, mock_period, mock_get_session, mock_orchestrate
    ):
        """Session must be closed even after successful run."""
        mock_dt.now.return_value.isoweekday.return_value = 1
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        run_daily()

        mock_session.close.assert_called_once()

    @patch("scripts.run_cron.orchestrate_single_agent", side_effect=RuntimeError("Crash"))
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value", return_value=8)
    @patch("scripts.run_cron.datetime")
    def test_closes_session_on_exception(
        self, mock_dt, mock_period, mock_get_session, mock_orchestrate
    ):
        """Session must be closed even if an agent raises an unhandled exception."""
        mock_dt.now.return_value.isoweekday.return_value = 1
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError):
            run_daily()

        mock_session.close.assert_called_once()

    @patch("scripts.run_cron.orchestrate_single_agent", return_value=0)
    @patch("scripts.run_cron.get_session")
    @patch("scripts.run_cron._get_period_value")
    @patch("scripts.run_cron.datetime")
    def test_calculates_period_per_agent(
        self, mock_dt, mock_period, mock_get_session, mock_orchestrate
    ):
        """Each agent should get its own period value (edition vs week)."""
        mock_dt.now.return_value.isoweekday.return_value = 1
        mock_get_session.return_value = MagicMock()
        mock_period.side_effect = lambda name: 6 if name == "sintese" else 8

        run_daily()

        for c in mock_orchestrate.call_args_list:
            agent_name = c[0][0]
            if agent_name == "sintese":
                assert c[1]["period_value"] == 6
            else:
                assert c[1]["period_value"] == 8


# ---------------------------------------------------------------------------
# TestServicesToml — railway/services.toml consistency
# ---------------------------------------------------------------------------


class TestServicesToml:
    """Validate railway/services.toml has a single cron-agents service."""

    @pytest.fixture
    def toml_content(self) -> str:
        path = PROJECT_ROOT / "railway" / "services.toml"
        assert path.exists(), f"railway/services.toml not found at {path}"
        return path.read_text()

    def test_single_cron_agents_service(self, toml_content: str):
        """There should be exactly one cron-agents service (not per-agent)."""
        assert "[services.cron-agents]" in toml_content

    def test_cron_command_is_no_arg(self, toml_content: str):
        """The cron service should call run_cron.py without an agent arg."""
        assert 'python scripts/run_cron.py"' in toml_content or \
               "python scripts/run_cron.py'" in toml_content or \
               'start_command = "python scripts/run_cron.py"' in toml_content

    def test_api_service_declared(self, toml_content: str):
        assert "[services.api]" in toml_content

    def test_no_per_agent_cron_services(self, toml_content: str):
        """Individual per-agent cron sections should not exist."""
        for agent_name in AGENTS:
            section = f"[services.cron-{agent_name}]"
            assert section not in toml_content, (
                f"Found legacy per-agent section {section} in services.toml"
            )
