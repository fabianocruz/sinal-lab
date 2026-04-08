"""CLI entry point for the SINTESE agent.

Usage:
    python -m apps.agents.sintese.main [--edition N] [--output PATH] [--dry-run]
    python -m apps.agents.sintese.main --edition 3 --persist --send

When --edition is omitted, the next edition number is auto-detected
from the database (max existing edition + 1).
"""

import logging
import re

from apps.agents.base.cli import run_agent_cli
from apps.agents.sintese.agent import SinteseAgent
from apps.agents.sintese.newsletter import (
    markdown_to_html,
    send_broadcast,
    wrap_in_email_template,
)

logger = logging.getLogger(__name__)


def _next_edition_from_db() -> int:
    """Query the database for the latest SINTESE edition and return the next number.

    Scans all ``sinal-semanal-<N>`` slugs, finds the maximum N, and returns N + 1.
    Falls back to 1 if the database is unreachable or has no SINTESE entries.
    """
    try:
        from packages.database.session import get_session
        from packages.database.models import ContentPiece

        session = get_session()
        try:
            rows = (
                session.query(ContentPiece.slug)
                .filter(
                    ContentPiece.agent_name == "sintese",
                    ContentPiece.slug.like("sinal-semanal-%"),
                )
                .all()
            )
            max_edition = 0
            for (slug,) in rows:
                match = re.search(r"sinal-semanal-(\d+)", slug)
                if match:
                    max_edition = max(max_edition, int(match.group(1)))
            next_ed = max_edition + 1
            logger.info("DB has editions up to %d, next: %d", max_edition, next_ed)
            return next_ed
        finally:
            session.close()
    except Exception as exc:
        logger.warning("Could not auto-detect edition from DB: %s", exc)
        return 1


def _add_sintese_args(parser):
    """Add SINTESE-specific CLI arguments."""
    parser.add_argument(
        "--html", type=str, default=None,
        help="Path to save the newsletter HTML output",
    )
    parser.add_argument(
        "--send", action="store_true",
        help="Send newsletter broadcast via Resend (requires API keys)",
    )


def _sintese_post_run(agent, result, args, session):
    """SINTESE-specific post-processing: HTML generation and newsletter send."""
    # Generate and optionally save HTML
    html_body = markdown_to_html(result.body_md)
    html_full = wrap_in_email_template(html_body, result.title)

    if hasattr(args, "html") and args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(html_full)
        logger.info("HTML saved to %s", args.html)

    # Send newsletter broadcast
    if hasattr(args, "send") and args.send:
        logger.info("Sending newsletter broadcast...")
        edition = getattr(args, "edition", 1)
        subject = f"Sinal Semanal #{edition}"
        ok = send_broadcast(html_full, subject)
        if not ok:
            logger.warning("Broadcast not sent — check RESEND_API_KEY and RESEND_AUDIENCE_ID")


def main() -> None:
    run_agent_cli(
        agent_class=SinteseAgent,
        description="SINTESE — Sinal.lab Newsletter Synthesizer Agent",
        default_output_dir="apps/agents/sintese/output",
        period_arg="edition",
        slug_fn=lambda agent, args: f"sinal-semanal-{args.edition}",
        filename_fn=lambda agent, args: f"sinal-semanal-{args.edition}.md",
        post_run_fn=_sintese_post_run,
        extra_args_fn=_add_sintese_args,
        auto_period_fn=_next_edition_from_db,
    )


if __name__ == "__main__":
    main()
