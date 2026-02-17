"""CLI entry point for the CODIGO agent.

Usage:
    python -m apps.agents.codigo.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.codigo.main --week 8 --persist
"""

from apps.agents.base.cli import run_agent_cli
from apps.agents.codigo.agent import CodigoAgent


def main() -> None:
    run_agent_cli(
        agent_class=CodigoAgent,
        description="CODIGO — Sinal.lab Developer Ecosystem Intelligence Agent",
        default_output_dir="apps/agents/codigo/output",
        slug_fn=lambda agent, args: f"codigo-week-{args.week}",
        filename_fn=lambda agent, args: f"codigo-week-{args.week}.md",
    )


if __name__ == "__main__":
    main()
