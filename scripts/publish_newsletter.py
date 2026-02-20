#!/usr/bin/env python3
"""Unified newsletter publisher for Sinal.lab.

Reads Markdown outputs from all 5 agents, composes a single newsletter,
converts to HTML, and publishes as a draft on Beehiiv.

Usage:
    python scripts/publish_newsletter.py --edition 8 --week 8
    python scripts/publish_newsletter.py --edition 8 --week 8 --html output.html --dry-run
    python scripts/publish_newsletter.py --edition 8
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.agents.sintese.newsletter import (
    markdown_to_html,
    send_via_beehiiv,
    wrap_in_email_template,
)
from scripts.run_agents import AGENTS

logger = logging.getLogger(__name__)

# Section headers for each agent in the composed newsletter.
# SINTESE is the lead editorial and gets no extra header.
AGENT_SECTIONS: Dict[str, str] = {
    "radar": "Tendências da Semana",
    "codigo": "Código & Infraestrutura",
    "funding": "Investimentos",
    "mercado": "Ecossistema LATAM",
}

# Order in which agent sections appear after SINTESE.
SECTION_ORDER = ["radar", "codigo", "funding", "mercado"]


def load_agent_output(filepath: Path) -> Optional[dict]:
    """Parse a Markdown file with YAML frontmatter.

    Returns {"frontmatter": dict, "body": str} or None if file doesn't exist.
    """
    if not filepath.exists():
        return None

    content = filepath.read_text(encoding="utf-8").strip()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return {"frontmatter": frontmatter, "body": body}

    # No frontmatter found — treat entire content as body
    return {"frontmatter": {}, "body": content}


def compose_newsletter(edition: int, outputs: Dict[str, dict]) -> str:
    """Compose unified newsletter Markdown from all agent outputs.

    Structure:
    - SINTESE content as lead editorial (full body)
    - Separator
    - RADAR section under "Tendências da Semana"
    - CODIGO section under "Código & Infraestrutura"
    - FUNDING section under "Investimentos"
    - MERCADO section under "Ecossistema LATAM"
    - Footer tagline

    Agents with missing output are silently skipped.
    """
    sections = []

    # SINTESE as lead editorial
    if "sintese" in outputs:
        sections.append(outputs["sintese"]["body"])
    else:
        # Minimal header when SINTESE is missing
        sections.append(f"# Sinal Semanal #{edition}\n")

    # Remaining agent sections
    for agent_name in SECTION_ORDER:
        if agent_name not in outputs:
            continue

        header = AGENT_SECTIONS[agent_name]
        body = outputs[agent_name]["body"]

        sections.append("---")
        sections.append(f"## {header}\n")
        sections.append(body)

    # Footer
    sections.append("---")
    sections.append("*Sinal.lab — Inteligência aberta para quem constrói.*")

    return "\n\n".join(sections)


def publish_newsletter(
    edition: int,
    week: Optional[int] = None,
    dry_run: bool = False,
    html_path: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> None:
    """Load agent outputs, compose newsletter, and publish to Beehiiv.

    Args:
        edition: Newsletter edition number (e.g. 8).
        week: ISO week number for week-based agents. Defaults to current week.
        dry_run: If True, compose and optionally save HTML but don't publish.
        html_path: Optional path to save the composed HTML.
        project_root: Override project root (used in tests).
    """
    root = project_root or PROJECT_ROOT

    if week is None:
        week = datetime.now().isocalendar()[1]

    # Load all available agent outputs
    outputs: Dict[str, dict] = {}
    for agent_name, cfg in AGENTS.items():
        period = edition if cfg["period_arg"] == "edition" else week
        filename = cfg["filename_pattern"].format(period=period)
        filepath = root / cfg["output_dir"] / filename

        result = load_agent_output(filepath)
        if result is not None:
            outputs[agent_name] = result
            logger.info("Loaded %s output: %s", agent_name.upper(), filepath.name)
        else:
            logger.warning("No output found for %s: %s", agent_name.upper(), filepath)

    if not outputs:
        logger.error("No agent outputs found. Nothing to publish.")
        return

    # Compose newsletter
    newsletter_md = compose_newsletter(edition, outputs)
    logger.info(
        "Composed newsletter from %d agent(s): %s",
        len(outputs),
        ", ".join(outputs.keys()),
    )

    # Convert to HTML
    html_body = markdown_to_html(newsletter_md)
    subject = f"Sinal Semanal #{edition}"
    html_full = wrap_in_email_template(html_body, subject)

    # Save HTML if requested
    if html_path:
        Path(html_path).write_text(html_full, encoding="utf-8")
        logger.info("HTML saved to %s", html_path)

    # Publish to Beehiiv
    if not dry_run:
        ok = send_via_beehiiv(html_full, subject)
        if ok:
            logger.info("Newsletter published as draft on Beehiiv")
        else:
            logger.warning("Beehiiv publish failed or not configured")
    else:
        logger.info("Dry run — skipping Beehiiv publish")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sinal.lab newsletter publisher — compose and publish to Beehiiv",
    )
    parser.add_argument(
        "--edition", type=int, required=True,
        help="Newsletter edition number",
    )
    parser.add_argument(
        "--week", type=int, default=None,
        help="ISO week number for week-based agents (defaults to current week)",
    )
    parser.add_argument(
        "--html", type=str, default=None,
        help="Path to save the composed HTML",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compose newsletter but don't publish to Beehiiv",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [publisher] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    publish_newsletter(
        edition=args.edition,
        week=args.week,
        dry_run=args.dry_run,
        html_path=args.html,
    )


if __name__ == "__main__":
    main()
