"""CLI entry point for the RADAR agent.

Usage:
    python -m apps.agents.radar.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.radar.main --week 8 --persist
"""

from apps.agents.base.cli import run_agent_cli
from apps.agents.radar.agent import RadarAgent


def main() -> None:
    run_agent_cli(
        agent_class=RadarAgent,
        description="RADAR — Sinal.lab Trend Intelligence Agent",
        default_output_dir="apps/agents/radar/output",
        slug_fn=lambda agent, args: f"radar-week-{args.week}",
        filename_fn=lambda agent, args: f"radar-week-{args.week}.md",
    )


if __name__ == "__main__":
    main()
