"""CLI entry point for the VOZES agent.

Usage:
    python -m apps.agents.vozes.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.vozes.main --week 14 --persist
    python -m apps.agents.vozes.main --week 14 --dry-run --verbose
"""

from __future__ import annotations

import logging
from typing import Any

from apps.agents.base.cli import run_agent_cli
from apps.agents.vozes.agent import VozesAgent

logger = logging.getLogger(__name__)


def _post_run_persist(
    agent: Any,
    result: Any,
    args: Any,
    session: Any,
) -> None:
    """Persist domain-specific data (individual social signals).

    Called by run_agent_cli after persist_agent_output when --persist is set.
    Bridges the cli post_run_fn signature to db_writer.persist_vozes_signals.
    """
    from apps.agents.vozes.db_writer import persist_vozes_signals

    persist_vozes_signals(agent, result, session)
    session.commit()
    logger.info("VOZES signal data committed to database")


def main() -> None:
    run_agent_cli(
        agent_class=VozesAgent,
        description="VOZES - Sinal.lab Social Voice Monitoring Agent",
        default_output_dir="apps/agents/vozes/output",
        slug_fn=lambda agent, args: f"vozes-week-{args.week}",
        filename_fn=lambda agent, args: f"vozes-week-{args.week}.md",
        post_run_fn=_post_run_persist,
    )


if __name__ == "__main__":
    main()
