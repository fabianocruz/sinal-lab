#!/usr/bin/env python3
"""Seed the content_pieces table with the 7 founding newsletters.

Usage:
    python scripts/seed_content.py                  # insert into DB
    python scripts/seed_content.py --dry-run        # preview without writing
    python scripts/seed_content.py --force           # re-insert (delete existing by slug)

Requires DATABASE_URL environment variable or .env file.
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)

NEWSLETTERS = [
    {
        "slug": "briefing-47-paradoxo-modelo-gratuito",
        "title": "O paradoxo do modelo gratuito: quando abundância de IA vira commodity e escassez vira produto",
        "subtitle": "TAMBÉM: 14 rodadas mapeadas · US$287M total · Rust ganha tração em fintechs BR",
        "agent_name": "sintese",
        "content_type": "DATA_REPORT",
        "confidence_dq": 5.0,
        "published_at": "2026-02-10",
        "meta_description": "Análise sobre o paradoxo dos modelos gratuitos de IA e o impacto no ecossistema tech LATAM.",
        "body_md": """Três coisas que importam esta semana: o modelo gratuito da DeepSeek que não é gratuito, a rodada silenciosa que pode redefinir acquiring no México, e por que o melhor engenheiro de ML do Brasil acabou de sair de uma big tech para uma startup de 8 pessoas em Medellín.

A semana foi barulhenta. O ciclo de hype de modelos open-source atingiu um pico previsível, com pelo menos 4 lançamentos competindo por atenção. Filtramos o que realmente muda algo para quem está construindo na região. O resto é ruído.

A avalanche de modelos open-source da última semana não é generosidade — é estratégia de comoditização da camada de inferência. Para quem constrói em LATAM, o sinal é claro: a vantagem competitiva está migrando de "qual modelo uso" para "que dados proprietários alimento".

Os três launches mais relevantes da semana (DeepSeek R2, Qwen 3, Mistral Medium 2) compartilham um padrão: performance comparable ao estado da arte, custo marginal tendendo a zero, e diferenciação cada vez mais sutil. O verdadeiro moat agora é o fine-tuning com dados de domínio — exatamente onde startups LATAM têm vantagem geográfica natural.""",
    },
    {
        "slug": "briefing-46-healthtech-latam",
        "title": "Healthtech LATAM: a vertical silenciosa que cresceu 340%",
        "subtitle": "TAMBÉM: US$1.2B em deals no Q4 · Mapa de talento técnico",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2026-02-03",
        "meta_description": "Como a healthtech se tornou a vertical de maior crescimento na América Latina.",
        "body_md": """Três padrões emergentes esta semana dominaram o fluxo de informação: a aceleração da healthtech no México e Colômbia, a consolidação de fintechs em fase de maturidade, e um sinal fraco mas consistente de migração de engenheiros sênior para startups de impacto.

A healthtech LATAM foi por anos tratada como nicho. Em 2025, ela processou mais de 40 milhões de consultas digitais na região. Os dados desta semana indicam que o ciclo de crescimento não está desacelerando — está mudando de perfil, migrando de telemedicina básica para infraestrutura clínica complexa.

O que é mais relevante para quem está construindo: a adoção institucional. Hospitais públicos no Brasil e no México começaram a contratar startups de diagnóstico por IA como fornecedores primários, não pilotos. Isso muda completamente o perfil de receita dessas empresas.""",
    },
    {
        "slug": "briefing-45-mapa-calor-talento",
        "title": "O mapa de calor do talento técnico na América Latina",
        "subtitle": "TAMBÉM: CrewAI atinge 50k stars · Vagas Rust em fintechs",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2026-01-27",
        "meta_description": "Mapeamento do talento técnico na América Latina e tendências de contratação.",
        "body_md": """O repositório mais relevante da semana não saiu de uma big tech americana. Saiu de uma equipe de cinco pessoas em Buenos Aires. O framework de AI agents CrewAI atingiu 50 mil stars no GitHub, impulsionado por uma contribuição significativa de desenvolvedores brasileiros.

O padrão de multi-agent orchestration está se consolidando como o paradigma dominante para aplicações enterprise — e a comunidade LATAM está na vanguarda da adoção. Isso não é coincidência: os problemas de negócios na região — compliance tributário, integração bancária fragmentada, atendimento em múltiplos idiomas — são exatamente os casos de uso onde agentes especializados têm vantagem.

