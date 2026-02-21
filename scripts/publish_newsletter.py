#!/usr/bin/env python3
"""Unified newsletter publisher for Sinal.lab.

Reads Markdown outputs from all 5 agents, composes a single newsletter,
converts to HTML, and sends via Resend Broadcasts.

Usage (file-based broadcast):
    python scripts/publish_newsletter.py broadcast --edition 8 --week 8
    python scripts/publish_newsletter.py broadcast --edition 8 --week 8 --dry-run

Usage (DB-based briefing email):
    python scripts/publish_newsletter.py briefing --edition 48 --week 8 --recipient fabianoc@gmail.com
    python scripts/publish_newsletter.py briefing --edition 48 --week 8 --dry-run
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
    send_broadcast,
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

# Default output subdirectory for composed newsletters (relative to project root).
NEWSLETTER_OUTPUT_SUBDIR = Path("output") / "newsletters"


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
    """Load agent outputs, compose newsletter, and send via Resend Broadcasts.

    Args:
        edition: Newsletter edition number (e.g. 8).
        week: ISO week number for week-based agents. Defaults to current week.
        dry_run: If True, compose and optionally save HTML but don't send.
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

    # Always save HTML to standard output directory
    newsletter_dir = root / NEWSLETTER_OUTPUT_SUBDIR
    newsletter_dir.mkdir(parents=True, exist_ok=True)
    default_filename = f"sinal-semanal-{edition}-week-{week}.html"
    default_path = newsletter_dir / default_filename
    default_path.write_text(html_full, encoding="utf-8")
    logger.info("HTML saved to %s", default_path)

    # Save additional copy if custom path requested
    if html_path:
        Path(html_path).write_text(html_full, encoding="utf-8")
        logger.info("HTML copy saved to %s", html_path)

    # Send via Resend Broadcasts
    if not dry_run:
        ok = send_broadcast(html_full, subject)
        if ok:
            logger.info("Newsletter broadcast sent via Resend")
        else:
            logger.warning("Broadcast failed or not configured")
    else:
        logger.info("Dry run — skipping broadcast")


def publish_briefing_email(
    edition: int,
    week: Optional[int] = None,
    dry_run: bool = False,
    recipient: Optional[str] = None,
) -> None:
    """Compose a rich briefing email from DB content and send via Resend.

    Reads published ContentPiece records, extracts structured metadata,
    and builds a BriefingData payload for the branded email template.

    Args:
        edition: Newsletter edition number.
        week: ISO week number. Defaults to current week.
        dry_run: If True, save HTML preview but don't send.
        recipient: Email address for test send. Required unless dry_run.
    """
    from apps.api.deps import get_session_factory
    from apps.api.services.briefing_composer import compose_briefing_data
    from apps.api.services.email import _build_briefing_html, send_newsletter_email

    if week is None:
        week = datetime.now().isocalendar()[1]

    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        data = compose_briefing_data(session, edition, week)
        if not data:
            logger.error("No published SINTESE content found. Cannot compose briefing.")
            return

        logger.info(
            "Composed briefing #%d (week %d): %s",
            edition, week, data["sintese_title"],
        )

        if dry_run:
            html = _build_briefing_html(data)
            newsletter_dir = PROJECT_ROOT / NEWSLETTER_OUTPUT_SUBDIR
            newsletter_dir.mkdir(parents=True, exist_ok=True)
            preview_path = newsletter_dir / f"briefing-{edition}-preview.html"
            preview_path.write_text(html, encoding="utf-8")
            logger.info("Preview saved to %s", preview_path)
            return

        if not recipient:
            logger.error("--recipient is required for non-dry-run sends.")
            return

        ok = send_newsletter_email(recipient, data)
        if ok:
            logger.info("Briefing email sent to %s", recipient)
        else:
            logger.warning("Failed to send briefing email to %s", recipient)
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sinal.lab newsletter publisher — compose and send via Resend",
    )
    subparsers = parser.add_subparsers(dest="command", help="Publishing mode")

    # broadcast — file-based Markdown → Resend Broadcasts (legacy)
    broadcast_parser = subparsers.add_parser(
        "broadcast", help="Compose from agent Markdown files and send via Resend Broadcasts",
    )
    broadcast_parser.add_argument(
        "--edition", type=int, required=True,
        help="Newsletter edition number",
    )
    broadcast_parser.add_argument(
        "--week", type=int, default=None,
        help="ISO week number (defaults to current week)",
    )
    broadcast_parser.add_argument(
        "--html", type=str, default=None,
        help="Save additional HTML copy to this path",
    )
    broadcast_parser.add_argument(
        "--dry-run", action="store_true",
        help="Compose but don't send",
    )

    # briefing — DB-based structured data → Resend transactional email
    briefing_parser = subparsers.add_parser(
        "briefing", help="Compose from DB content and send rich briefing email",
    )
    briefing_parser.add_argument(
        "--edition", type=int, required=True,
        help="Newsletter edition number",
    )
    briefing_parser.add_argument(
        "--week", type=int, default=None,
        help="ISO week number (defaults to current week)",
    )
    briefing_parser.add_argument(
        "--recipient", type=str, default=None,
        help="Email address to send test briefing to",
    )
    briefing_parser.add_argument(
        "--dry-run", action="store_true",
        help="Save HTML preview but don't send",
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

    if args.command == "broadcast":
        publish_newsletter(
            edition=args.edition,
            week=args.week,
            dry_run=args.dry_run,
            html_path=args.html,
        )
    elif args.command == "briefing":
        publish_briefing_email(
            edition=args.edition,
            week=args.week,
            dry_run=args.dry_run,
            recipient=args.recipient,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
