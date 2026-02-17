"""Agent orchestrator with editorial-in-the-loop.

Connects the agent lifecycle to editorial review, persistence, and
evidence item writing in a single coordinated flow.

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
    """Run agent → editorial review → persist → evidence items.

    Flow:
        1. agent.run() → AgentOutput
        2. If enable_editorial: EditorialPipeline().review(output)
           → sets review_status based on publish_ready
        3. If persist: persist_agent_output() + optionally persist_raw_items()
           + optionally domain_persist_fn()

    Entity resolver is NOT called here — that's a cross-agent operation
    that belongs in scripts/run_agents.py after all agents complete.

    Args:
        agent: Agent instance (not yet run).
        session: SQLAlchemy session (required if persist=True).
        slug: Content slug for persistence.
        enable_editorial: Run editorial pipeline before persistence.
        enable_evidence: Persist raw items as evidence.
        persist: Whether to persist AgentRun + ContentPiece.
        domain_persist_fn: Optional callback(agent, result, session)
            for agent-specific persistence (funding rounds, company profiles).

    Returns:
        OrchestrationResult with output, editorial result, and stats.
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
