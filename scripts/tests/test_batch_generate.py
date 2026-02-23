"""Tests for scripts/batch_generate.py — batch content generation.

Validates pure helper functions (_compute_week, _compute_published_at),
slug existence check, publish promotion logic, run_batch orchestration,
and the BATCH_AGENTS constant.

Uses SQLite in-memory with StaticPool (same pattern as API tests).

Run: pytest scripts/tests/test_batch_generate.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base
from packages.database.models.content_piece import ContentPiece

from scripts.batch_generate import (
    BATCH_AGENTS,
    _PUB_ANCHOR,
    _compute_published_at,
    _compute_week,
    _publish_approved_pieces,
    _slug_exists,
    run_batch,
)
from scripts.run_agents import AGENTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def session(engine):
    """Provide a database session for each test."""
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _insert_piece(session, slug, agent_name="sintese", review_status="approved"):
    """Insert a minimal ContentPiece via ORM for testing."""
    piece = ContentPiece(
        id=uuid.uuid4(),
        title=f"Test: {slug}",
        slug=slug,
        body_md="Test body",
        content_type="DATA_REPORT",
        agent_name=agent_name,
        review_status=review_status,
    )
    session.add(piece)
    session.commit()


# ---------------------------------------------------------------------------
# BATCH_AGENTS constant
# ---------------------------------------------------------------------------


def test_batch_agents_has_five_agents():
    """BATCH_AGENTS contains exactly the 5 content agents."""
    assert len(BATCH_AGENTS) == 5


def test_batch_agents_names():
    """BATCH_AGENTS lists the expected agent names in order."""
    assert BATCH_AGENTS == ["sintese", "radar", "codigo", "funding", "mercado"]


def test_batch_agents_all_in_agents_config():
    """Every agent in BATCH_AGENTS has a corresponding entry in AGENTS."""
    for name in BATCH_AGENTS:
        assert name in AGENTS, f"{name} missing from AGENTS config"


def test_batch_agents_excludes_index():
    """INDEX agent is intentionally excluded from batch runs."""
    assert "index" not in BATCH_AGENTS


# ---------------------------------------------------------------------------
# _compute_week()
# ---------------------------------------------------------------------------


def test_compute_week_first_edition():
    """First edition (index 0) returns the start_week itself."""
    assert _compute_week(start_week=1, edition_index=0) == 1
    assert _compute_week(start_week=10, edition_index=0) == 10


def test_compute_week_sequential():
    """Consecutive editions increment the week by 1."""
    assert _compute_week(start_week=1, edition_index=1) == 2
    assert _compute_week(start_week=1, edition_index=2) == 3
    assert _compute_week(start_week=5, edition_index=3) == 8


def test_compute_week_wraps_at_52():
    """Week numbers wrap from 52 back to 1."""
    assert _compute_week(start_week=52, edition_index=0) == 52
    assert _compute_week(start_week=52, edition_index=1) == 1
    assert _compute_week(start_week=52, edition_index=2) == 2


def test_compute_week_full_cycle():
    """52 editions from week 1 returns to week 52, then wraps."""
    assert _compute_week(start_week=1, edition_index=51) == 52
    assert _compute_week(start_week=1, edition_index=52) == 1


def test_compute_week_stays_in_range():
    """All computed weeks are in [1, 52] for a large range."""
    for idx in range(200):
        week = _compute_week(start_week=1, edition_index=idx)
        assert 1 <= week <= 52, f"Week {week} out of range at index {idx}"


# ---------------------------------------------------------------------------
# _compute_published_at()
# ---------------------------------------------------------------------------


def test_compute_published_at_start_edition_returns_anchor():
    """The start edition maps exactly to the anchor date."""
    result = _compute_published_at(start_edition=19, edition_number=19)
    assert result == _PUB_ANCHOR


def test_compute_published_at_next_edition_adds_one_week():
    """Edition start+1 is one week after the anchor."""
    result = _compute_published_at(start_edition=19, edition_number=20)
    assert result == _PUB_ANCHOR + timedelta(weeks=1)


def test_compute_published_at_30_editions_span():
    """30 editions span 29 weeks from anchor."""
    result = _compute_published_at(start_edition=19, edition_number=48)
    assert result == _PUB_ANCHOR + timedelta(weeks=29)


def test_compute_published_at_returns_utc():
    """All computed dates have UTC timezone."""
    result = _compute_published_at(start_edition=1, edition_number=5)
    assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# _slug_exists()
# ---------------------------------------------------------------------------


def test_slug_exists_returns_false_for_missing(session):
    """_slug_exists returns False when slug is not in the database."""
    assert _slug_exists(session, "nonexistent-slug") is False


def test_slug_exists_returns_true_for_existing(session):
    """_slug_exists returns True when slug exists in the database."""
    _insert_piece(session, "test-slug-exists")
    assert _slug_exists(session, "test-slug-exists") is True


def test_slug_exists_checks_exact_match(session):
    """_slug_exists doesn't match partial slugs."""
    _insert_piece(session, "sinal-semanal-19")
    assert _slug_exists(session, "sinal-semanal-1") is False
    assert _slug_exists(session, "sinal-semanal-19") is True


