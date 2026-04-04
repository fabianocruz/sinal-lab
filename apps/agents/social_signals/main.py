"""CLI entry point for the Social Signals Intelligence agent.

Usage:
    python -m apps.agents.social_signals.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.social_signals.main --week 14 --persist
    python -m apps.agents.social_signals.main --week 14 --dry-run --verbose
"""

import logging
from typing import Any

from apps.agents.base.cli import run_agent_cli
from apps.agents.social_signals.agent import SocialSignalsAgent

logger = logging.getLogger(__name__)


def _post_run_persist(
    agent: Any,
    result: Any,
    args: Any,
    session: Any,
) -> None:
    """Persist domain-specific data (signals, clusters, weekly pulse).

    Called by run_agent_cli after persist_agent_output when --persist is set.
    Bridges the cli post_run_fn signature to db_writer.persist_social_signals.
    """
    from apps.agents.social_signals.db_writer import persist_social_signals

    persist_social_signals(agent, result, session)
    session.commit()
    logger.info("Social Signals domain data committed to database")


def main() -> None:
    run_agent_cli(
        agent_class=SocialSignalsAgent,
        description="SOCIAL_SIGNALS — Sinal.lab Social Signal Intelligence Agent",
        default_output_dir="apps/agents/social_signals/output",
        slug_fn=lambda agent, args: f"social-signals-week-{args.week}",
        filename_fn=lambda agent, args: f"social-signals-week-{args.week}.md",
        post_run_fn=_post_run_persist,
    )


if __name__ == "__main__":
    main()
