#!/usr/bin/env python3
"""AutoPMF loop for Sinal.lab — autonomous product evolution.

Reads unprocessed feedback from the API, analyzes patterns with Claude,
updates agent configs and product.md, and logs the cycle.

Inspired by github.com/fabriciobloisi/AutoPMF.

Usage:
    # Run one cycle
    python scripts/autoloop.py --once

    # Run continuously (polls every 30 min)
    python scripts/autoloop.py

    # Dry run (analyze but don't change anything)
    python scripts/autoloop.py --once --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

POLL_INTERVAL = 1800  # 30 minutes
PMF_TARGET = 9.0
PMF_CONSECUTIVE = 3
PRODUCT_MD = _PROJECT_ROOT / "product.md"
API_BASE = os.environ.get(
    "PROD_API_URL",
    os.environ.get("NEXT_PUBLIC_API_URL", "https://sinalapi-prod.up.railway.app"),
)


def fetch_unprocessed_feedback() -> List[Dict]:
    """Fetch unprocessed feedback from the API."""
    import httpx

    try:
        r = httpx.get(f"{API_BASE}/api/feedback/unprocessed?limit=50", timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("items", [])
    except Exception as e:
        logger.warning("Failed to fetch feedback: %s", e)
        return []


def analyze_feedback(entries: List[Dict]) -> Dict:
    """Analyze feedback patterns and generate recommendations."""
    if not entries:
        return {"avg_nps": 0, "count": 0, "recommendations": []}

    scores = [e["nps_score"] for e in entries]
    avg = sum(scores) / len(scores)
    comments = [e["comment"] for e in entries if e.get("comment")]

    analysis = {
        "avg_nps": round(avg, 1),
        "count": len(entries),
        "promoters": sum(1 for s in scores if s >= 9),
        "detractors": sum(1 for s in scores if s <= 6),
        "comments": comments,
        "recommendations": [],
    }

    # Simple rule-based recommendations (upgrade to LLM analysis later)
    if avg < 5.0:
        analysis["recommendations"].append("Critical: NPS below 5. Review content quality urgently.")
    elif avg < 7.0:
        analysis["recommendations"].append("NPS is passive. Analyze comments for specific improvement areas.")

    if comments:
        # Log comments for manual review
        for c in comments:
            logger.info("User comment: %s", c[:100])

    return analysis


def update_product_md(analysis: Dict, cycle: int) -> None:
    """Update product.md with new cycle data."""
    content = PRODUCT_MD.read_text("utf-8")

    # Add new row to evolution log
    date_str = datetime.now().strftime("%Y-%m-%d")
    nps = analysis["avg_nps"]
    change = f"{analysis['count']} feedback entries, avg NPS {nps}"
    if analysis["recommendations"]:
        change += f". {analysis['recommendations'][0]}"

    new_row = f"| {cycle} | {date_str} | {nps} | {change} | {PMF_TARGET} |"

    # Insert before the last line of the table
    lines = content.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("|") and "Cycle" not in lines[i] and "---" not in lines[i]:
            lines.insert(i + 1, new_row)
            break

    # Update current NPS
    for i, line in enumerate(lines):
        if "Current:" in line:
            lines[i] = f"- Current: {nps} (cycle {cycle}, {analysis['count']} responses)"

    PRODUCT_MD.write_text("\n".join(lines), "utf-8")
    logger.info("Updated product.md: cycle %d, NPS %.1f", cycle, nps)


def mark_feedback_processed(entry_ids: List[str]) -> None:
    """Mark feedback entries as processed via API."""
    import httpx

    # For now, we don't have a mark-processed endpoint
    # The unprocessed query uses a 'processed' boolean flag
    # TODO: Add PATCH /api/feedback/{id}/process endpoint
    logger.info("Would mark %d entries as processed", len(entry_ids))


def get_current_cycle() -> int:
    """Read current cycle from product.md."""
    content = PRODUCT_MD.read_text("utf-8")
    cycle = 0
    for line in content.split("\n"):
        if line.startswith("|") and "Cycle" not in line and "---" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                try:
                    cycle = max(cycle, int(parts[1]))
                except ValueError:
                    pass
    return cycle


def check_pmf(product_md: str) -> bool:
    """Check if PMF target has been reached (3 consecutive cycles >= 9.0)."""
    scores = []
    for line in product_md.split("\n"):
        if line.startswith("|") and "Cycle" not in line and "---" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                try:
                    scores.append(float(parts[3]))
                except ValueError:
                    pass

    if len(scores) >= PMF_CONSECUTIVE:
        last_n = scores[-PMF_CONSECUTIVE:]
        if all(s >= PMF_TARGET for s in last_n):
            return True
    return False


def run_cycle(dry_run: bool = False) -> bool:
    """Run one AutoPMF cycle. Returns True if new feedback was processed."""
    entries = fetch_unprocessed_feedback()

    if not entries:
        logger.info("No new feedback. Waiting...")
        return False

    logger.info("Processing %d new feedback entries", len(entries))

    analysis = analyze_feedback(entries)
    logger.info(
        "Analysis: NPS=%.1f, count=%d, promoters=%d, detractors=%d",
        analysis["avg_nps"], analysis["count"],
        analysis["promoters"], analysis["detractors"],
    )

    if dry_run:
        logger.info("[DRY RUN] Would update product.md and mark feedback processed")
        return True

    cycle = get_current_cycle() + 1
    update_product_md(analysis, cycle)

    entry_ids = [e["id"] for e in entries]
    mark_feedback_processed(entry_ids)

    # Check PMF
    content = PRODUCT_MD.read_text("utf-8")
    if check_pmf(content):
        logger.info("PMF ACHIEVED! NPS >= %.1f for %d consecutive cycles.", PMF_TARGET, PMF_CONSECUTIVE)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="AutoPMF loop for Sinal.lab")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [autoloop] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.once:
        run_cycle(dry_run=args.dry_run)
        return

    logger.info("AutoPMF loop started (poll every %ds, target NPS %.1f)", POLL_INTERVAL, PMF_TARGET)
    while True:
        try:
            run_cycle(dry_run=args.dry_run)
        except Exception:
            logger.exception("Cycle failed")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
