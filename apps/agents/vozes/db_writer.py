"""Database persistence for the VOZES agent.

Handles upsert of individual SocialSignal records. Cluster and WeeklyPulse
persistence is handled by PULSO (which consumes VOZES output).

Uses the same _upsert_social_signal logic from social_signals/db_writer.py.
"""

from __future__ import annotations

import logging
from typing import Any, List

from sqlalchemy.orm import Session

from apps.agents.social_signals.db_writer import _upsert_social_signal
from apps.agents.social_signals.models import ProcessedSignal

logger = logging.getLogger(__name__)


def persist_vozes_signals(
    agent: Any,
    agent_output: Any,
    session: Session,
) -> None:
    """Domain persistence callback for the orchestrator.

    Matches the signature expected by orchestrator's domain_persist_fn:
    (agent, agent_output, session) -> None.

    Persists individual SocialSignal records (one per classified post).
    Cluster-level persistence is handled by PULSO agent.

    Args:
        agent: VozesAgent instance.
        agent_output: AgentOutput from agent.output().
        session: SQLAlchemy session (caller manages commit/rollback).
    """
    all_signals: List[ProcessedSignal] = getattr(agent, "_all_signals", [])
    run_id: str = getattr(agent, "run_id", "")

    stats = {"inserted": 0, "updated": 0}

    for signal in all_signals:
        result = _upsert_social_signal(
            session,
            signal,
            cluster_db_id=None,  # No cluster assignment yet (PULSO handles that)
            agent_run_id=run_id,
        )
        if result == "inserted":
            stats["inserted"] += 1
        else:
            stats["updated"] += 1

    session.flush()

    logger.info(
        "VOZES persistence: %d signals inserted, %d updated",
        stats["inserted"],
        stats["updated"],
    )
