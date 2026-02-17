"""CLI entry point for MERCADO agent.

Usage:
    python -m apps.agents.mercado.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.mercado.main --week 8 --persist
"""

import logging

from apps.agents.base.cli import run_agent_cli
from apps.agents.mercado.agent import MercadoAgent

logger = logging.getLogger(__name__)


def _mercado_post_run(agent, result, args, session):
    """MERCADO-specific post-processing: persist company profiles.

    Uses agent._scores (ScoredCompanyProfile list) from the completed run,
    avoiding the previous bug of re-running agent.score(agent.process(agent.collect())).
    """
    from apps.agents.mercado.db_writer import persist_all_profiles

    scored_profiles = getattr(agent, "_scores", [])
    if scored_profiles:
        profiles_with_confidence = [
            (scored.profile, scored.composite_score)
            for scored in scored_profiles
        ]
        stats = persist_all_profiles(session, profiles_with_confidence)
        logger.info("Persisted company profiles: %s", stats)


def main() -> None:
    run_agent_cli(
        agent_class=MercadoAgent,
        description="MERCADO — Sinal.lab LATAM Startup Mapping Agent",
        default_output_dir="apps/agents/mercado/output",
        slug_fn=lambda agent, args: f"mercado-week-{args.week}",
        filename_fn=lambda agent, args: f"mercado-week-{args.week}.md",
        post_run_fn=_mercado_post_run,
    )


if __name__ == "__main__":
    main()