O sinal mais fraco mas mais interessante da semana: três vagas abertas em fintechs brasileiras exigindo Rust. Há seis meses isso seria incomum. Agora sugere uma mudança estrutural na stack de infraestrutura de pagamentos.""",
    },
    {
        "slug": "briefing-44-embedded-finance-b2b",
        "title": "Por que o embedded finance B2B está prestes a explodir na América Latina",
        "subtitle": "DEEP DIVE: Análise completa com 23 fontes verificáveis",
        "agent_name": "sintese",
        "content_type": "DEEP_DIVE",
        "confidence_dq": 5.0,
        "published_at": "2026-01-20",
        "meta_description": "Deep dive sobre embedded finance B2B na América Latina com 23 fontes verificáveis.",
        "body_md": """Esta é uma edição especial Deep Dive. Dedicamos as últimas três semanas a mapear o embedded finance B2B na América Latina — um mercado que ainda não tem nome consensual, mas que já tem capital, tecnologia e demanda comprovada.

A tese central: o B2B embedded finance vai repetir na América Latina o que o B2C fez entre 2018 e 2022, mas em velocidade maior e com densidade maior de casos de uso. A razão é estrutural: a informalidade do tecido empresarial latino-americano cria um vacuum regulatório que fintechs B2B podem preencher legalmente sem competir diretamente com os grandes bancos.

Mapeamos 47 empresas ativas no espaço, entrevistamos 12 fundadores e analisamos 23 fontes públicas e privadas. O resultado é o mapa mais completo do segmento disponível em português.""",
    },
    {
        "slug": "briefing-43-q4-2025-deals-latam",
        "title": "Q4 2025: US$1.2 bilhão em deals LATAM — quem captou, de quem, e por que",
        "subtitle": "TAMBÉM: Fintech domina mas edtech recupera · Seed rounds +40%",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": None,
        "published_at": "2026-01-13",
        "meta_description": "Análise dos deals LATAM no Q4 2025: US$1.2 bilhão em rodadas mapeadas.",
        "body_md": """O quarto trimestre de 2025 confirmou o que os dados vinham indicando desde outubro: o inverno do capital venture na América Latina terminou. Com US$1.2 bilhão em rodadas mapeadas, o Q4 foi o trimestre mais aquecido desde Q2 2022.

Os números por vertical contam uma história interessante. Fintech continua dominando — 41% do capital total — mas a composição mudou. As rodadas de growth estão sumindo. O que está crescendo são os seeds tardios (US$3-8M) e as Series A focadas em rentabilidade. O capital está indo para empresas que têm unit economics comprovados, não para crescimento a qualquer custo.

O dado mais relevante: seed rounds cresceram 40% em número (não em valor). Mais bets menores, com mais disciplina. Isso é saudável para o ecossistema.""",
    },
    {
        "slug": "briefing-42-novo-mapa-fintechs-latam",
        "title": "O novo mapa das fintechs LATAM: quem sobreviveu, quem pivotou, quem sumiu",
        "subtitle": "TAMBÉM: 3 M&As silenciosos · Nova onda de BaaS no México",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2026-01-06",
        "meta_description": "Mapeamento das fintechs LATAM: quem sobreviveu ao inverno de 2023-2024.",
        "body_md": """Começamos 2026 com um exercício de mapeamento: o que restou do boom de fintechs LATAM de 2020-2022? A resposta é mais nuançada do que o pessimismo do mercado sugere.

Das 340 fintechs que mapeamos em 2022, 187 ainda estão operacionais. Dessas, 43 pivotaram significativamente o modelo de negócios. E 12 passaram por aquisições silenciosas — deals que nunca foram anunciados publicamente mas que confirmamos por registros corporativos e movimentações de equipe no LinkedIn.

O padrão dos sobreviventes é consistente: focaram em um vertical estreito, priorizaram rentabilidade sobre crescimento entre 2023 e 2024, e construíram defensibilidade regulatória. A empresa que tentou ser banco, wallet, crédito e investimento ao mesmo tempo geralmente não está mais aqui.""",
    },
    {
        "slug": "briefing-especial-retrospectiva-2025",
        "title": "Retrospectiva 2025: os 10 sinais que definiram o ano do ecossistema tech LATAM",
        "subtitle": "ESPECIAL: Edição de fim de ano com análise dos 5 agentes",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-12-30",
        "meta_description": "Retrospectiva 2025: os 10 sinais mais relevantes do ecossistema tech LATAM.",
        "body_md": """2025 foi o ano em que o ecossistema tech latino-americano parou de se definir por comparação com o Vale do Silício e começou a ter identidade própria. Este é o nosso relatório de fim de ano: os 10 sinais que, em retrospecto, foram os mais preditivos do que aconteceu.

