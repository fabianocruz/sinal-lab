"""Integration tests for the agent orchestrator.

Unlike test_orchestrator.py (which mocks the editorial pipeline),
these tests exercise the full flow end-to-end with a real in-memory
database, verifying that records are actually written, cross-linked,
and rolled back correctly.

The editorial pipeline is still mocked (it requires LLM access),
but everything else runs against real SQLAlchemy sessions.
"""

from datetime import datetime, timezone
from typing import Any, List
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


class IntegrationAgent:
    """Full-featured agent for integration testing.

    Mimics a real agent with collect/process/score lifecycle
    data stored on the instance.
    """

    agent_name = "integration-agent"
    agent_category = "content"
    version = "1.0.0"

    def __init__(self, week_number: int = 1) -> None:
        self.week_number = week_number
        self.run_id = f"integration-agent-20260217-w{week_number}"
        self.started_at = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        self.completed_at = datetime(2026, 2, 17, 10, 5, 0, tzinfo=timezone.utc)
        self._collected_data: List[Any] = [
            {"title": f"Item {i}", "url": f"https://example.com/{i}"}
            for i in range(5)
        ]
        self._processed_data: List[Any] = self._collected_data[:4]
        self._scores: List[Any] = []
        self._errors: List[str] = []
        self.provenance = ProvenanceTracker()
        for i in range(3):
            self.provenance.track(
                source_url=f"https://source{i}.com",
                source_name=f"source-{i}",
                extraction_method="api",
            )

    def run(self) -> AgentOutput:
        body = (
            "# Integration Test Report\n\n"
            "## Findings\n\n"
            + " ".join(["analysis"] * 60) + "\n\n"
            "## Data\n\n"
            "| Metric | Value |\n|--------|-------|\n"
            "| Items | 5 |\n| Sources | 3 |\n"
        )
        return AgentOutput(
            title=f"Integration Report Week {self.week_number}",
            body_md=body,
            agent_name=self.agent_name,
            run_id=self.run_id,
            confidence=_make_confidence(dq=0.8, ac=0.75),
            sources=[f"source-{i}" for i in range(3)],
            content_type="DATA_REPORT",
            agent_category=self.agent_category,
            summary=f"Integration report for week {self.week_number}.",
        )

    def get_run_metadata(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "run_id": self.run_id,
            "items_collected": len(self._collected_data),
            "items_processed": len(self._processed_data),
        }


def _make_editorial_result(publish_ready: bool = True):
    result = MagicMock()
    result.publish_ready = publish_ready
    result.overall_grade = "A" if publish_ready else "C"
    result.all_flags = []
    result.layer_results = []
    result.seo_metadata = {}
    result.byline = None
    return result


# ---------------------------------------------------------------------------
# Integration tests — full pipeline
# ---------------------------------------------------------------------------