# ---------------------------------------------------------------------------
# _publish_approved_pieces()
# ---------------------------------------------------------------------------


def test_publish_approved_promotes_to_published(session):
    """Approved pieces matching slug patterns get promoted to published."""
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="approved")

    promoted = _publish_approved_pieces(
        session, start_edition=19, start_week=1, editions=1, dry_run=False,
    )

    assert promoted == 1
    piece = session.query(ContentPiece).filter(ContentPiece.slug == "sinal-semanal-19").first()
    assert piece.review_status == "published"
    assert piece.published_at is not None


def test_publish_approved_sets_correct_date(session):
    """Published pieces get the computed publication date."""
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="approved")

    _publish_approved_pieces(
        session, start_edition=19, start_week=1, editions=1, dry_run=False,
    )

    piece = session.query(ContentPiece).filter(ContentPiece.slug == "sinal-semanal-19").first()
    # SQLite strips timezone info, so compare without tz
    assert piece.published_at.replace(tzinfo=None) == _PUB_ANCHOR.replace(tzinfo=None)


def test_publish_approved_skips_already_published(session):
    """Already-published pieces are not counted or modified."""
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="published")

    promoted = _publish_approved_pieces(
        session, start_edition=19, start_week=1, editions=1, dry_run=False,
    )

    assert promoted == 0


def test_publish_approved_skips_draft(session):
    """Draft pieces are not promoted."""
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="draft")

    promoted = _publish_approved_pieces(
        session, start_edition=19, start_week=1, editions=1, dry_run=False,
    )

    assert promoted == 0


def test_publish_approved_dry_run_does_not_modify(session):
    """Dry run counts promotable pieces without modifying them."""
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="approved")

    promoted = _publish_approved_pieces(
        session, start_edition=19, start_week=1, editions=1, dry_run=True,
    )

    assert promoted == 1
    piece = session.query(ContentPiece).filter(ContentPiece.slug == "sinal-semanal-19").first()
    assert piece.review_status == "approved"  # NOT modified


def test_publish_approved_multiple_editions(session):
    """Multiple editions with approved pieces all get promoted."""
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="approved")
    _insert_piece(session, "sinal-semanal-20", agent_name="sintese", review_status="approved")
    _insert_piece(session, "radar-week-1", agent_name="radar", review_status="approved")

    promoted = _publish_approved_pieces(
        session, start_edition=19, start_week=1, editions=2, dry_run=False,
    )

    assert promoted == 3


def test_publish_approved_empty_db(session):
    """No errors when database is empty."""
    promoted = _publish_approved_pieces(
        session, start_edition=19, start_week=1, editions=5, dry_run=False,
    )
    assert promoted == 0


# ---------------------------------------------------------------------------
# run_batch() — with mocked orchestrator
# ---------------------------------------------------------------------------


@patch("packages.database.session.get_session")
@patch("scripts.batch_generate.orchestrate_single_agent")
def test_run_batch_calls_all_agents_per_edition(mock_orchestrate, mock_get_session, session):
    """run_batch calls orchestrate_single_agent for every agent in every edition."""
    mock_get_session.return_value = session
    mock_orchestrate.return_value = 0  # success

    successes, failures = run_batch(
        editions=2,
        start_edition=19,
        start_week=1,
        enable_editorial=True,
        enable_evidence=True,
        dry_run=False,
        verbose=False,
    )

    # 2 editions × 5 agents = 10 calls
    assert mock_orchestrate.call_count == 10
    assert successes == 10
    assert failures == 0


