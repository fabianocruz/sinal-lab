#!/usr/bin/env python3
"""Unified background collector daemon for Sinal.lab.

Runs multiple collection jobs on independent schedules in a single
process. Designed to run as a Railway service (always-on).

Jobs:
  - Funding:   every 4h  (Coresignal API + NeoFeed/Bloomberg scrapers)
  - Signals:   every 6h  (Twitter, Bluesky, RSS, Polymarket)
  - Companies: every 12h (Coresignal + GitHub org discovery)
  - Feed:      every 2h  (curate collected signals into feed items)

Usage:
    # Run all collectors (production)
    python scripts/collect_all.py

    # Run specific jobs only
    python scripts/collect_all.py --jobs funding,signals

    # Single cycle (no loop)
    python scripts/collect_all.py --once

    # Dry run
    python scripts/collect_all.py --once --dry-run
"""

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

logger = logging.getLogger("collector")


# ---------------------------------------------------------------------------
# Job registry
# ---------------------------------------------------------------------------

class Job:
    """A scheduled collection job."""

    def __init__(
        self,
        name: str,
        interval_seconds: int,
        run_fn: Callable[[], None],
        description: str = "",
    ):
        self.name = name
        self.interval = interval_seconds
        self.run_fn = run_fn
        self.description = description
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0

    @property
    def due(self) -> bool:
        if self.last_run is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_run).total_seconds()
        return elapsed >= self.interval

    def execute(self, dry_run: bool = False) -> None:
        logger.info("=== [%s] Starting %s ===", self.name, self.description)
        start = time.monotonic()
        try:
            if dry_run:
                logger.info("[%s] Dry run, skipping execution", self.name)
            else:
                self.run_fn()
            self.run_count += 1
            elapsed = time.monotonic() - start
            logger.info("[%s] Completed in %.1fs (run #%d)", self.name, elapsed, self.run_count)
        except Exception:
            self.error_count += 1
            logger.error("[%s] FAILED (error #%d):\n%s", self.name, self.error_count, traceback.format_exc())
        self.last_run = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Job implementations
# ---------------------------------------------------------------------------

def run_funding_scrapers() -> None:
    """Collect funding events from free scrapers only (NeoFeed, Bloomberg, RSS)."""
    from scripts.collect_funding import collect_from_neofeed, collect_from_bloomberg, persist_events
    events = collect_from_neofeed() + collect_from_bloomberg()
    if events:
        inserted, skipped = persist_events(events)
        logger.info("Funding scrapers: %d inserted, %d skipped", inserted, skipped)


def run_signals() -> None:
    """Collect social signals (Twitter, Bluesky, RSS)."""
    run_agent_subprocess("social_signals", week=_current_week(), persist=True)


def run_feed() -> None:
    """Curate collected signals into feed items."""
    run_agent_subprocess("feed_curator", week=_current_week(), persist=True)


def _current_week() -> int:
    return datetime.now(timezone.utc).isocalendar()[1]


# ---------------------------------------------------------------------------
# Agent subprocess runner (shared with run_agents.py)
# ---------------------------------------------------------------------------

def _ensure_run_agent_subprocess():
    """Ensure run_agent_subprocess is importable, add fallback if not."""
    try:
        from scripts.run_agents import AGENTS
        return True
    except ImportError:
        return False


# Fallback: run agent via subprocess if import doesn't work
import subprocess

def run_agent_subprocess(agent_name: str, week: int, persist: bool = True) -> None:
    """Run an agent via subprocess."""
    cmd = [
        sys.executable, str(_PROJECT_ROOT / "scripts" / "run_agents.py"),
        agent_name,
        "--week", str(week),
    ]
    if persist:
        cmd.append("--persist")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(_PROJECT_ROOT)

    logger.info("Running: %s", " ".join(cmd))
    # Timeout 1800s (30min): social_signals collects from 45 sources sync (~6min)
    # and persists with similarity search against thousands of historical signals
    # (slow until pgvector extension is enabled). 600s was too tight in prod.
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)

    if result.returncode != 0:
        logger.error("Agent %s failed (exit %d): %s", agent_name, result.returncode, result.stderr[-500:] if result.stderr else "")
        raise RuntimeError(f"Agent {agent_name} failed with exit code {result.returncode}")

    logger.info("Agent %s completed successfully", agent_name)