class TestOrchestratorFullPipeline:
    """End-to-end tests: agent → editorial → persist → verify DB state."""

    @patch("apps.agents.base.orchestrator.EditorialPipeline")
    def test_full_flow_approved(self, mock_pipeline_class, session: Session):
        """Agent runs → editorial approves → records persisted with approved status."""
        mock_pipeline = MagicMock()
        mock_pipeline.review.return_value = _make_editorial_result(publish_ready=True)
        mock_pipeline_class.return_value = mock_pipeline

        agent = IntegrationAgent(week_number=8)

        result = orchestrate_agent_run(
            agent, session=session, slug="integration-week-8",
            enable_editorial=True, persist=True,
        )

        # Verify OrchestrationResult
        assert isinstance(result, OrchestrationResult)
        assert result.persisted is True
        assert result.editorial_result is not None
        assert result.editorial_result.publish_ready is True

        # Verify DB: AgentRun
        runs = session.query(AgentRun).all()
        assert len(runs) == 1
        assert runs[0].agent_name == "integration-agent"
        assert runs[0].run_id == "integration-agent-20260217-w8"
        assert runs[0].status == "completed"

        # Verify DB: ContentPiece
        pieces = session.query(ContentPiece).all()
        assert len(pieces) == 1
        assert pieces[0].slug == "integration-week-8"
        assert pieces[0].review_status == "approved"
        assert pieces[0].title == "Integration Report Week 8"
        assert pieces[0].agent_run_id == "integration-agent-20260217-w8"

    @patch("apps.agents.base.orchestrator.EditorialPipeline")
    def test_full_flow_pending_review(self, mock_pipeline_class, session: Session):
        """Agent runs → editorial rejects → records persisted with pending_review."""
        mock_pipeline = MagicMock()
        mock_pipeline.review.return_value = _make_editorial_result(publish_ready=False)
        mock_pipeline_class.return_value = mock_pipeline

        agent = IntegrationAgent(week_number=9)

        result = orchestrate_agent_run(
            agent, session=session, slug="integration-week-9",
            enable_editorial=True, persist=True,
        )

        piece = session.query(ContentPiece).filter_by(slug="integration-week-9").first()
        assert piece is not None
        assert piece.review_status == "pending_review"
        assert result.editorial_result.publish_ready is False

    @patch("apps.agents.base.orchestrator.EditorialPipeline")
    def test_full_flow_editorial_failure_defaults_to_pending(self, mock_pipeline_class, session: Session):
        """If editorial pipeline crashes, review_status defaults to pending_review."""
        mock_pipeline = MagicMock()
        mock_pipeline.review.side_effect = RuntimeError("LLM unavailable")
        mock_pipeline_class.return_value = mock_pipeline

        agent = IntegrationAgent(week_number=10)

        result = orchestrate_agent_run(
            agent, session=session, slug="integration-week-10",
            enable_editorial=True, persist=True,
        )

        piece = session.query(ContentPiece).filter_by(slug="integration-week-10").first()
        assert piece is not None
        assert piece.review_status == "pending_review"
        assert result.editorial_result is None

    def test_full_flow_no_editorial(self, session: Session):
        """Agent runs → no editorial → records persisted with default pending_review."""
        agent = IntegrationAgent(week_number=11)

        result = orchestrate_agent_run(
            agent, session=session, slug="integration-week-11",
            enable_editorial=False, persist=True,
        )

        assert result.editorial_result is None
        piece = session.query(ContentPiece).filter_by(slug="integration-week-11").first()
        assert piece is not None
        assert piece.review_status == "pending_review"

    def test_full_flow_domain_persist_fn(self, session: Session):
        """Domain-specific persistence callback is called within the transaction."""
        agent = IntegrationAgent(week_number=12)
        domain_calls = []

        def track_domain(ag, output, sess):
            domain_calls.append({
                "agent_name": ag.agent_name,
                "output_title": output.title,
                "session_is_same": sess is session,
            })

        result = orchestrate_agent_run(
            agent, session=session, slug="integration-week-12",
            enable_editorial=False, persist=True,
            domain_persist_fn=track_domain,
        )

        assert len(domain_calls) == 1
        assert domain_calls[0]["agent_name"] == "integration-agent"
        assert domain_calls[0]["output_title"] == "Integration Report Week 12"
        assert domain_calls[0]["session_is_same"] is True

    def test_full_flow_domain_persist_failure_rolls_back(self, session: Session):
        """If domain_persist_fn fails, all records (AgentRun + ContentPiece) are rolled back."""
        agent = IntegrationAgent(week_number=13)

        def failing_domain(ag, output, sess):
            raise ValueError("Domain write failed")

        with pytest.raises(ValueError, match="Domain write failed"):
            orchestrate_agent_run(
                agent, session=session, slug="integration-week-13",
                enable_editorial=False, persist=True,
                domain_persist_fn=failing_domain,
            )

        # After rollback, no records should exist
        assert session.query(AgentRun).count() == 0
        assert session.query(ContentPiece).filter_by(slug="integration-week-13").count() == 0

    @patch("apps.agents.base.orchestrator.EditorialPipeline")
    def test_multiple_runs_different_slugs(self, mock_pipeline_class, session: Session):
        """Multiple orchestrations with different slugs create separate records."""
        mock_pipeline = MagicMock()
        mock_pipeline.review.return_value = _make_editorial_result(publish_ready=True)
        mock_pipeline_class.return_value = mock_pipeline

        for week in (1, 2, 3):
            agent = IntegrationAgent(week_number=week)
            orchestrate_agent_run(
                agent, session=session, slug=f"integration-week-{week}",
                enable_editorial=True, persist=True,
            )

        assert session.query(AgentRun).count() == 3
        assert session.query(ContentPiece).count() == 3

        slugs = {p.slug for p in session.query(ContentPiece).all()}
        assert slugs == {"integration-week-1", "integration-week-2", "integration-week-3"}

    def test_dry_run_no_persist(self, session: Session):
        """With persist=False, no DB records are created."""
        agent = IntegrationAgent(week_number=14)

        result = orchestrate_agent_run(
            agent, session=session, slug="integration-week-14",
            enable_editorial=False, persist=False,
        )

        assert result.persisted is False
        assert session.query(AgentRun).count() == 0
        assert session.query(ContentPiece).count() == 0

    def test_output_has_correct_confidence(self, session: Session):
        """Verify the AgentOutput confidence data flows through correctly."""
        agent = IntegrationAgent(week_number=15)

        result = orchestrate_agent_run(
            agent, session=session, slug="integration-week-15",
            enable_editorial=False, persist=True,
        )

        assert result.agent_output.confidence.data_quality == 0.8
        assert result.agent_output.confidence.analysis_confidence == 0.75
        assert result.agent_output.confidence.grade in ("A", "B")

        # ContentPiece should have mapped confidence
        piece = session.query(ContentPiece).filter_by(slug="integration-week-15").first()
        assert piece is not None
        assert piece.confidence_dq is not None
        assert piece.confidence_ac is not None
