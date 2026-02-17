"""CLI entry point for the FUNDING agent.

Usage:
    python -m apps.agents.funding.main [--week N] [--output PATH] [--dry-run] [--persist]
    python -m apps.agents.funding.main --week 7 --persist
"""

import logging

from apps.agents.base.cli import run_agent_cli
from apps.agents.funding.agent import FundingAgent

logger = logging.getLogger(__name__)


def _funding_post_run(agent, result, args, session):
    """FUNDING-specific post-processing: persist funding rounds."""
    from apps.agents.funding.db_writer import persist_all_events

    scored_events = getattr(agent, "_scored_events", [])
    if scored_events:
        events_with_confidence = [
            (scored.event, scored.confidence.composite) for scored in scored_events
        ]
        stats = persist_all_events(session, events_with_confidence)
        logger.info("Persisted funding rounds: %s", stats)


def main() -> None:
    run_agent_cli(
        agent_class=FundingAgent,
        description="FUNDING — Sinal.lab Investment Tracking Agent",
        default_output_dir="apps/agents/funding/output",
        slug_fn=lambda agent, args: f"funding-semanal-{args.week}",
        filename_fn=lambda agent, args: f"funding-week-{args.week}.md",
        post_run_fn=_funding_post_run,
    )


if __name__ == "__main__":
    main()