# ---------------------------------------------------------------------------
# Job definitions
# ---------------------------------------------------------------------------

JOBS: Dict[str, Job] = {
    "funding_scrapers": Job(
        name="FUNDING_SCRAPE",
        interval_seconds=4 * 3600,  # 4 hours (free scrapers)
        run_fn=run_funding_scrapers,
        description="Funding scrapers (NeoFeed, Bloomberg, RSS)",
    ),
    "signals": Job(
        name="SIGNALS",
        interval_seconds=6 * 3600,  # 6 hours
        run_fn=run_signals,
        description="Social signals (Twitter, Bluesky, RSS)",
    ),
    "feed": Job(
        name="FEED",
        interval_seconds=2 * 3600,  # 2 hours
        run_fn=run_feed,
        description="Feed curation",
    ),
}


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_once(jobs: List[Job], dry_run: bool = False) -> None:
    """Run all jobs once."""
    for job in jobs:
        job.execute(dry_run=dry_run)


def run_loop(jobs: List[Job], dry_run: bool = False) -> None:
    """Run jobs in a continuous loop based on their schedules."""
    logger.info(
        "Starting collector daemon with %d jobs: %s",
        len(jobs),
        ", ".join(f"{j.name} (every {j.interval // 3600}h)" for j in jobs),
    )

    # Run all jobs immediately on startup
    for job in jobs:
        job.execute(dry_run=dry_run)

    # Then loop, checking every 60 seconds if any job is due
    while True:
        time.sleep(60)

        for job in jobs:
            if job.due:
                job.execute(dry_run=dry_run)

        # Log status every hour + write health file for monitoring
        now = datetime.now(timezone.utc)
        if now.minute == 0 and now.second < 60:
            total_errors = 0
            for job in jobs:
                next_run = ""
                if job.last_run:
                    remaining = job.interval - (now - job.last_run).total_seconds()
                    next_run = f"next in {int(remaining // 60)}m"
                logger.info(
                    "[status] %s: runs=%d, errors=%d, %s",
                    job.name, job.run_count, job.error_count, next_run,
                )
                total_errors += job.error_count

            # Alert if error rate is high
            total_runs = sum(j.run_count for j in jobs)
            if total_runs > 0 and total_errors / max(total_runs, 1) > 0.5:
                logger.error(
                    "[ALERT] High error rate: %d errors / %d runs (%.0f%%). "
                    "Check job configurations and API keys.",
                    total_errors, total_runs, total_errors / total_runs * 100,
                )

            # Write health file (Railway health check reads this)
            health = {
                "status": "healthy" if total_errors < total_runs else "degraded",
                "uptime_hours": (now - jobs[0].last_run).total_seconds() / 3600 if jobs[0].last_run else 0,
                "total_runs": total_runs,
                "total_errors": total_errors,
                "timestamp": now.isoformat(),
            }
            try:
                Path("/tmp/collector_health.json").write_text(
                    __import__("json").dumps(health)
                )
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified background collector daemon")
    parser.add_argument("--once", action="store_true", help="Run all jobs once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--jobs", type=str, default=None, help="Comma-separated job names (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Select jobs
    if args.jobs:
        job_names = [j.strip() for j in args.jobs.split(",")]
        selected = [JOBS[n] for n in job_names if n in JOBS]
        unknown = [n for n in job_names if n not in JOBS]
        if unknown:
            logger.warning("Unknown jobs: %s (available: %s)", unknown, list(JOBS.keys()))
    else:
        selected = list(JOBS.values())

    if not selected:
        logger.error("No jobs selected")
        return

    if args.once:
        run_once(selected, dry_run=args.dry_run)
    else:
        run_loop(selected, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
