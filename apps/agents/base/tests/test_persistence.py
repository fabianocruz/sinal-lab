"""Tests for shared persistence layer.

Tests persist_agent_run, persist_content_piece, and persist_agent_output
using an in-memory SQLite database.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker
from packages.database.models.base import Base
from packages.database.models.agent_run import AgentRun
from packages.database.models.content_piece import ContentPiece

from apps.agents.base.persistence import (
    persist_agent_run,
    persist_content_piece,
    persist_agent_output,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Provide a transactional database session for tests."""
    factory = sessionmaker(bind=engine)
    sess = factory()
    yield sess
    sess.rollback()
    sess.close()


def _make_confidence(dq: float = 0.7, ac: float = 0.6) -> ConfidenceScore:
    return ConfidenceScore(data_quality=dq, analysis_confidence=ac, source_count=3)


def _make_agent(
    name: str = "radar",
    run_id: Optional[str] = None,
    items_collected: int = 50,
    items_processed: int = 40,
) -> MagicMock:
    """Build a mock agent mimicking BaseAgent public interface."""
    agent = MagicMock()
    agent.agent_name = name
    agent.run_id = run_id or f"{name}-20260217-001"
    agent.started_at = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
    agent.completed_at = datetime(2026, 2, 17, 10, 1, 0, tzinfo=timezone.utc)
    agent._collected_data = list(range(items_collected))
    agent._processed_data = list(range(items_processed))
    agent._errors = []
    agent.provenance = ProvenanceTracker()
    agent.provenance.track(
        source_url="https://api.github.com",
        source_name="github-trending",
        extraction_method="api",
        confidence=0.8,
    )
    agent.provenance.track(
        source_url="https://news.ycombinator.com/rss",
        source_name="hackernews",
        extraction_method="rss",
        confidence=0.6,
    )
    return agent


def _make_result(
    title: str = "RADAR Report W7",
    slug_hint: str = "radar-week-7",
    confidence: Optional[ConfidenceScore] = None,
) -> AgentOutput:
    """Build a minimal AgentOutput for testing."""
    conf = confidence or _make_confidence()
    body = (
        "# Weekly Report\n\n"
        + " ".join(["word"] * 60)  # >50 words to pass validation
    )
    return AgentOutput(
        title=title,
        body_md=body,
        agent_name="radar",
        run_id="radar-20260217-001",
        confidence=conf,
        sources=["github-trending", "hackernews"],
        content_type="DATA_REPORT",
        agent_category="data",
        summary="A weekly radar report.",
    )


# ---------------------------------------------------------------------------
# TestPersistAgentRun
# ---------------------------------------------------------------------------


