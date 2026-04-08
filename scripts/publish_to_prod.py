#!/usr/bin/env python3
"""Publish agent outputs to production database atomically.

Reads local .md outputs, strips YAML frontmatter, extracts metadata,
and syncs to the production database in one operation. Preserves
hero_image and other metadata that should not be overwritten.

Usage:
    # Publish all week 15 + edition 53
    python scripts/publish_to_prod.py --edition 53 --week 15

    # Dry run
    python scripts/publish_to_prod.py --edition 53 --week 15 --dry-run

    # Specific agents only
    python scripts/publish_to_prod.py --edition 53 --week 15 --agents sintese,radar
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

PROD_DB_URL = "postgresql://postgres:TIJEisKHZxvdLkfnfCDjVXPCXqQSusdp@trolley.proxy.rlwy.net:25062/railway"

# Agent output file mapping
AGENT_FILES = {
    "sintese": {
        "slug_pattern": "sinal-semanal-{edition}",
        "file_pattern": "apps/agents/sintese/output/sinal-semanal-{edition}.md",
        "period": "edition",
    },
    "radar": {
        "slug_pattern": "radar-week-{week}",
        "file_pattern": "apps/agents/radar/output/radar-week-{week}.md",
        "period": "week",
    },
    "codigo": {
        "slug_pattern": "codigo-week-{week}",
        "file_pattern": "apps/agents/codigo/output/codigo-week-{week}.md",
        "period": "week",
    },
    "funding": {
        "slug_pattern": "funding-semanal-{week}",
        "file_pattern": "apps/agents/funding/output/funding-week-{week}.md",
        "period": "week",
    },
    "mercado": {
        "slug_pattern": "mercado-week-{week}",
        "file_pattern": "apps/agents/mercado/output/mercado-week-{week}.md",
        "period": "week",
    },
}


def parse_md_file(path: Path) -> Dict:
    """Parse a Markdown file, separating frontmatter from body.

    Returns dict with 'frontmatter' (dict) and 'body' (str, no frontmatter).
    """
    content = path.read_text("utf-8").strip()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return {"frontmatter": fm, "body": body}

    return {"frontmatter": {}, "body": content}


def publish_agent(
    engine,
    agent_name: str,
    config: Dict,
    edition: int,
    week: int,
    dry_run: bool = False,
) -> bool:
    """Publish a single agent output to production.

    Returns True if successful, False if skipped/failed.
    """
    period = edition if config["period"] == "edition" else week
    slug = config["slug_pattern"].format(edition=edition, week=week)
    file_path = _PROJECT_ROOT / config["file_pattern"].format(edition=edition, week=week)

    if not file_path.exists():
        logger.warning("[%s] File not found: %s", agent_name, file_path)
        return False

    parsed = parse_md_file(file_path)
    fm = parsed["frontmatter"]
    body = parsed["body"]

    title = fm.get("title", slug)
    summary = fm.get("summary", "")
    email_subject = fm.get("email_subject", "")

    if dry_run:
        logger.info(
            "[DRY] %s: title='%s' | %d chars | slug=%s",
            agent_name, title[:50], len(body), slug,
        )
        return True

    now = datetime.now(timezone.utc)

    with engine.connect() as conn:
        # Get current metadata to preserve hero_image
        row = conn.execute(
            text("SELECT metadata FROM content_pieces WHERE slug = :slug"),
            {"slug": slug},
        ).fetchone()

        meta = {}
        if row and row[0]:
            meta = row[0] if isinstance(row[0], dict) else json.loads(row[0])

        # Update metadata fields without clobbering hero_image
        if email_subject:
            meta["email_subject"] = email_subject

        # Clean Nuvini/EFEX from metadata if present
        meta_str = json.dumps(meta)
        if "Nuvini" in meta_str or "EFEX" in meta_str:
            for key in list(meta.keys()):
                if key == "hero_image":
                    continue
                val = meta[key]
                if isinstance(val, list):
                    meta[key] = [
                        i for i in val
                        if "Nuvini" not in json.dumps(i) and "EFEX" not in json.dumps(i)
                    ]

        if row:
            # Update existing
            conn.execute(
                text("""
                    UPDATE content_pieces
                    SET title = :title, summary = :summary, body_md = :body,
                        metadata = :meta, review_status = 'published',
                        published_at = :now
                    WHERE slug = :slug
                """),
                {
                    "title": title,
                    "summary": summary,
                    "body": body,
                    "meta": json.dumps(meta),
                    "now": now,
                    "slug": slug,
                },
            )
            logger.info("[%s] Updated: %s (%d chars)", agent_name, slug, len(body))
        else:
            logger.warning("[%s] Slug %s not found in prod DB, skipping", agent_name, slug)
            return False

        conn.commit()

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish agent outputs to production")
    parser.add_argument("--edition", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--agents", type=str, default=None, help="Comma-separated agent names")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [publish] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    engine = create_engine(PROD_DB_URL)

    agents = args.agents.split(",") if args.agents else list(AGENT_FILES.keys())
    success = 0
    total = 0

    for agent_name in agents:
        if agent_name not in AGENT_FILES:
            logger.warning("Unknown agent: %s", agent_name)
            continue
        total += 1
        if publish_agent(engine, agent_name, AGENT_FILES[agent_name], args.edition, args.week, args.dry_run):
            success += 1

    logger.info("Published %d/%d agents to production%s", success, total, " (dry run)" if args.dry_run else "")


if __name__ == "__main__":
    main()
