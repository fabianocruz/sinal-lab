#!/usr/bin/env python3
"""Unified agent runner for Sinal.lab.

Runs one or more agents with optional database persistence.

Usage:
    python scripts/run_agents.py sintese --edition 3 --persist
    python scripts/run_agents.py radar --persist
    python scripts/run_agents.py all --persist --dry-run
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

AGENTS = {
    "sintese": {
        "module": "apps.agents.sintese.main",
        "description": "Newsletter synthesis from RSS/Atom feeds",
    },
    "radar": {
        "module": "apps.agents.radar.main",
        "description": "Emerging trend detection (HN, GitHub, arXiv)",
    },
    "codigo": {
        "module": "apps.agents.codigo.main",
        "description": "Developer ecosystem signals (GitHub, npm, PyPI)",
    },
    "funding": {
        "module": "apps.agents.funding.main",
        "description": "Investment tracking (VC announcements, funding rounds)",
    },
    "mercado": {
        "module": "apps.agents.mercado.main",
        "description": "LATAM startup mapping and ecosystem intelligence",
    },
}


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [run_agents] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_agent(name: str, extra_args: list[str], dry_run: bool = False) -> int:
    """Run a single agent as a subprocess."""
    logger = logging.getLogger("run_agents")

    if name not in AGENTS:
        logger.error("Unknown agent: %s. Valid: %s", name, list(AGENTS.keys()))
        return 1

    agent_cfg = AGENTS[name]
    cmd = [sys.executable, "-m", agent_cfg["module"]] + extra_args

    if dry_run:
        cmd.append("--dry-run")

    logger.info("Running %s: %s", name.upper(), " ".join(cmd))
    logger.info("  Description: %s", agent_cfg["description"])

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )

    if result.returncode == 0:
        logger.info("%s completed successfully", name.upper())
    else:
        logger.error("%s failed with exit code %d", name.upper(), result.returncode)

    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sinal.lab unified agent runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available agents:
  sintese   Newsletter synthesis from RSS/Atom feeds
  radar     Emerging trend detection
  codigo    Developer ecosystem signals
  funding   Investment tracking (VC announcements, funding rounds)
  mercado   LATAM startup mapping and ecosystem intelligence
  all       Run all agents sequentially
        """,
    )
    parser.add_argument(
        "agent",
        choices=list(AGENTS.keys()) + ["all"],
        help="Agent to run (or 'all')",
    )
    parser.add_argument(
        "--edition", type=int, default=1,
        help="Edition number (for sintese agent)",
    )
    parser.add_argument(
        "--persist", action="store_true",
        help="Save results to database",
    )
    parser.add_argument(
        "--send", action="store_true",
        help="Send newsletter (sintese only)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without saving or sending",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("run_agents")

    agents_to_run = list(AGENTS.keys()) if args.agent == "all" else [args.agent]
    exit_codes = []

    for name in agents_to_run:
        extra_args = []

        if name == "sintese":
            extra_args.extend(["--edition", str(args.edition)])
            if args.send:
                extra_args.append("--send")

        if args.persist:
            extra_args.append("--persist")

        if args.verbose:
            extra_args.append("--verbose")

        code = run_agent(name, extra_args, dry_run=args.dry_run)
        exit_codes.append(code)

    failed = sum(1 for c in exit_codes if c != 0)
    total = len(exit_codes)

    logger.info("=" * 40)
    logger.info("Results: %d/%d agents succeeded", total - failed, total)

    if failed:
        logger.error("%d agent(s) failed", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
