#!/usr/bin/env python3
"""Railway cron service entry point for Sinal.lab agents.

Thin wrapper over run_agents.py that auto-calculates period values
(ISO week or next edition from DB) and runs in orchestrate mode.

Usage:
    python scripts/run_cron.py           # Daily dispatch (Railway cron mode)
    python scripts/run_cron.py radar     # Run single agent (manual/debug)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=False)

from sqlalchemy import desc

from packages.database.models.content_piece import ContentPiece
from packages.database.session import get_session
from scripts.run_agents import AGENTS, orchestrate_single_agent, setup_logging

logger = logging.getLogger("run_cron")

# isoweekday(): 1=Monday … 7=Sunday
SCHEDULE: dict[int, list[str]] = {
    1: ["codigo", "radar", "sintese", "funding"],  # Monday
    3: ["mercado"],                                  # Wednesday
}


def _get_current_week() -> int:
    """Return current ISO week number."""
    return datetime.now().isocalendar()[1]


def _get_next_edition() -> int:
    """Query DB for latest sintese edition, return +1.

    Parses the edition number from the slug (e.g. 'sinal-semanal-5' -> 6).
    Falls back to current ISO week if DB is unavailable or no editions exist.
    """
    try:
        session = get_session()
        try:
            row = (
                session.query(ContentPiece.slug)
                .filter(ContentPiece.agent_name == "sintese")
                .order_by(desc(ContentPiece.created_at))
                .first()
            )
            if row:
                # slug = "sinal-semanal-5" → extract 5
                last_part = row[0].rsplit("-", 1)[-1]
                if last_part.isdigit():
                    next_ed = int(last_part) + 1
                    logger.info("DB: latest sintese edition=%s, next=%d", row[0], next_ed)
                    return next_ed
        finally:
            session.close()
    except Exception as exc:
        logger.warning("Could not query DB for edition: %s. Falling back to ISO week.", exc)

    fallback = _get_current_week()
    logger.info("Using ISO week %d as edition fallback", fallback)
    return fallback


def _get_period_value(agent_name: str) -> int:
    """Auto-calculate the period value for an agent."""
    cfg = AGENTS[agent_name]
    if cfg["period_arg"] == "edition":
        return _get_next_edition()
    return _get_current_week()


def run_daily() -> int:
    """Dispatch agents based on today's schedule. Returns 0 or 1."""
    today = datetime.now().isoweekday()
    agents = SCHEDULE.get(today, [])

    if not agents:
        logger.info("No agents scheduled for weekday %d. Nothing to do.", today)
        return 0

    logger.info("Daily dispatch: weekday=%d, agents=%s", today, agents)
    failures: list[str] = []

    session = get_session()
    try:
        for agent_name in agents:
            period_value = _get_period_value(agent_name)
            logger.info("Running agent=%s, period=%d", agent_name, period_value)

            exit_code = orchestrate_single_agent(
                agent_name,
                period_value=period_value,
                session=session,
                enable_editorial=True,
                enable_evidence=True,
            )

            if exit_code != 0:
                logger.error("Agent %s failed with exit_code=%d", agent_name, exit_code)
                failures.append(agent_name)
            else:
                logger.info("Agent %s completed successfully", agent_name)
    finally:
        session.close()

    if failures:
        logger.error("Daily dispatch finished with failures: %s", failures)
        return 1

    logger.info("Daily dispatch completed successfully")
    return 0


def _run_single(agent_name: str) -> int:
    """Run a single agent via orchestrator. Returns exit code 0 or 1."""
    if agent_name not in AGENTS:
        logger.error("Unknown agent: %s. Valid: %s", agent_name, list(AGENTS.keys()))
        return 1

    period_value = _get_period_value(agent_name)
    logger.info("Starting cron run: agent=%s, period=%d", agent_name, period_value)

    session = get_session()
    try:
        exit_code = orchestrate_single_agent(
            agent_name,
            period_value=period_value,
            session=session,
            enable_editorial=True,
            enable_evidence=True,
        )
    finally:
        session.close()

    if exit_code == 0:
        logger.info("Cron run completed successfully: agent=%s", agent_name)
    else:
        logger.error("Cron run failed: agent=%s, exit_code=%d", agent_name, exit_code)

    return exit_code


def main() -> int:
    """Entry point: no args → daily dispatch, with arg → single agent."""
    setup_logging(verbose=True)

    if len(sys.argv) < 2:
        return run_daily()

    return _run_single(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
