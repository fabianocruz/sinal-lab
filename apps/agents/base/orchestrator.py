"""Agent orchestrator with editorial-in-the-loop.

Connects the agent lifecycle to editorial review, persistence, and
evidence item writing in a single coordinated flow.

Editorial-in-the-Loop Flow
--------------------------
The orchestrator runs agents through a 3-step pipeline:

    1. agent.run()  →  AgentOutput (title, body_md, confidence, etc.)
    2. Editorial review  →  EditorialPipeline grades the output and
       sets review_status to "approved" (publish_ready=True) or
       "pending_review" (needs human review).  If editorial fails,
       the output is routed to human review as a safety net.
    3. Persistence  →  AgentRun + ContentPiece + optional evidence
       items + optional domain-specific records (e.g. funding rounds).

Atomic Transaction Pattern
--------------------------
All persistence in step 3 happens within a **single transaction**:
persist_agent_run() and persist_content_piece() are called without
committing, followed by evidence and domain writes, and finally a
single session.commit().  If any step raises, session.rollback()
undoes everything — no partial writes.

This differs from persist_agent_output() (the convenience wrapper),
which commits internally.  The orchestrator intentionally avoids it
to guarantee atomicity across the full write set.

Design Decisions
----------------
- Entity resolver is NOT called here — it's a cross-agent operation
  that belongs in scripts/run_agents.py after all agents complete.
- Domain-specific db_writers (funding rounds, company profiles) are
  passed via domain_persist_fn callback, keeping the orchestrator
  agent-agnostic.

Usage:
    from apps.agents.base.orchestrator import orchestrate_agent_run

    result = orchestrate_agent_run(
        agent, session=session, slug="radar-week-7",
        enable_editorial=True, persist=True,
    )
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from apps.agents.base.evidence_writer import persist_raw_items
from apps.agents.base.output import AgentOutput
from apps.agents.base.persistence import persist_agent_run, persist_content_piece
from apps.agents.editorial.pipeline import EditorialPipeline

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Result of a full orchestrated agent run."""

    agent_output: AgentOutput
    editorial_result: Optional[Any] = None  # EditorialResult when editorial is enabled
    evidence_stats: Optional[Dict[str, int]] = None
    persisted: bool = False


def orchestrate_agent_run(
    agent: Any,
    session: Optional[Session] = None,
    slug: Optional[str] = None,
    enable_editorial: bool = True,
    enable_evidence: bool = False,
    persist: bool = True,
    domain_persist_fn: Optional[Callable[..., None]] = None,
) -> OrchestrationResult:
    """Run agent -> editorial review -> persist -> evidence items.

    Flow:
        1. ``agent.run()`` produces an ``AgentOutput``.
        2. If *enable_editorial*: ``EditorialPipeline().review(output)``
           grades the content and sets *review_status* to ``"approved"``
           when ``publish_ready`` is True, or ``"pending_review"`` otherwise.
           Editorial failures are caught and default to ``"pending_review"``.
        3. If *persist*: writes AgentRun + ContentPiece + optional evidence
           items + optional domain records in a **single atomic transaction**
           (one ``session.commit()``, full ``session.rollback()`` on error).

    Entity resolver is NOT called here — that's a cross-agent operation
    that belongs in ``scripts/run_agents.py`` after all agents complete.

    Args:
        agent: Agent instance (not yet run).  Must implement ``run()``
            returning ``AgentOutput`` and expose ``agent_name``, ``run_id``.
        session: SQLAlchemy session (required if persist=True).
        slug: Content slug for persistence (used as ContentPiece unique key).
        enable_editorial: Run editorial pipeline before persistence.
        enable_evidence: Persist raw items (``agent._collected_data``) as
            evidence via ``persist_raw_items()``.
        persist: Whether to persist AgentRun + ContentPiece.
        domain_persist_fn: Optional ``callback(agent, agent_output, session)``
            for agent-specific persistence (e.g. funding rounds, company
            profiles).  Called inside the same transaction.

    Returns:
        OrchestrationResult with output, editorial result, and stats.

    Raises:
        Exception: Re-raises any persistence error after rolling back
            the transaction.
    """
    # Step 1: Run agent
    logger.info("Orchestrating run for agent '%s'", agent.agent_name)
    agent_output = agent.run()

    # Step 2: Editorial review (optional)
    editorial_result = None
    review_status = "pending_review"

    if enable_editorial:
        try:
            pipeline = EditorialPipeline()
            editorial_result = pipeline.review(agent_output)

            if editorial_result.publish_ready:
                review_status = "approved"
                logger.info("Editorial: approved for publishing")
            else:
                review_status = "pending_review"
                logger.info("Editorial: routed to human review")
        except Exception as e:
            logger.error("Editorial review failed: %s", e, exc_info=True)
            review_status = "pending_review"

    # Step 3: Persist (optional)
    evidence_stats = None
    persisted = False

    if persist and session and slug:
        try:
            # Use low-level functions (no auto-commit) so we can
            # roll back everything atomically if any step fails.
            persist_agent_run(session, agent, agent_output)
            persist_content_piece(
                session, agent_output, slug,
                review_status=review_status,
            )

            # Evidence items
            if enable_evidence:
                collected = getattr(agent, "_collected_data", [])
                if collected:
                    evidence_stats = persist_raw_items(
                        session, collected,
                        agent_name=agent.agent_name,
                        collector_run_id=agent.run_id,
                    )

            # Domain-specific persistence
            if domain_persist_fn:
                domain_persist_fn(agent, agent_output, session)

            session.commit()
            persisted = True
            logger.info("Orchestration complete: persisted slug=%s", slug)

        except Exception as e:
            logger.error("Persistence failed, rolling back: %s", e, exc_info=True)
            session.rollback()
            raise

    return OrchestrationResult(
        agent_output=agent_output,
        editorial_result=editorial_result,
        evidence_stats=evidence_stats,
        persisted=persisted,
    )
