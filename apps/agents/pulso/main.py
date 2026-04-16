"""CLI entry point for the PULSO agent.

Usage:
    python -m apps.agents.pulso.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.pulso.main --week 16 --persist
    python -m apps.agents.pulso.main --week 16 --dry-run --verbose
    python -m apps.agents.pulso.main --week 16 --vozes-output path/to/vozes.json
"""

from __future__ import annotations

import argparse
import logging
from typing import Any

from apps.agents.base.cli import run_agent_cli
from apps.agents.pulso.agent import PulsoAgent

logger = logging.getLogger(__name__)


def _add_pulso_args(parser: argparse.ArgumentParser) -> None:
    """Add PULSO-specific CLI arguments."""
    parser.add_argument(
        "--vozes-output",
        type=str,
        default=None,
        help="Path to VOZES agent output JSON file (signals input)",
    )


def _post_run_persist(
    agent: Any,
    result: Any,
    args: Any,
    session: Any,
) -> None:
    """Persist domain-specific data (clusters, weekly pulse).

    Called by run_agent_cli after persist_agent_output when --persist is set.
    """
    from apps.agents.pulso.db_writer import persist_pulso_data

    persist_pulso_data(agent, result, session)
    session.commit()
    logger.info("PULSO domain data committed to database")


def main() -> None:
    run_agent_cli(
        agent_class=PulsoAgent,
        description="PULSO — Sinal.lab Social Signal Clustering & Scoring Agent",
        default_output_dir="apps/agents/pulso/output",
        slug_fn=lambda agent, args: f"pulso-week-{args.week}",
        filename_fn=lambda agent, args: f"pulso-week-{args.week}.md",
        post_run_fn=_post_run_persist,
        extra_args_fn=_add_pulso_args,
    )


if __name__ == "__main__":
    main()
