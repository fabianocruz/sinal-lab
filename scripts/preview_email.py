#!/usr/bin/env python3
"""Preview branded emails in the browser.

Generates HTML from the unified brand template and opens it in the
default browser. Useful for visual QA of email changes.

Usage:
    python scripts/preview_email.py welcome
    python scripts/preview_email.py welcome --name "Maria"
    python scripts/preview_email.py newsletter --edition 8
    python scripts/preview_email.py newsletter --edition 8 --week 8
    python scripts/preview_email.py briefing
    python scripts/preview_email.py briefing --minimal
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

from apps.api.services.email import _build_briefing_html, _build_welcome_html
from apps.api.services.email_template import build_brand_html
from apps.agents.sintese.newsletter import markdown_to_html, wrap_in_email_template

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sample data for briefing preview
# ---------------------------------------------------------------------------

_SAMPLE_MINIMAL_BRIEFING_DATA = {
    "edition_number": 47,
    "week_number": 6,
    "date_range": "3\u201310 Fev 2026",
    "preview_text": "O paradoxo do modelo gratuito, 14 rodadas mapeadas e Rust em fintechs BR.",
    "opening_headline": "Tr\u00eas coisas que importam esta semana",
    "opening_body": "A semana foi barulhenta em IA, com implica\u00e7\u00f5es diretas para quem constr\u00f3i na Am\u00e9rica Latina.",
    "sintese_title": "O paradoxo do modelo gratuito",
    "sintese_paragraphs": [
        "A semana trouxe um paradoxo revelador no mercado de IA.",
        "Este \u00e9 o novo mapa do poder em IA.",
    ],
    "sintese_dq": "4.2/5",
    "sintese_sources": 12,
    "radar_title": "3 padr\u00f5es emergentes desta semana",
    "radar_trends": [
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Vertical AI agents em compliance",
            "context": "4 startups lan\u00e7aram produtos similares.",
        },
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Migra\u00e7\u00e3o para Rust em fintechs",
            "context": "3 vagas abertas.",
        },
        {
            "arrow": "\u2193",
            "arrow_color": "#FF8A59",
            "title": "Interesse de VCs em crypto fintech",
            "context": "Deal flow caiu 60%.",
        },
    ],
    "radar_dq": "3.8/5",
    "radar_sources": 8,
    "codigo_title": "O repo que cresceu 400% em stars",
    "codigo_body": "CrewAI atingiu 50k stars esta semana.",
    "codigo_url": "https://sinal.tech/codigo/crewai-50k",
    "funding_count": 14,
    "funding_total": "287M",
    "funding_score": "4.5/5",
    "funding_deals": [
        {"stage": "Serie B", "description": "Clip (MEX) \u00b7 $50M \u00b7 SoftBank"},
        {"stage": "Serie A", "description": "Pomelo (ARG) \u00b7 $18M \u00b7 Kaszek"},
        {"stage": "Seed", "description": "Axon (BRA) \u00b7 $2.8M \u00b7 Canary"},
    ],
    "funding_remaining": 11,
    "funding_url": "https://sinal.tech/funding/semana-6",
    "mercado_count": 8,
    "mercado_score": "3.9/5",
    "mercado_movements": [
        {"type": "Launch", "description": "Koywe 2.0 (CHL) \u00b7 Crypto Rails"},
        {"type": "M&A", "description": "Dock adquire processadora no Peru"},
        {"type": "Hire", "description": "Ex-CTO Rappi \u2192 VP Eng na Clara (MEX)"},
    ],
    "mercado_remaining": 5,
    "mercado_url": "https://sinal.tech/mercado/semana-6",
}

_SAMPLE_BRIEFING_DATA = {
    "edition_number": 47,
    "week_number": 6,
    "date_range": "3\u201310 Fev 2026",
    "preview_text": "O paradoxo do modelo gratuito, 14 rodadas mapeadas e Rust em fintechs BR.",
    "opening_headline": "Tr\u00eas coisas que importam esta semana",
    "opening_body": (
        "A semana foi barulhenta em IA, com implica\u00e7\u00f5es diretas para quem constr\u00f3i "
        "na Am\u00e9rica Latina. Deepseek derrubou pre\u00e7os, Nubank anunciou sua plataforma de AI "
        "e tr\u00eas fintechs brasileiras abriram vagas para engenheiros Rust. Aqui est\u00e3o os "
        "sinais que realmente importam."
    ),
    # SINTESE section
    "sintese_title": "O paradoxo do modelo gratuito",
    "sintese_image_url": "https://images.sinal.tech/briefing/47/sintese-hero.jpg",
    "sintese_paragraphs": [
        "A semana trouxe um paradoxo revelador no mercado de IA: enquanto modelos gratuitos "
        "proliferam, a concentra\u00e7\u00e3o de poder nos provedores de infraestrutura aumenta. "
        "Deepseek R1 chegou com pre\u00e7os 95% menores que GPT-4, for\u00e7ando OpenAI e Anthropic "
        "a revis\u00e3o de estrat\u00e9gias de precifica\u00e7\u00e3o.",
        "Para founders LATAM, isso significa uma janela: custo de API caindo rapidamente, "
        "mas lock-in de infraestrutura aumentando. Quem controla o fine-tuning e os dados "
        "de treinamento continua sendo o verdadeiro vencedor. Este \u00e9 o novo mapa do poder em IA.",
    ],
    "sintese_dq": "4.2/5",
    "sintese_sources": 12,
    "sintese_source_urls": [
        {"name": "arXiv", "url": "https://arxiv.org/abs/2401.01234"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/2026/02/05/deepseek-pricing"},
        {"name": "Bloomberg", "url": "https://www.bloomberg.com/news/articles/openai-pricing"},
    ],
    "sintese_cta_url": "https://sinal.tech/sintese/paradoxo-modelo-gratuito-47",
    # RADAR section
    "radar_title": "3 padr\u00f5es emergentes desta semana",
    "radar_image_url": "https://images.sinal.tech/briefing/47/radar-trends.jpg",
    "radar_trends": [
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Vertical AI agents em compliance financeiro",
            "context": (
                "4 startups lan\u00e7aram produtos similares na mesma semana: "
                "compliance autom\u00e1tico para mercado de capitais brasileiro."
            ),
            "url": "https://sinal.tech/radar/vertical-ai-compliance-47",
            "source_name": "Sinal Radar",
            "why_it_matters": (
                "CVM come\u00e7a exigir trilhas de auditoria para decis\u00f5es algor\u00edtmicas "
                "em Q3 2026. Janela de 6 meses para capturar mercado."
            ),
            "metrics": {"stars": 4, "forks": 0},
        },
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Migra\u00e7\u00e3o para Rust em fintechs brasileiras",
            "context": (
                "Nubank, Inter e Stone abriram 3 vagas s\u00eanior para Rust "
                "na mesma semana, todas em times de infraestrutura cr\u00edtica."
            ),
            "url": "https://sinal.tech/radar/rust-fintechs-br-47",
            "source_name": "LinkedIn Jobs + GitHub",
            "why_it_matters": (
                "Padr\u00e3o similar ocorreu em fintechs US em 2023, seguido de "
                "migra\u00e7\u00f5es de infra nos 12 meses seguintes."
            ),
            "metrics": {"stars": 3},
        },
        {
            "arrow": "\u2193",
            "arrow_color": "#FF8A59",
            "title": "Interesse de VCs em crypto fintech LATAM",
            "context": (
                "Deal flow caiu 60% no Q1 2026 vs Q1 2025. "
                "Tr\u00eas fundos pausa-ram teses ativas na regi\u00e3o."
            ),
            "url": "https://sinal.tech/radar/vc-crypto-latam-47",
            "source_name": "Crunchbase + entrevistas",
            "why_it_matters": (
                "Founders em crypto fintech devem antecipar runway de 18+ meses "
                "e pivotar narrativa para stablecoins regulamentadas."
            ),
            "metrics": {"stars": 0, "forks": 3},
        },
    ],
    "radar_dq": "3.8/5",
    "radar_sources": 8,
    # CODIGO section
    "codigo_title": "O repo que cresceu 400% em stars",
    "codigo_body": (
        "CrewAI atingiu 50k stars esta semana ap\u00f3s integrar suporte nativo "
        "a modelos da Anthropic. O padr\u00e3o de orquestra\u00e7\u00e3o multi-agente est\u00e1 "
        "se consolidando como alternativa ao LangChain para casos de uso em produ\u00e7\u00e3o."
    ),
    "codigo_url": "https://sinal.tech/codigo/crewai-50k",
    "codigo_repo_url": "https://github.com/crewAIInc/crewAI",
    "codigo_language": "Python",
    "codigo_metrics": {"stars": 50000, "forks": 1200},
    # FUNDING section
    "funding_count": 14,
    "funding_total": "287M",
    "funding_score": "4.5/5",
    "funding_deals": [
        {
            "stage": "Serie B",
            "description": "Clip (MEX) \u00b7 $50M \u00b7 SoftBank",
            "source_url": "https://techcrunch.com/2026/02/06/clip-mexico-series-b",
            "company_url": "https://clip.mx",
            "lead_investors": ["SoftBank Latin America Fund"],
            "why_it_matters": (
                "Maior rodada de pagamentos no M\u00e9xico desde 2023. "
                "Valuation implica multiplica\u00e7\u00e3o 3x desde Serie A."
            ),
        },
        {
            "stage": "Serie A",
            "description": "Pomelo (ARG) \u00b7 $18M \u00b7 Kaszek",
            "source_url": "https://forbes.com.br/2026/02/07/pomelo-serie-a",
            "company_url": "https://pomelo.la",
            "lead_investors": ["Kaszek", "Tiger Global"],
            "why_it_matters": (
                "Infraestrutura de emiss\u00e3o de cart\u00f5es cresce 200% YoY "
                "impulsionada por demand de neobanks regionais."
            ),
        },
        {
            "stage": "Seed",
            "description": "Axon (BRA) \u00b7 $2.8M \u00b7 Canary",
            "source_url": "https://startupi.com.br/axon-seed",
            "company_url": "https://axon.com.br",
            "lead_investors": ["Canary"],
            "why_it_matters": (
                "Primeiro cheque institucional em compliance-as-a-service "
                "focado em open finance brasileiro."
            ),
        },
    ],
    "funding_remaining": 11,
    "funding_url": "https://sinal.tech/funding/semana-6",
    # MERCADO section
    "mercado_count": 8,
    "mercado_score": "3.9/5",
    "mercado_movements": [
        {
            "type": "Launch",
            "description": "Koywe 2.0 (CHL) \u00b7 Crypto Rails para empresas",
            "source_url": "https://www.koywe.com/blog/koywe-2",
            "company_url": "https://koywe.com",
            "sector": "Crypto Infrastructure",
            "why_it_matters": (
                "API de stablecoins agora cobre BRL, CLP e MXN com liquidez "
                "garantida. Pode deslocar TED/PIX para pagamentos B2B internacionais."
            ),
        },
        {
            "type": "M&A",
            "description": "Dock adquire processadora no Peru",
            "source_url": "https://exame.com/negocios/dock-aquisicao-peru",
            "company_url": "https://dock.tech",
            "sector": "Payments Infrastructure",
            "why_it_matters": (
                "Terceira aquisi\u00e7\u00e3o da Dock em 18 meses. "
                "Estrat\u00e9gia de rollup regional em infraestrutura de pagamentos."
            ),
        },
        {
            "type": "Hire",
            "description": "Ex-CTO Rappi \u2192 VP Engineering na Clara (MEX)",
            "source_url": "https://linkedin.com/in/example",
            "company_url": "https://clara.com",
            "sector": "Corporate Cards",
            "why_it_matters": (
                "Sinal de acelera\u00e7\u00e3o de produto. Clara compete diretamente "
                "com Ramp e Brex no segmento enterprise LATAM."
            ),
        },
    ],
    "mercado_remaining": 5,
    "mercado_url": "https://sinal.tech/mercado/semana-6",
}


# ---------------------------------------------------------------------------
# Preview generators
# ---------------------------------------------------------------------------


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


def preview_briefing(rich: bool = True, from_db: bool = False,
                     edition: int = 48, week: int = 9) -> str:
    """Generate briefing email HTML for preview.

    Args:
        rich: If True, use sample data with images and links.
              If False, use minimal data for backward compat testing.
        from_db: If True, compose from actual published content in the DB.
        edition: Edition number (used when from_db=True).
        week: ISO week number (used when from_db=True).
    """
    if from_db:
        from packages.database.config import SessionLocal
        from apps.api.services.briefing_composer import compose_briefing_data

        session = SessionLocal()
        try:
            data = compose_briefing_data(session, edition=edition, week=week)
        finally:
            session.close()

        if not data:
            raise RuntimeError(
                f"No published SINTESE piece found for edition {edition}."
            )
        return _build_briefing_html(data)

    data = _SAMPLE_BRIEFING_DATA if rich else _SAMPLE_MINIMAL_BRIEFING_DATA
    return _build_briefing_html(data)


# ---------------------------------------------------------------------------
# Browser open helper
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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

    # briefing subcommand
    briefing_parser = subparsers.add_parser(
        "briefing",
        help="Preview weekly briefing email (new template)",
    )
    briefing_parser.add_argument(
        "--minimal", action="store_true",
        help="Use minimal sample data (no rich fields) for backward compat testing",
    )
    briefing_parser.add_argument(
        "--from-db", action="store_true",
        help="Compose briefing from actual published content in the database",
    )
    briefing_parser.add_argument(
        "--edition", type=int, default=48,
        help="Edition number (used with --from-db, default: 48)",
    )
    briefing_parser.add_argument(
        "--week", type=int, default=9,
        help="ISO week number (used with --from-db, default: 9)",
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
    elif args.command == "briefing":
        html = preview_briefing(
            rich=not args.minimal,
            from_db=args.from_db,
            edition=args.edition,
            week=args.week,
        )
        label = "briefing"
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