class TestPersistAgentRun:
    """Tests for persist_agent_run()."""

    def test_creates_agent_run_record(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert isinstance(run, AgentRun)
        assert run.id is not None

    def test_maps_agent_fields(self, session: Session):
        agent = _make_agent(name="codigo", run_id="codigo-20260217-abc")
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert run.agent_name == "codigo"
        assert run.run_id == "codigo-20260217-abc"
        assert run.started_at == agent.started_at

    def test_maps_timing_fields(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert run.started_at == agent.started_at
        assert run.completed_at is not None
        # completed_at should be set (either from agent or now)

    def test_maps_item_counts(self, session: Session):
        agent = _make_agent(items_collected=100, items_processed=80)
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert run.items_collected == 100
        assert run.items_processed == 80
        assert run.items_output == 1  # one output document

    def test_maps_confidence(self, session: Session):
        confidence = _make_confidence(dq=0.8, ac=0.7)
        agent = _make_agent()
        result = _make_result(confidence=confidence)

        run = persist_agent_run(session, agent, result)

        # composite = 0.8*0.6 + 0.7*0.4 = 0.48 + 0.28 = 0.76
        assert run.avg_confidence == pytest.approx(0.76, abs=0.01)

    def test_maps_data_sources(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert run.data_sources is not None
        sources = run.data_sources.get("sources", [])
        assert "github-trending" in sources
        assert "hackernews" in sources

    def test_status_is_completed(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert run.status == "completed"

    def test_error_count_is_zero(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert run.error_count == 0

    def test_does_not_commit(self, session: Session):
        """persist_agent_run should add to session but NOT commit."""
        agent = _make_agent()
        result = _make_result()

        persist_agent_run(session, agent, result)

        # The record is in the session (dirty/new) but not committed
        assert session.new or session.dirty  # at least one pending change

    def test_maps_error_count_from_agent(self, session: Session):
        agent = _make_agent()
        agent._errors = ["timeout", "parse_error"]
        result = _make_result()

        run = persist_agent_run(session, agent, result)

        assert run.error_count == 2


# ---------------------------------------------------------------------------
# TestPersistContentPiece
# ---------------------------------------------------------------------------


class TestPersistContentPiece:
    """Tests for persist_content_piece()."""

    def test_creates_new_content_piece(self, session: Session):
        result = _make_result()

        piece = persist_content_piece(session, result, slug="radar-week-7")

        assert isinstance(piece, ContentPiece)
        assert piece.slug == "radar-week-7"
        assert piece.title == "RADAR Report W7"

    def test_upserts_existing_by_slug(self, session: Session):
        """If slug already exists, update instead of insert."""
        # Create initial
        result1 = _make_result(title="Old Title")
        persist_content_piece(session, result1, slug="radar-week-7")
        session.flush()

        # Upsert with new data
        result2 = _make_result(title="New Title")
        piece = persist_content_piece(session, result2, slug="radar-week-7")
        session.flush()

        assert piece.title == "New Title"
        # Should only have 1 record with this slug
        count = session.query(ContentPiece).filter_by(slug="radar-week-7").count()
        assert count == 1

    def test_updates_body_on_upsert(self, session: Session):
        result1 = _make_result()
        persist_content_piece(session, result1, slug="test-slug")
        session.flush()

        result2 = _make_result()
        result2.body_md = "# Updated Body\n\n" + " ".join(["updated"] * 60)
        piece = persist_content_piece(session, result2, slug="test-slug")
        session.flush()

        assert "Updated Body" in piece.body_md

    def test_updates_confidence_on_upsert(self, session: Session):
        result1 = _make_result(confidence=_make_confidence(dq=0.5, ac=0.4))
        persist_content_piece(session, result1, slug="test-slug")
        session.flush()

        new_conf = _make_confidence(dq=0.9, ac=0.8)
        result2 = _make_result(confidence=new_conf)
        piece = persist_content_piece(session, result2, slug="test-slug")
        session.flush()

        # dq_display = 0.9 * 5 = 4.5, ac_display = 0.8 * 5 = 4.0
        assert piece.confidence_dq == pytest.approx(4.5, abs=0.1)
        assert piece.confidence_ac == pytest.approx(4.0, abs=0.1)

    def test_updates_sources_on_upsert(self, session: Session):
        result1 = _make_result()
        persist_content_piece(session, result1, slug="test-slug")
        session.flush()

        result2 = _make_result()
        result2.sources = ["new-source-1", "new-source-2"]
        piece = persist_content_piece(session, result2, slug="test-slug")
        session.flush()

        assert piece.sources == ["new-source-1", "new-source-2"]

    def test_confidence_uses_display_scale(self, session: Session):
        """ContentPiece stores confidence on 1-5 scale (dq_display/ac_display)."""
        confidence = _make_confidence(dq=0.6, ac=0.5)
        result = _make_result(confidence=confidence)

        piece = persist_content_piece(session, result, slug="test-slug")
        session.flush()

        # dq_display = 0.6 * 5 = 3.0, ac_display = 0.5 * 5 = 2.5
        assert piece.confidence_dq == pytest.approx(3.0, abs=0.1)
        assert piece.confidence_ac == pytest.approx(2.5, abs=0.1)

    def test_default_review_status(self, session: Session):
        result = _make_result()

        piece = persist_content_piece(session, result, slug="test-slug")

        assert piece.review_status == "pending_review"

    def test_custom_review_status(self, session: Session):
        result = _make_result()

        piece = persist_content_piece(
            session, result, slug="test-slug", review_status="approved"
        )

        assert piece.review_status == "approved"

    def test_optional_body_html(self, session: Session):
        result = _make_result()

        piece = persist_content_piece(
            session, result, slug="test-slug", body_html="<h1>Test</h1>"
        )

        assert piece.body_html == "<h1>Test</h1>"

    def test_does_not_commit(self, session: Session):
        """persist_content_piece should add to session but NOT commit."""
        result = _make_result()

        persist_content_piece(session, result, slug="test-slug")

        assert session.new or session.dirty

    def test_maps_content_type(self, session: Session):
        result = _make_result()
        result.content_type = "ANALYSIS"

        piece = persist_content_piece(session, result, slug="test-slug")

        assert piece.content_type == "ANALYSIS"

    def test_maps_agent_name(self, session: Session):
        result = _make_result()
        result.agent_name = "funding"

        piece = persist_content_piece(session, result, slug="test-slug")

        assert piece.agent_name == "funding"

    def test_maps_summary(self, session: Session):
        result = _make_result()
        result.summary = "Custom summary text."

        piece = persist_content_piece(session, result, slug="test-slug")

        assert piece.summary == "Custom summary text."


# ---------------------------------------------------------------------------
# TestPersistAgentOutput
# ---------------------------------------------------------------------------


class TestPersistAgentOutput:
    """Tests for persist_agent_output() — the convenience function."""

    def test_creates_both_records(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        agent_run, content = persist_agent_output(
            session, agent, result, slug="radar-week-7"
        )

        assert isinstance(agent_run, AgentRun)
        assert isinstance(content, ContentPiece)

    def test_returns_tuple(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        output = persist_agent_output(
            session, agent, result, slug="radar-week-7"
        )

        assert isinstance(output, tuple)
        assert len(output) == 2

    def test_commits_on_success(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        persist_agent_output(session, agent, result, slug="radar-week-7")

        # After commit, records should be queryable
        runs = session.query(AgentRun).all()
        pieces = session.query(ContentPiece).all()
        assert len(runs) == 1
        assert len(pieces) == 1

    def test_content_piece_links_to_agent_run(self, session: Session):
        agent = _make_agent(run_id="radar-20260217-linked")
        result = _make_result()
        result.run_id = "radar-20260217-linked"

        _, content = persist_agent_output(
            session, agent, result, slug="test-link"
        )

        assert content.agent_run_id == "radar-20260217-linked"

    def test_rolls_back_on_error(self, session: Session):
        """If an error occurs, no records should be persisted."""
        agent = _make_agent()
        result = _make_result()
        # Use a duplicate slug to force an error on the second call
        persist_agent_output(session, agent, result, slug="dup-slug")

        # Second call with same slug but different run_id → should fail on AgentRun unique
        agent2 = _make_agent(run_id="radar-20260217-002")
        result2 = _make_result()
        result2.run_id = "radar-20260217-002"

        # persist_agent_output for same slug should upsert ContentPiece (not error)
        # but the AgentRun run_id must be unique → no conflict
        # Let's force a real error by making session.commit() fail
        # Instead, test with a bad agent_name that's too long
        agent_bad = _make_agent()
        agent_bad.agent_name = "x" * 200  # exceeds String(100) for agent_name
        result_bad = _make_result()

        with pytest.raises(Exception):
            persist_agent_output(
                session, agent_bad, result_bad, slug="error-slug"
            )

        # After rollback, no "error-slug" record should exist
        # Need a fresh session since the old one may be in a bad state
        count = session.query(ContentPiece).filter_by(slug="error-slug").count()
        assert count == 0

    def test_passes_review_status(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        _, content = persist_agent_output(
            session, agent, result, slug="test-status",
            review_status="approved",
        )

        assert content.review_status == "approved"

    def test_passes_body_html(self, session: Session):
        agent = _make_agent()
        result = _make_result()

        _, content = persist_agent_output(
            session, agent, result, slug="test-html",
            body_html="<p>Report</p>",
        )

        assert content.body_html == "<p>Report</p>"


# ---------------------------------------------------------------------------
# TestAutoPublish
# ---------------------------------------------------------------------------


class TestAutoPublish:
    """Tests for auto-publish functionality (published_at)."""

    def test_published_status_sets_published_at(self, session: Session):
        """When review_status='published', published_at should be set."""
        result = _make_result()

        piece = persist_content_piece(
            session, result, slug="test-auto-pub",
            review_status="published",
        )
        session.flush()

        assert piece.published_at is not None

    def test_pending_review_leaves_published_at_none(self, session: Session):
        """Default pending_review should NOT set published_at."""
        result = _make_result()

        piece = persist_content_piece(
            session, result, slug="test-pending",
        )
        session.flush()

        assert piece.published_at is None

    def test_upsert_to_published_sets_published_at(self, session: Session):
        """Upsert from pending_review → published sets published_at."""
        result = _make_result()
        persist_content_piece(session, result, slug="test-upsert-pub")
        session.flush()

        piece = persist_content_piece(
            session, result, slug="test-upsert-pub",
            review_status="published",
        )
        session.flush()

        assert piece.published_at is not None

    def test_persist_agent_output_published(self, session: Session):
        """Full persist with published status sets published_at."""
        agent = _make_agent()
        result = _make_result()

        _, content = persist_agent_output(
            session, agent, result, slug="test-full-pub",
            review_status="published",
        )

        assert content.review_status == "published"
        assert content.published_at is not None
