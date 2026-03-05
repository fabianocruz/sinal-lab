"""Shared persistence layer for Sinal.lab agents.

Extracts duplicated AgentRun + ContentPiece creation from SINTESE and
FUNDING main.py into reusable functions. Gives all 5 agents DB persistence.

Usage:
    from apps.agents.base.persistence import persist_agent_output

    agent_run, content = persist_agent_output(session, agent, result, slug)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from apps.agents.base.output import AgentOutput
from packages.database.models.agent_run import AgentRun
from packages.database.models.content_piece import ContentPiece

logger = logging.getLogger(__name__)


def persist_agent_run(
    session: Session,
    agent: "BaseAgent",  # noqa: F821 — forward ref to avoid circular import
    result: AgentOutput,
) -> AgentRun:
    """Create an AgentRun record from a completed agent run.

    Maps agent metadata (name, run_id, timing, item counts) and result
    confidence into an AgentRun ORM record. Does NOT commit — caller
    manages the transaction.

    Args:
        session: SQLAlchemy session.
        agent: A completed BaseAgent instance (after .run()).
        result: The AgentOutput produced by the agent.

    Returns:
        AgentRun record (added to session, not committed).
    """
    now = datetime.now(timezone.utc)

    # Extract data sources from provenance tracker
    data_sources = None
    if hasattr(agent, "provenance") and agent.provenance:
        data_sources = {"sources": agent.provenance.get_sources()}

    # Extract error count
    error_count = len(agent._errors) if hasattr(agent, "_errors") else 0

    agent_run = AgentRun(
        id=uuid.uuid4(),
        agent_name=agent.agent_name,
        run_id=agent.run_id,
        started_at=agent.started_at or now,
        completed_at=agent.completed_at or now,
        status="completed",
        items_collected=len(agent._collected_data) if hasattr(agent, "_collected_data") else 0,
        items_processed=len(agent._processed_data) if hasattr(agent, "_processed_data") else 0,
        items_output=1,
        avg_confidence=result.confidence.composite,
        data_sources=data_sources,
        error_count=error_count,
    )

    session.add(agent_run)
    logger.info("Prepared AgentRun for %s (run_id=%s)", agent.agent_name, agent.run_id)
    return agent_run


def persist_content_piece(
    session: Session,
    result: AgentOutput,
    slug: str,
    review_status: str = "pending_review",
    body_html: Optional[str] = None,
) -> ContentPiece:
    """Create or update a ContentPiece by slug.

    If a ContentPiece with the given slug already exists, updates its body,
    confidence, sources, summary, and review_status. Otherwise creates a new
    record. Does NOT commit — caller manages the transaction.

    Args:
        session: SQLAlchemy session.
        result: The AgentOutput to persist.
        slug: Unique slug for the content piece.
        review_status: Initial review status (default: "pending_review").
        body_html: Optional pre-rendered HTML body.

    Returns:
        ContentPiece record (new or updated, not committed).
    """
    existing = session.query(ContentPiece).filter_by(slug=slug).first()

    now = datetime.now(timezone.utc)
    published_at = now if review_status == "published" else None

    if existing:
        existing.title = result.title
        existing.body_md = result.body_md
        existing.confidence_dq = result.confidence.dq_display
        existing.confidence_ac = result.confidence.ac_display
        existing.sources = result.sources
        existing.summary = result.summary
        existing.review_status = review_status
        existing.agent_run_id = result.run_id
        existing.agent_name = result.agent_name
        existing.content_type = result.content_type
        existing.metadata_ = result.metadata
        if published_at:
            existing.published_at = published_at
        if body_html is not None:
            existing.body_html = body_html
        logger.info("Updated ContentPiece slug=%s (status=%s)", slug, review_status)
        return existing

    piece = ContentPiece(
        id=uuid.uuid4(),
        title=result.title,
        slug=slug,
        body_md=result.body_md,
        body_html=body_html,
        summary=result.summary,
        content_type=result.content_type,
        agent_name=result.agent_name,
        agent_run_id=result.run_id,
        sources=result.sources,
        confidence_dq=result.confidence.dq_display,
        confidence_ac=result.confidence.ac_display,
        review_status=review_status,
        published_at=published_at,
        metadata_=result.metadata,
    )
    session.add(piece)
    logger.info("Created ContentPiece slug=%s", slug)
    return piece


def persist_agent_output(
    session: Session,
    agent: "BaseAgent",  # noqa: F821
    result: AgentOutput,
    slug: str,
    review_status: str = "pending_review",
    body_html: Optional[str] = None,
) -> Tuple[AgentRun, ContentPiece]:
    """Convenience: persist both AgentRun and ContentPiece, then commit.

    Rolls back the transaction on any error.

    Args:
        session: SQLAlchemy session.
        agent: A completed BaseAgent instance.
        result: The AgentOutput produced by the agent.
        slug: Unique slug for the content piece.
        review_status: Initial review status (default: "pending_review").
        body_html: Optional pre-rendered HTML body.

    Returns:
        Tuple of (AgentRun, ContentPiece).

    Raises:
        Exception: Re-raises after rollback on any persistence error.
    """
    try:
        agent_run = persist_agent_run(session, agent, result)
        content = persist_content_piece(
            session, result, slug,
            review_status=review_status,
            body_html=body_html,
        )
        session.commit()
        logger.info(
            "Persisted agent output: run=%s, slug=%s",
            agent.run_id, slug,
        )
        return (agent_run, content)
    except Exception:
        session.rollback()
        logger.error(
            "Failed to persist agent output for %s, rolled back",
            agent.run_id,
            exc_info=True,
        )
        raise