@patch("packages.database.session.get_session")
@patch("scripts.batch_generate.orchestrate_single_agent")
def test_run_batch_counts_failures(mock_orchestrate, mock_get_session, session):
    """Orchestrator failures increment the failure counter."""
    mock_get_session.return_value = session
    mock_orchestrate.return_value = 1  # failure

    successes, failures = run_batch(
        editions=1,
        start_edition=19,
        start_week=1,
        enable_editorial=True,
        enable_evidence=True,
        dry_run=False,
        verbose=False,
    )

    assert successes == 0
    assert failures == 5  # all 5 agents failed


@patch("packages.database.session.get_session")
@patch("scripts.batch_generate.orchestrate_single_agent")
def test_run_batch_skips_existing_slugs(mock_orchestrate, mock_get_session, session):
    """Existing slugs are skipped (idempotency)."""
    mock_get_session.return_value = session
    mock_orchestrate.return_value = 0

    # Pre-insert the sintese slug for edition 19
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="published")

    successes, failures = run_batch(
        editions=1,
        start_edition=19,
        start_week=1,
        enable_editorial=True,
        enable_evidence=True,
        dry_run=False,
        verbose=False,
    )

    # sintese skipped, 4 other agents called
    assert mock_orchestrate.call_count == 4
    assert successes == 5  # 1 skip + 4 ok
    assert failures == 0


@patch("packages.database.session.get_session")
@patch("scripts.batch_generate.orchestrate_single_agent")
def test_run_batch_dry_run_skips_orchestrator(mock_orchestrate, mock_get_session, session):
    """Dry run does not call the orchestrator at all."""
    mock_get_session.return_value = session

    successes, failures = run_batch(
        editions=2,
        start_edition=19,
        start_week=1,
        enable_editorial=True,
        enable_evidence=True,
        dry_run=True,
        verbose=False,
    )

    mock_orchestrate.assert_not_called()
    assert successes == 10  # 2 × 5 = 10 dry-run successes
    assert failures == 0


@patch("packages.database.session.get_session")
@patch("scripts.batch_generate.orchestrate_single_agent")
def test_run_batch_passes_correct_period_values(mock_orchestrate, mock_get_session, session):
    """Sintese gets edition number; other agents get week number."""
    mock_get_session.return_value = session
    mock_orchestrate.return_value = 0

    run_batch(
        editions=1,
        start_edition=19,
        start_week=5,
        enable_editorial=True,
        enable_evidence=True,
        dry_run=False,
        verbose=False,
    )

    calls = mock_orchestrate.call_args_list
    # First call is sintese with period_value=edition_number=19
    assert calls[0][1]["period_value"] == 19
    assert calls[0][0][0] == "sintese"
    # Second call is radar with period_value=week_number=5
    assert calls[1][1]["period_value"] == 5
    assert calls[1][0][0] == "radar"


@patch("packages.database.session.get_session")
@patch("scripts.batch_generate.orchestrate_single_agent")
def test_run_batch_promotes_approved_after_all_editions(mock_orchestrate, mock_get_session, session):
    """After running all editions, approved pieces are promoted to published."""
    mock_get_session.return_value = session
    mock_orchestrate.return_value = 0

    # Pre-insert an approved piece that matches expected slug
    _insert_piece(session, "sinal-semanal-19", agent_name="sintese", review_status="approved")

    run_batch(
        editions=1,
        start_edition=19,
        start_week=1,
        enable_editorial=True,
        enable_evidence=True,
        dry_run=False,
        verbose=False,
    )

    # The approved piece should now be published
    piece = session.query(ContentPiece).filter(ContentPiece.slug == "sinal-semanal-19").first()
    assert piece.review_status == "published"


@patch("packages.database.session.get_session")
@patch("scripts.batch_generate.orchestrate_single_agent")
def test_run_batch_passes_editorial_and_evidence_flags(mock_orchestrate, mock_get_session, session):
    """Editorial and evidence flags are forwarded to the orchestrator."""
    mock_get_session.return_value = session
    mock_orchestrate.return_value = 0

    run_batch(
        editions=1,
        start_edition=19,
        start_week=1,
        enable_editorial=False,
        enable_evidence=False,
        dry_run=False,
        verbose=False,
    )

    for call in mock_orchestrate.call_args_list:
        assert call[1]["enable_editorial"] is False
        assert call[1]["enable_evidence"] is False
