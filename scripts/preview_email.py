#!/usr/bin/env python3
"""Preview branded emails in the browser.

Generates HTML from the unified brand template and opens it in the
default browser. Useful for visual QA of email changes.

Usage:
    python scripts/preview_email.py welcome
    python scripts/preview_email.py welcome --name "Maria"
    python scripts/preview_email.py newsletter --edition 8
    python scripts/preview_email.py newsletter --edition 8 --week 8
"""

import argparse
import logging
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.services.email import _build_welcome_html
from apps.api.services.email_template import build_brand_html
from apps.agents.sintese.newsletter import markdown_to_html, wrap_in_email_template

logger = logging.getLogger(__name__)


def preview_welcome(name: Optional[str] = None) -> str:
    """Generate welcome email HTML for preview."""
    subject = "Bem-vindo ao Sinal \u2014 intelig\u00eancia tech LATAM"
    inner_html = _build_welcome_html(name)
    return build_brand_html(inner_html, subject)


def preview_newsletter(edition: int, week: Optional[int] = None) -> str:
    """Generate newsletter email HTML for preview.

    Looks for composed newsletter output file first, falls back to
    a sample newsletter if no output exists.
    """
    from datetime import datetime

    if week is None:
        week = datetime.now().isocalendar()[1]

    # Try to load existing composed newsletter
    html_path = (
        PROJECT_ROOT / "output" / "newsletters"
        / f"sinal-semanal-{edition}-week-{week}.html"
    )
    if html_path.exists():
        logger.info("Loading existing newsletter: %s", html_path.name)
        return html_path.read_text(encoding="utf-8")

    # Fall back to composing from agent outputs
    try:
        from scripts.publish_newsletter import compose_newsletter, load_agent_output
        from scripts.run_agents import AGENTS

        outputs = {}
        for agent_name, cfg in AGENTS.items():
            period = edition if cfg["period_arg"] == "edition" else week
            filename = cfg["filename_pattern"].format(period=period)
            filepath = PROJECT_ROOT / cfg["output_dir"] / filename
            result = load_agent_output(filepath)
            if result is not None:
                outputs[agent_name] = result

        if outputs:
            newsletter_md = compose_newsletter(edition, outputs)
            html_body = markdown_to_html(newsletter_md)
            subject = f"Sinal Semanal #{edition}"
            return wrap_in_email_template(html_body, subject)
    except Exception as exc:
        logger.warning("Could not compose from agent outputs: %s", exc)

    # Final fallback: sample content
    sample_md = f"""# Sinal Semanal #{edition}

Esta \u00e9 uma pr\u00e9via da newsletter. Nenhum conte\u00fado de agente encontrado
para edi\u00e7\u00e3o {edition} / semana {week}.

## Tend\u00eancias da Semana

- **AI Agents** continuam dominando o ecossistema
- **Infraestrutura cloud** na Am\u00e9rica Latina cresce 40%

## Investimentos

> $5.8M S\u00e9rie A \u2014 BemAgro (agritech, S\u00e3o Paulo)

---

*Sinal.lab \u2014 Intelig\u00eancia aberta para quem constr\u00f3i.*
"""
    html_body = markdown_to_html(sample_md)
    subject = f"Sinal Semanal #{edition}"
    return wrap_in_email_template(html_body, subject)


def open_in_browser(html: str, label: str) -> None:
    """Write HTML to a temp file and open in the default browser."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".html",
        prefix=f"sinal-{label}-",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(html)
        filepath = f.name

    webbrowser.open(f"file://{filepath}")
    logger.info("Opened %s in browser: %s", label, filepath)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview Sinal branded emails in the browser",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shared arguments added to parent parser (before subcommand)
    parser.add_argument(
        "--no-open", action="store_true",
        help="Generate HTML but don't open in browser (print path instead)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose logging",
    )

    # welcome subcommand
    welcome_parser = subparsers.add_parser("welcome", help="Preview welcome email")
    welcome_parser.add_argument(
        "--name", type=str, default=None,
        help="Recipient name for the greeting",
    )

    # newsletter subcommand
    newsletter_parser = subparsers.add_parser("newsletter", help="Preview newsletter email")
    newsletter_parser.add_argument(
        "--edition", type=int, required=True,
        help="Newsletter edition number",
    )
    newsletter_parser.add_argument(
        "--week", type=int, default=None,
        help="ISO week number (defaults to current week)",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [preview] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.command == "welcome":
        html = preview_welcome(args.name)
        label = "welcome"
    elif args.command == "newsletter":
        html = preview_newsletter(args.edition, args.week)
        label = f"newsletter-{args.edition}"
    else:
        parser.error(f"Unknown command: {args.command}")
        return

    if args.no_open:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".html",
            prefix=f"sinal-{label}-",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(html)
            print(f.name)
    else:
        open_in_browser(html, label)


if __name__ == "__main__":
    main()
