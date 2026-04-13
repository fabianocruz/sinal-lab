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

from apps.agents.sintese.email_renderer import AgentCard, ArticleHighlight, FeatureHighlight, IntelligenceHighlight, extract_agent_summary
from apps.agents.sintese.newsletter import (
    build_newsletter_email,
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

# Display names and colors for agent cards in the email.
AGENT_DISPLAY_NAMES: Dict[str, str] = {
    "radar": "RADAR",
    "codigo": "CÓDIGO",
    "funding": "FUNDING",
    "mercado": "MERCADO",
}

AGENT_COLORS: Dict[str, str] = {
    "radar": "#59FFB4",
    "codigo": "#59B4FF",
    "funding": "#FF8A59",
    "mercado": "#C459FF",
}

# Order in which agent sections appear after SINTESE.
SECTION_ORDER = ["radar", "codigo", "funding", "mercado"]

# URL path prefix per agent (matches Next.js app/[agent]/[slug] routes).
AGENT_URL_PREFIX: Dict[str, str] = {
    "radar": "newsletter",
    "codigo": "newsletter",
    "funding": "newsletter",
    "mercado": "newsletter",
}

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


def _resolve_email_subject(
    edition: int,
    frontmatter: dict,
) -> str:
    """Build email subject from frontmatter, DB metadata, or fallback.

    Priority: frontmatter email_subject > DB metadata email_subject
    > frontmatter title > generic.
    """
    # 1. Frontmatter email_subject (best case: .md has YAML frontmatter)
    subj = frontmatter.get("email_subject", "")
    if subj:
        return f"Sinal Semanal #{edition}: {subj}"

    # 2. DB metadata fallback (orchestrator persists email_subject there)
    try:
        from packages.database.session import get_session
        from packages.database.models.content_piece import ContentPiece

        session = get_session()
        piece = session.query(ContentPiece).filter_by(
            slug=f"sinal-semanal-{edition}",
        ).first()
        if piece:
            meta = piece.metadata_ or {}
            db_subj = meta.get("email_subject", "")
            if db_subj:
                session.close()
                return f"Sinal Semanal #{edition}: {db_subj}"
        session.close()
    except Exception:
        logger.debug("Could not read email_subject from DB", exc_info=True)

    # 3. Frontmatter title
    title = frontmatter.get("title", "")
    if title:
        return f"Sinal Semanal #{edition}: {title}"

    # 4. Generic fallback
    return f"Sinal Semanal #{edition}"


# Map Intelligence report URLs to their metadata.
# Add new reports here as they are published.
INTELLIGENCE_REPORTS: Dict[str, dict] = {
    "devtools-market-intelligence-mar-2026": {
        "title": "DevTools Market Intelligence: Top 100 Startups de Developer Tools",
        "summary": "100 startups mapeadas, 13 categorias, $30B+ em capital. O maior levantamento de developer tools do ecossistema global.",
        "author": "Sinal Intelligence",
    },
    "eu-treinei-o-claude-para-escrever-como-eu-em-duas-semanas-ele-ja-rascunhava-80-dos-meus-textos": {
        "title": "Eu treinei o Claude para escrever como eu. Em duas semanas, ele já rascunhava 80% dos meus textos",
        "summary": "Como um fundador técnico treinou o Claude para replicar seu estilo de escrita, os erros no caminho, e o framework que saiu do processo.",
        "author": "Fabiano Cruz",
    },
    "healthtech-ai-mapa-completo-mercado-global": {
        "title": "Healthtech + AI: O Mapa Completo do Mercado Global",
        "summary": "100 empresas analisadas, 16 segmentos, 50+ investidores, rankings e 10 tendencias para 2026-2028.",
        "author": "Sinal Intelligence",
    },
    "embedded-finance-deep-research-2026": {
        "title": "Embedded Finance: Deep Market Intelligence Report 2026",
        "summary": "O mapa completo de embedded finance na America Latina: players, infraestrutura, regulacao e oportunidades para fintechs e plataformas que integram servicos financeiros.",
        "author": "Sinal Intelligence",
    },
}


def _build_intelligence_highlight(url: str) -> Optional[IntelligenceHighlight]:
    """Build IntelligenceHighlight from a report URL.

    Looks up report metadata from INTELLIGENCE_REPORTS registry.
    Returns None if the URL slug is not recognized.
    """
    # Extract slug from URL (last path segment)
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    meta = INTELLIGENCE_REPORTS.get(slug)
    if not meta:
        logger.warning("Unknown Intelligence report slug: %s", slug)
        return None
    return IntelligenceHighlight(
        title=meta["title"],
        summary=meta["summary"],
        site_url=url,
        author=meta.get("author", "Sinal Intelligence"),
    )


# Registry of article highlights per edition
ARTICLE_HIGHLIGHTS: Dict[int, dict] = {
    52: {
        "title": "Eu treinei o Claude para escrever como eu. Em duas semanas, ele já rascunhava 80% dos meus textos",
        "summary": "Como um fundador técnico treinou o Claude para replicar seu estilo de escrita, os erros no caminho, e o framework que saiu do processo.",
        "author": "Fabiano Cruz",
        "site_url": "https://sinal.tech/artigos/eu-treinei-o-claude-para-escrever-como-eu-em-duas-semanas-ele-ja-rascunhava-80-dos-meus-textos",
        "cover_url": "https://q1anrx64yh9vfjwf.public.blob.vercel-storage.com/covers/sintese/ed30-v1-dlbMCZN89f6qr3zjqCxwEb0b3Y5pQx-4lZvQTKwcwr5o1A2sZrJUMKQIho9Ga.png",
    },
    53: {
        "title": "MCP Dev Brasil: 33 servidores MCP open source para APIs brasileiras",
        "summary": "Pagamentos, nota fiscal, logistica, banking, ERPs, messaging e crypto. 379+ tools tipadas para conectar AI agents com a infraestrutura real de negocios no Brasil. MIT license.",
        "author": "CodeSpar",
        "site_url": "https://github.com/codespar/mcp-dev-brasil",
    },
}


# Registry of feature highlights per edition.
# Use this to promote platform features (e.g. Social Signal Intelligence).
FEATURE_HIGHLIGHTS: Dict[int, dict] = {
    53: {
        "title": "Social Signal Intelligence",
        "summary": "866 sinais, 13 clusters, 5 plataformas, 13 temas. Detecte tendencias emergentes em AI, Fintech, HealthTech e mais antes de virarem mainstream.",
        "site_url": "https://sinal.tech/signals",
        "badge": "Novo na plataforma",
        "cta_label": "Explorar sinais",
        "color": "#E8FF59",
    },
}


def _build_feature_highlight(edition: int) -> Optional[FeatureHighlight]:
    """Build FeatureHighlight for the current edition."""
    meta = FEATURE_HIGHLIGHTS.get(edition)
    if not meta:
        return None
    return FeatureHighlight(
        title=meta["title"],
        summary=meta["summary"],
        site_url=meta["site_url"],
        badge=meta.get("badge", "Novo"),
        cta_label=meta.get("cta_label", "Explorar agora"),
        color=meta.get("color", "#E8FF59"),
    )


def _build_article_highlight(edition: int = 52) -> Optional[ArticleHighlight]:
    """Build ArticleHighlight for the current edition."""
    meta = ARTICLE_HIGHLIGHTS.get(edition)
    if not meta:
        return None
    return ArticleHighlight(
        title=meta["title"],
        summary=meta["summary"],
        site_url=meta["site_url"],
        author=meta.get("author", "Sinal"),
        cover_url=meta.get("cover_url"),
    )


def publish_newsletter(
    edition: int,
    week: Optional[int] = None,
    dry_run: bool = False,
    html_path: Optional[str] = None,
    project_root: Optional[Path] = None,
    intelligence_url: Optional[str] = None,
) -> None:
    """Load agent outputs, compose newsletter, and send via Resend Broadcasts.

    Args:
        edition: Newsletter edition number (e.g. 8).
        week: ISO week number for week-based agents. Defaults to current week.
        dry_run: If True, compose and optionally save HTML but don't send.
        html_path: Optional path to save the composed HTML.
        project_root: Override project root (used in tests).
        intelligence_url: URL of an Intelligence report to highlight in the email.
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

    logger.info(
        "Loaded %d agent(s): %s",
        len(outputs),
        ", ".join(outputs.keys()),
    )

    # SINTESE markdown for the hero section
    sintese_body = outputs.get("sintese", {}).get("body", "")
    if not sintese_body:
        sintese_body = f"# Sinal Semanal #{edition}\n"

    # Build agent cards for secondary agents (RADAR, CODIGO, FUNDING, MERCADO)
    agent_cards = []
    for agent_name in SECTION_ORDER:
        if agent_name not in outputs:
            continue
        body = outputs[agent_name]["body"]
        summary = extract_agent_summary(body)
        if not summary:
            continue
        slug = AGENTS[agent_name]["slug_pattern"].format(period=week)
        agent_cards.append(
            AgentCard(
                name=AGENT_DISPLAY_NAMES[agent_name],
                color=AGENT_COLORS[agent_name],
                label=AGENT_SECTIONS[agent_name],
                summary=summary,
                site_url=f"https://sinal.tech/{AGENT_URL_PREFIX[agent_name]}/{slug}",
            )
        )

    edition_url = f"https://sinal.tech/newsletter/sinal-semanal-{edition}"

    # Build subject with DB fallback for orchestrator runs (no frontmatter)
    sintese_fm = outputs.get("sintese", {}).get("frontmatter", {})
    subject = _resolve_email_subject(edition, sintese_fm)

    # Build Intelligence highlight if URL provided
    intelligence = None
    if intelligence_url:
        intelligence = _build_intelligence_highlight(intelligence_url)
        if intelligence:
            logger.info("Intelligence highlight: %s", intelligence.title)

    # Build article highlight for this edition
    article_highlight = _build_article_highlight(edition)
    if article_highlight:
        logger.info("Article highlight: %s", article_highlight.title)

    # Build feature highlight for this edition
    feature_highlight = _build_feature_highlight(edition)
    if feature_highlight:
        logger.info("Feature highlight: %s", feature_highlight.title)

    html_email = build_newsletter_email(
        sintese_body, agent_cards=agent_cards, edition_url=edition_url,
        intelligence=intelligence, article=article_highlight,
        feature=feature_highlight, max_hero_articles=8,
    )

    # Always save HTML to standard output directory
    newsletter_dir = root / NEWSLETTER_OUTPUT_SUBDIR
    newsletter_dir.mkdir(parents=True, exist_ok=True)
    default_filename = f"sinal-semanal-{edition}-week-{week}.html"
    default_path = newsletter_dir / default_filename
    default_path.write_text(html_email, encoding="utf-8")
    logger.info("HTML saved to %s", default_path)

    # Save additional copy if custom path requested
    if html_path:
        Path(html_path).write_text(html_email, encoding="utf-8")
        logger.info("HTML copy saved to %s", html_path)

    # Send via Resend Broadcasts
    if not dry_run:
        print("\n" + "=" * 60)
        print("  BROADCAST REVIEW")
        print("=" * 60)
        print(f"  Subject: {subject}")
        print(f"  Edition: #{edition}")
        print(f"  HTML:    {default_path}")
        print("=" * 60)
        print("  This will send to ALL subscribers. This cannot be undone.")
        print("=" * 60)
        confirm = input("\n  Type ENVIAR to confirm broadcast: ").strip()
        if confirm != "ENVIAR":
            logger.info("Broadcast cancelled by user (typed %r)", confirm)
            return
        ok = send_broadcast(html_email, subject)
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
    project_root: Optional[Path] = None,
) -> None:
    """Compose a newsletter email from agent Markdown files and send to one recipient.

    Uses the same email-safe template as broadcast (table-based HTML with
    inline styles), but sends to a single recipient via transactional email
    instead of Resend Broadcasts.

    Args:
        edition: Newsletter edition number.
        week: ISO week number. Defaults to current week.
        dry_run: If True, save HTML preview but don't send.
        recipient: Email address to send to. Required unless dry_run.
        project_root: Override project root (used in tests).
    """
    from apps.agents.sintese.newsletter import send_via_resend

    root = project_root or PROJECT_ROOT

    if week is None:
        week = datetime.now().isocalendar()[1]

    # Load all available agent outputs (same as broadcast path)
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

    if "sintese" not in outputs:
        logger.error("No SINTESE output found. Cannot compose briefing.")
        return

    sintese_body = outputs["sintese"]["body"]

    # Build agent cards for secondary agents
    agent_cards = []
    for agent_name in SECTION_ORDER:
        if agent_name not in outputs:
            continue
        body = outputs[agent_name]["body"]
        summary = extract_agent_summary(body)
        if not summary:
            continue
        slug = AGENTS[agent_name]["slug_pattern"].format(period=week)
        agent_cards.append(
            AgentCard(
                name=AGENT_DISPLAY_NAMES[agent_name],
                color=AGENT_COLORS[agent_name],
                label=AGENT_SECTIONS[agent_name],
                summary=summary,
                site_url=f"https://sinal.tech/{AGENT_URL_PREFIX[agent_name]}/{slug}",
            )
        )

    edition_url = f"https://sinal.tech/newsletter/sinal-semanal-{edition}"

    # Build subject with DB fallback for orchestrator runs (no frontmatter)
    sintese_fm = outputs["sintese"].get("frontmatter", {})
    subject = _resolve_email_subject(edition, sintese_fm)

    # Build highlights for this edition
    intel_highlight = _build_intelligence_highlight(
        "https://sinal.tech/intelligence/healthtech-ai-mapa-completo-mercado-global"
    )
    article_highlight = _build_article_highlight(edition)
    feature_highlight = _build_feature_highlight(edition)

    # Convert to email-safe HTML (same template as broadcast)
    html_email = build_newsletter_email(
        sintese_body, agent_cards=agent_cards, edition_url=edition_url,
        intelligence=intel_highlight, article=article_highlight,
        feature=feature_highlight, max_hero_articles=8,
    )

    # Save preview HTML
    newsletter_dir = root / NEWSLETTER_OUTPUT_SUBDIR
    newsletter_dir.mkdir(parents=True, exist_ok=True)
    preview_path = newsletter_dir / f"briefing-{edition}-preview.html"
    preview_path.write_text(html_email, encoding="utf-8")
    logger.info("Preview saved to %s", preview_path)

    if dry_run:
        logger.info("Dry run -- skipping send")
        return

    if not recipient:
        logger.error("--recipient is required for non-dry-run sends.")
        return

    ok = send_via_resend(html_email, subject, recipient)
    if ok:
        logger.info("Briefing email sent to %s", recipient)
    else:
        logger.warning("Failed to send briefing email to %s", recipient)


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
    broadcast_parser.add_argument(
        "--intelligence", type=str, default=None,
        help="URL of an Intelligence report to highlight in the email",
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
            intelligence_url=args.intelligence,
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
