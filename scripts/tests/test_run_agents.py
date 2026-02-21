"""Tests for scripts/run_agents.py — unified agent runner.

Covers the orchestrate mode, subprocess mode helpers, domain persist
callbacks, agent class loading, and CLI argument parsing.
"""

from datetime import datetime, timezone
from typing import Any, List
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker
from packages.database.models.base import Base

from scripts.run_agents import (
    AGENTS,
    DOMAIN_PERSIST_FNS,
    _load_agent_class,
    _funding_domain_persist,
    _mercado_domain_persist,
    main,
    orchestrate_single_agent,
    run_agent,
    setup_logging,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    factory = sessionmaker(bind=engine)
    sess = factory()
    yield sess
    sess.rollback()
    sess.close()


def _make_confidence(dq: float = 0.7, ac: float = 0.6) -> ConfidenceScore:
    return ConfidenceScore(data_quality=dq, analysis_confidence=ac, source_count=3)


class FakeAgent:
    """Minimal agent stub for orchestrate mode tests."""

    agent_name = "test-agent"
    agent_category = "content"
    version = "0.1.0"

    def __init__(self, **kwargs) -> None:
        self.run_id = "test-agent-20260217-001"
        self.started_at = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        self.completed_at = datetime(2026, 2, 17, 10, 1, 0, tzinfo=timezone.utc)
        self._collected_data: List[Any] = list(range(10))
        self._processed_data: List[Any] = list(range(8))
        self._scores: List[Any] = []
        self._errors: List[str] = []
        self.provenance = ProvenanceTracker()
        self.provenance.track(
            source_url="https://example.com",
            source_name="test-source",
            extraction_method="api",
        )

    def run(self) -> AgentOutput:
        body = "# Test Report\n\n" + " ".join(["word"] * 60)
        return AgentOutput(
            title="Test Report",
            body_md=body,
            agent_name=self.agent_name,
            run_id=self.run_id,
            confidence=_make_confidence(),
            sources=["test-source"],
            content_type="DATA_REPORT",
            agent_category=self.agent_category,
            summary="A test report.",
        )

    def get_run_metadata(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "run_id": self.run_id,
            "items_collected": len(self._collected_data),
            "items_processed": len(self._processed_data),
        }


def _make_orchestration_result(persisted: bool = True):
    """Build a mock OrchestrationResult."""
    result = MagicMock()
    result.agent_output.confidence.grade = "B"
    result.persisted = persisted
    result.editorial_result = None
    result.evidence_stats = None
    return result


# ---------------------------------------------------------------------------
# TestAgentsDict — structure validation
# ---------------------------------------------------------------------------


class TestAgentsDict:
    """Validate AGENTS dict has all required keys for orchestrate mode."""

    def test_all_agents_present(self):
        expected = {"sintese", "radar", "codigo", "funding", "mercado"}
        assert set(AGENTS.keys()) == expected

    def test_all_agents_have_orchestrate_keys(self):
        required_keys = {"module", "description", "class_module", "class_name",
                         "period_arg", "slug_pattern"}
        for name, cfg in AGENTS.items():
            missing = required_keys - set(cfg.keys())
            assert not missing, f"Agent '{name}' missing keys: {missing}"

    def test_slug_patterns_contain_period_placeholder(self):
        for name, cfg in AGENTS.items():
            assert "{period}" in cfg["slug_pattern"], (
                f"Agent '{name}' slug_pattern must contain {{period}}"
            )

    def test_period_arg_is_valid(self):
        valid = {"week", "edition"}
        for name, cfg in AGENTS.items():
            assert cfg["period_arg"] in valid, (
                f"Agent '{name}' has invalid period_arg: {cfg['period_arg']}"
            )


# ---------------------------------------------------------------------------
# TestLoadAgentClass
# ---------------------------------------------------------------------------


class TestLoadAgentClass:
    """Tests for _load_agent_class() lazy import."""

    def test_loads_radar_agent(self):
        cls = _load_agent_class("radar")
        assert cls.__name__ == "RadarAgent"

    def test_loads_sintese_agent(self):
        cls = _load_agent_class("sintese")
        assert cls.__name__ == "SinteseAgent"

    def test_loads_all_agents(self):
        for name in AGENTS:
            cls = _load_agent_class(name)
            assert cls.__name__ == AGENTS[name]["class_name"]


# ---------------------------------------------------------------------------
# TestSetupLogging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """Tests for setup_logging()."""

    def test_default_info_level(self):
        setup_logging(verbose=False)
        # No assertion needed — just verify no crash

    def test_verbose_debug_level(self):
        setup_logging(verbose=True)
        # No assertion needed — just verify no crash


# ---------------------------------------------------------------------------
# TestRunAgent (subprocess mode)
# ---------------------------------------------------------------------------


class TestRunAgent:
    """Tests for run_agent() subprocess launcher."""

    def test_unknown_agent_returns_1(self):
        code = run_agent("nonexistent", [])
        assert code == 1

    @patch("scripts.run_agents.subprocess.run")
    def test_success_returns_0(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        code = run_agent("radar", ["--week", "8"])
        assert code == 0

    @patch("scripts.run_agents.subprocess.run")
    def test_failure_returns_nonzero(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=1)
        code = run_agent("radar", [])
        assert code == 1

    @patch("scripts.run_agents.subprocess.run")
    def test_dry_run_appended(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        run_agent("radar", [], dry_run=True)
        cmd = mock_subprocess.call_args[0][0]
        assert "--dry-run" in cmd

    @patch("scripts.run_agents.subprocess.run")
    def test_uses_correct_module(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        run_agent("sintese", ["--edition", "3"])
        cmd = mock_subprocess.call_args[0][0]
        assert "apps.agents.sintese.main" in cmd


# ---------------------------------------------------------------------------
# TestDomainPersistFns
# ---------------------------------------------------------------------------


class TestDomainPersistFns:
    """Tests for domain-specific persistence callbacks."""

    def test_funding_in_registry(self):
        assert "funding" in DOMAIN_PERSIST_FNS
        assert DOMAIN_PERSIST_FNS["funding"] is _funding_domain_persist

    def test_mercado_in_registry(self):
        assert "mercado" in DOMAIN_PERSIST_FNS
        assert DOMAIN_PERSIST_FNS["mercado"] is _mercado_domain_persist

    def test_radar_not_in_registry(self):
        assert "radar" not in DOMAIN_PERSIST_FNS

    @patch("apps.agents.funding.db_writer.persist_all_events")
    def test_funding_persist_calls_persist_all_events(self, mock_persist):
        mock_persist.return_value = {"inserted": 3}
        agent = Mock()
        scored = Mock()
        scored.event = Mock()
        scored.confidence.composite = 0.8
        agent._scored_events = [scored]

        _funding_domain_persist(agent, Mock(), Mock())

        mock_persist.assert_called_once()

    @patch("apps.agents.funding.db_writer.persist_all_events")
    def test_funding_persist_skips_empty(self, mock_persist):
        agent = Mock()
        agent._scored_events = []

        _funding_domain_persist(agent, Mock(), Mock())

        mock_persist.assert_not_called()

    @patch("apps.agents.mercado.db_writer.persist_all_profiles")
    def test_mercado_persist_calls_persist_all_profiles(self, mock_persist):
        mock_persist.return_value = {"inserted": 2}
        agent = Mock()
        scored = Mock()
        scored.profile = Mock()
        scored.composite_score = 0.75
        agent._scores = [scored]

        _mercado_domain_persist(agent, Mock(), Mock())

        mock_persist.assert_called_once()

    @patch("apps.agents.mercado.db_writer.persist_all_profiles")
    def test_mercado_persist_skips_empty(self, mock_persist):
        agent = Mock()
        agent._scores = []

        _mercado_domain_persist(agent, Mock(), Mock())

        mock_persist.assert_not_called()


# ---------------------------------------------------------------------------
# TestOrchestrateSingleAgent
# ---------------------------------------------------------------------------


class TestOrchestrateSingleAgent:
    """Tests for orchestrate_single_agent()."""

    def test_unknown_agent_returns_1(self, session: Session):
        code = orchestrate_single_agent("nonexistent", 8, session)
        assert code == 1

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_success_returns_0(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        code = orchestrate_single_agent("radar", 8, session)

        assert code == 0

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_passes_correct_slug(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        orchestrate_single_agent("radar", 8, session)

        call_kwargs = mock_orchestrate.call_args[1]
        assert call_kwargs["slug"] == "radar-week-8"

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_passes_editorial_flag(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        orchestrate_single_agent("radar", 8, session, enable_editorial=False)

        call_kwargs = mock_orchestrate.call_args[1]
        assert call_kwargs["enable_editorial"] is False

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_passes_evidence_flag(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        orchestrate_single_agent("radar", 8, session, enable_evidence=False)

        call_kwargs = mock_orchestrate.call_args[1]
        assert call_kwargs["enable_evidence"] is False

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_passes_domain_persist_fn_for_funding(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        orchestrate_single_agent("funding", 8, session)

        call_kwargs = mock_orchestrate.call_args[1]
        assert call_kwargs["domain_persist_fn"] is _funding_domain_persist

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_no_domain_persist_fn_for_radar(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        orchestrate_single_agent("radar", 8, session)

        call_kwargs = mock_orchestrate.call_args[1]
        assert call_kwargs["domain_persist_fn"] is None

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_agent_failure_returns_1(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.side_effect = RuntimeError("Agent crashed")

        code = orchestrate_single_agent("radar", 8, session)

        assert code == 1

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_slug_pattern_for_sintese(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        orchestrate_single_agent("sintese", 3, session)

        call_kwargs = mock_orchestrate.call_args[1]
        assert call_kwargs["slug"] == "sinal-semanal-3"

    @patch("apps.agents.base.orchestrator.orchestrate_agent_run")
    @patch("scripts.run_agents._load_agent_class")
    def test_slug_pattern_for_funding(self, mock_load, mock_orchestrate, session: Session):
        mock_load.return_value = FakeAgent
        mock_orchestrate.return_value = _make_orchestration_result()

        orchestrate_single_agent("funding", 7, session)

        call_kwargs = mock_orchestrate.call_args[1]
        assert call_kwargs["slug"] == "funding-semanal-7"


# ---------------------------------------------------------------------------
# TestMainOrchestrateMode — CLI integration
# ---------------------------------------------------------------------------


class TestMainOrchestrateMode:
    """Tests for main() with --orchestrate flag."""

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8", "--orchestrate"])
    def test_orchestrate_calls_orchestrate_single_agent(self, mock_get_session, mock_orch):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_orch.return_value = 0

        main()

        mock_orch.assert_called_once()
        call_kwargs = mock_orch.call_args[1]
        assert call_kwargs["period_value"] == 8
        assert call_kwargs["enable_editorial"] is True
        assert call_kwargs["enable_evidence"] is True

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8", "--orchestrate", "--no-editorial"])
    def test_orchestrate_no_editorial(self, mock_get_session, mock_orch):
        mock_get_session.return_value = MagicMock()
        mock_orch.return_value = 0

        main()

        call_kwargs = mock_orch.call_args[1]
        assert call_kwargs["enable_editorial"] is False

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8", "--orchestrate", "--no-evidence"])
    def test_orchestrate_no_evidence(self, mock_get_session, mock_orch):
        mock_get_session.return_value = MagicMock()
        mock_orch.return_value = 0

        main()

        call_kwargs = mock_orch.call_args[1]
        assert call_kwargs["enable_evidence"] is False

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "sintese", "--edition", "5", "--orchestrate"])
    def test_orchestrate_sintese_uses_edition(self, mock_get_session, mock_orch):
        mock_get_session.return_value = MagicMock()
        mock_orch.return_value = 0

        main()

        call_kwargs = mock_orch.call_args[1]
        # sintese has period_arg="edition" → uses args.edition
        assert call_kwargs["period_value"] == 5

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "radar", "--orchestrate"])
    def test_orchestrate_defaults_week_to_current(self, mock_get_session, mock_orch):
        mock_get_session.return_value = MagicMock()
        mock_orch.return_value = 0

        main()

        call_kwargs = mock_orch.call_args[1]
        # Should use current ISO week when --week not specified
        current_week = datetime.now().isocalendar()[1]
        assert call_kwargs["period_value"] == current_week

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8", "--orchestrate"])
    def test_orchestrate_closes_session(self, mock_get_session, mock_orch):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_orch.return_value = 0

        main()

        mock_session.close.assert_called_once()

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8", "--orchestrate"])
    def test_orchestrate_closes_session_on_failure(self, mock_get_session, mock_orch):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_orch.side_effect = RuntimeError("Crash")

        with pytest.raises(RuntimeError):
            main()

        mock_session.close.assert_called_once()

    @patch("scripts.run_agents.orchestrate_single_agent")
    @patch("packages.database.session.get_session")
    @patch("sys.argv", ["run_agents.py", "all", "--week", "8", "--orchestrate"])
    def test_orchestrate_all_runs_all_agents(self, mock_get_session, mock_orch):
        mock_get_session.return_value = MagicMock()
        mock_orch.return_value = 0

        main()

        assert mock_orch.call_count == len(AGENTS)
        called_names = [call[0][0] for call in mock_orch.call_args_list]
        assert set(called_names) == set(AGENTS.keys())


# ---------------------------------------------------------------------------
# TestMainSubprocessMode — backward-compatible mode
# ---------------------------------------------------------------------------


class TestMainSubprocessMode:
    """Tests for main() in subprocess mode (default)."""

    @patch("scripts.run_agents.run_agent")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8"])
    def test_subprocess_calls_run_agent(self, mock_run):
        mock_run.return_value = 0
        main()
        mock_run.assert_called_once()

    @patch("scripts.run_agents.run_agent")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8", "--persist"])
    def test_subprocess_passes_persist(self, mock_run):
        mock_run.return_value = 0
        main()
        extra_args = mock_run.call_args[0][1]
        assert "--persist" in extra_args

    @patch("scripts.run_agents.run_agent")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8", "--dry-run"])
    def test_subprocess_passes_dry_run(self, mock_run):
        mock_run.return_value = 0
        main()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["dry_run"] is True

    @patch("scripts.run_agents.run_agent")
    @patch("sys.argv", ["run_agents.py", "sintese", "--edition", "3", "--send"])
    def test_subprocess_passes_send_for_sintese(self, mock_run):
        mock_run.return_value = 0
        main()
        extra_args = mock_run.call_args[0][1]
        assert "--send" in extra_args
        assert "--edition" in extra_args

    @patch("scripts.run_agents.run_agent")
    @patch("sys.argv", ["run_agents.py", "radar", "--week", "8"])
    def test_subprocess_passes_week_as_extra_arg(self, mock_run):
        mock_run.return_value = 0
        main()
        extra_args = mock_run.call_args[0][1]
        assert "--week" in extra_args
        assert "8" in extra_args

    @patch("scripts.run_agents.run_agent")
    @patch("sys.argv", ["run_agents.py", "all", "--week", "8"])
    def test_subprocess_sintese_does_not_get_week_arg(self, mock_run):
        """SINTESE uses --edition, not --week. Passing --week causes exit code 2."""
        mock_run.return_value = 0
        main()
        # Find the call for sintese
        for call in mock_run.call_args_list:
            agent_name = call[0][0]
            extra_args = call[0][1]
            if agent_name == "sintese":
                assert "--week" not in extra_args, (
                    "SINTESE should not receive --week (it only accepts --edition)"
                )
                break
        else:
            pytest.fail("sintese was never called")
