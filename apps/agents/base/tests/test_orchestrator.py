"""Tests for the agent orchestrator with editorial-in-the-loop.

Tests orchestrate_agent_run which connects:
agent.run() → editorial review → persistence → evidence items.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker
from packages.database.models.base import Base
from packages.database.models.agent_run import AgentRun
from packages.database.models.content_piece import ContentPiece

from apps.agents.base.orchestrator import (
    OrchestrationResult,
    orchestrate_agent_run,
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
    """Minimal agent for testing the orchestrator."""

    agent_name = "test-agent"
    agent_category = "content"
    version = "0.1.0"

    def __init__(self) -> None:
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
        self._run_called = False

    def run(self) -> AgentOutput:
        self._run_called = True
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


def _make_editorial_result(publish_ready: bool = True):
    """Create a mock EditorialResult."""
    result = MagicMock()
    result.publish_ready = publish_ready
    result.overall_grade = "A" if publish_ready else "D"
    result.all_flags = []
    result.layer_results = []
    result.seo_metadata = {}
    result.byline = None
    return result


# ---------------------------------------------------------------------------
# TestOrchestrateAgentRun
# ---------------------------------------------------------------------------


class TestOrchestrateAgentRun:
    """Tests for orchestrate_agent_run()."""

    def test_runs_agent(self, session: Session):
        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=False,
        )

        assert agent._run_called
        assert result.agent_output is not None
        assert result.agent_output.title == "Test Report"

    def test_returns_orchestration_result(self, session: Session):
        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=False,
        )

        assert isinstance(result, OrchestrationResult)

    @patch("apps.agents.base.orchestrator.EditorialPipeline")
    def test_editorial_runs_when_enabled(self, mock_pipeline_class, session: Session):
        mock_pipeline = MagicMock()
        mock_pipeline.review.return_value = _make_editorial_result(publish_ready=True)
        mock_pipeline_class.return_value = mock_pipeline

        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=True, persist=False,
        )

        mock_pipeline.review.assert_called_once()
        assert result.editorial_result is not None

    def test_editorial_skipped_when_disabled(self, session: Session):
        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=False,
        )

        assert result.editorial_result is None

    @patch("apps.agents.base.orchestrator.EditorialPipeline")
    def test_publish_ready_sets_approved_status(self, mock_pipeline_class, session: Session):
        mock_pipeline = MagicMock()
        mock_pipeline.review.return_value = _make_editorial_result(publish_ready=True)
        mock_pipeline_class.return_value = mock_pipeline

        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=True, persist=True,
        )

        # Content piece should have review_status = "approved"
        piece = session.query(ContentPiece).filter_by(slug="test-slug").first()
        assert piece is not None
        assert piece.review_status == "approved"

    @patch("apps.agents.base.orchestrator.EditorialPipeline")
    def test_not_publish_ready_sets_pending_review(self, mock_pipeline_class, session: Session):
        mock_pipeline = MagicMock()
        mock_pipeline.review.return_value = _make_editorial_result(publish_ready=False)
        mock_pipeline_class.return_value = mock_pipeline

        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=True, persist=True,
        )

        piece = session.query(ContentPiece).filter_by(slug="test-slug").first()
        assert piece is not None
        assert piece.review_status == "pending_review"

    def test_persists_agent_run_and_content(self, session: Session):
        agent = FakeAgent()

        orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=True,
        )

        runs = session.query(AgentRun).all()
        pieces = session.query(ContentPiece).all()
        assert len(runs) == 1
        assert len(pieces) == 1
        assert runs[0].agent_name == "test-agent"
        assert pieces[0].slug == "test-slug"

    def test_no_persist_when_disabled(self, session: Session):
        agent = FakeAgent()

        orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=False,
        )

        assert session.query(AgentRun).count() == 0
        assert session.query(ContentPiece).count() == 0

    def test_persisted_flag_set(self, session: Session):
        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=True,
        )

        assert result.persisted is True

    def test_persisted_flag_not_set(self, session: Session):
        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=False,
        )

        assert result.persisted is False

    def test_domain_persist_fn_called(self, session: Session):
        agent = FakeAgent()
        domain_fn = MagicMock()

        orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=True,
            domain_persist_fn=domain_fn,
        )

        domain_fn.assert_called_once()
        # Should receive (agent, result, session)
        call_args = domain_fn.call_args[0]
        assert call_args[0] is agent  # agent
        assert call_args[2] is session  # session

    def test_domain_persist_fn_not_called_when_no_persist(self, session: Session):
        agent = FakeAgent()
        domain_fn = MagicMock()

        orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=False,
            domain_persist_fn=domain_fn,
        )

        domain_fn.assert_not_called()

    @patch("apps.agents.base.orchestrator.persist_raw_items")
    def test_evidence_items_persisted(self, mock_persist_raw, session: Session):
        mock_persist_raw.return_value = {"inserted": 5, "updated": 0, "skipped": 0}

        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=True,
            enable_evidence=True,
        )

        mock_persist_raw.assert_called_once()
        assert result.evidence_stats is not None
        assert result.evidence_stats["inserted"] == 5

    @patch("apps.agents.base.orchestrator.persist_raw_items")
    def test_evidence_items_skipped(self, mock_persist_raw, session: Session):
        agent = FakeAgent()

        result = orchestrate_agent_run(
            agent, session=session, slug="test-slug",
            enable_editorial=False, persist=True,
            enable_evidence=False,
        )

        mock_persist_raw.assert_not_called()
        assert result.evidence_stats is None

    def test_rolls_back_on_persist_error(self, session: Session):
        """If persistence fails, no records should be committed."""
        agent = FakeAgent()
        agent.agent_name = "x" * 200  # Too long for String(100)

        with pytest.raises(Exception):
            orchestrate_agent_run(
                agent, session=session, slug="error-slug",
                enable_editorial=False, persist=True,
            )

        # Verify no records were persisted
        assert session.query(ContentPiece).filter_by(slug="error-slug").count() == 0
