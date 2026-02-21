"""CLI entry point for the SINTESE agent.

Usage:
    python -m apps.agents.sintese.main [--edition N] [--output PATH] [--dry-run]
    python -m apps.agents.sintese.main --edition 3 --persist --send
"""

import logging

from apps.agents.base.cli import run_agent_cli
from apps.agents.sintese.agent import SinteseAgent
from apps.agents.sintese.newsletter import (
    markdown_to_html,
    send_broadcast,
    wrap_in_email_template,
)

logger = logging.getLogger(__name__)


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
    )


if __name__ == "__main__":
    main()