Sinal 1: O colapso do modelo "crescimento primeiro" chegou atrasado na LATAM, mas chegou com mais violência. As empresas que não ajustaram o modelo entre 2022 e 2023 não sobreviveram até 2025.

Sinal 2: A infraestrutura financeira aberta (Open Finance no Brasil, PLD-FT na Colômbia) criou uma janela de oportunidade que as fintechs nativas digitais aproveitaram melhor que os incumbentes.

Sinal 3: A concentração de talento técnico sênior em três cidades (São Paulo, Cidade do México, Buenos Aires) começou a se dispersar. Medellín, Bogotá e Montevidéu absorveram engenheiros que antes não considerariam se mudar.""",
    },
]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for dry-run and force modes."""
    parser = argparse.ArgumentParser(description="Seed content_pieces with founding newsletters")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force", action="store_true", help="Re-insert existing slugs")
    return parser.parse_args()


def seed(session, newsletters: list[dict], *, force: bool = False) -> int:
    """Insert newsletters into content_pieces, skipping existing slugs.

    For each newsletter:
    1. Check if slug already exists in the database
    2. If --force, delete existing row before re-inserting
    3. Otherwise skip duplicates to make the script idempotent
    4. Insert with review_status="published" so they appear on the frontend
    """
    inserted = 0
    skipped = 0

    for item in newsletters:
        slug = item["slug"]

        # Step 1: Check for existing slug (idempotent by default)
        existing = session.execute(
            text("SELECT id FROM content_pieces WHERE slug = :slug"),
            {"slug": slug},
        ).fetchone()

        if existing:
            if force:
                # --force: delete and re-insert to update content
                session.execute(
                    text("DELETE FROM content_pieces WHERE slug = :slug"),
                    {"slug": slug},
                )
                print(f"  DELETED existing: {slug}")
            else:
                print(f"  SKIP (exists): {slug}")
                skipped += 1
                continue

        # Step 2: Parse date and insert with all required fields
        published_at = datetime.strptime(item["published_at"], "%Y-%m-%d").replace(
            hour=6, tzinfo=timezone.utc
        )

        session.execute(
            text("""
                INSERT INTO content_pieces (
                    id, title, slug, subtitle, body_md, summary,
                    content_type, agent_name, confidence_dq,
                    review_status, published_at, meta_description
                ) VALUES (
                    :id, :title, :slug, :subtitle, :body_md, :summary,
                    :content_type, :agent_name, :confidence_dq,
                    :review_status, :published_at, :meta_description
                )
            """),
            {
                "id": uuid.uuid4(),
                "title": item["title"],
                "slug": slug,
                "subtitle": item["subtitle"],
                "body_md": item["body_md"],
                "summary": item["subtitle"],
                "content_type": item["content_type"],
                "agent_name": item["agent_name"],
                "confidence_dq": item["confidence_dq"],
                "review_status": "published",
                "published_at": published_at,
                "meta_description": item["meta_description"],
            },
        )
        print(f"  INSERT: {item['title'][:60]}... ({slug})")
        inserted += 1

    # Step 3: Commit all inserts in a single transaction
    session.commit()
    print(f"\nDone: {inserted} inserted, {skipped} skipped.")
    return inserted


def main() -> None:
    """Entry point: connect to DB and seed newsletters.

    Reads DATABASE_URL from environment or .env file.
    Prints host info (without credentials) for confirmation.
    """
    args = parse_args()

    if args.dry_run:
        print("--- DRY RUN (no database writes) ---\n")
        for item in NEWSLETTERS:
            print(f"  {item['agent_name']:10s}  {item['slug']}")
        print(f"\nTotal: {len(NEWSLETTERS)} newsletters")
        return

    # Show DB host (mask credentials) for operator confirmation
    db_display = DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"Connecting to: {db_display}")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        seed(session, NEWSLETTERS, force=args.force)


if __name__ == "__main__":
    main()
