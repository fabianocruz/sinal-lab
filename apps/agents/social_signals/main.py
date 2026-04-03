"""CLI entry point for the Social Signals Intelligence agent.

Usage:
    python -m apps.agents.social_signals.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.social_signals.main --week 14 --persist
    python -m apps.agents.social_signals.main --week 14 --dry-run --verbose
"""

from apps.agents.base.cli import run_agent_cli
from apps.agents.social_signals.agent import SocialSignalsAgent


def main() -> None:
    run_agent_cli(
        agent_class=SocialSignalsAgent,
        description="SOCIAL_SIGNALS — Sinal.lab Social Signal Intelligence Agent",
        default_output_dir="apps/agents/social_signals/output",
        slug_fn=lambda agent, args: f"social-signals-week-{args.week}",
        filename_fn=lambda agent, args: f"social-signals-week-{args.week}.md",
    )


if __name__ == "__main__":
    main()
