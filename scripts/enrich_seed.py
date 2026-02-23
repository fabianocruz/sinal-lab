#!/usr/bin/env python3
"""Enrich seed_data.json with better titles and additional SINTESE/FUNDING entries.

Reads the existing seed data, generates hook-style titles for every entry,
creates SINTESE and FUNDING entries for weeks that lack them, and writes
the enriched data back.

Usage:
    python scripts/enrich_seed.py                 # enrich in-place
    python scripts/enrich_seed.py --dry-run       # preview without writing
    python scripts/enrich_seed.py --output /tmp/enriched.json
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SEED_PATH = Path(__file__).resolve().parent / "seed_data.json"

# ---------------------------------------------------------------------------
# Hook-style title pools — each agent has a set of varied angles.
# Placeholders: {week}, {total}, {city1}, {city2}, {sector1}, {sector2},
# {company1}, {company2}, {item1}, {item2}, {count}
# ---------------------------------------------------------------------------

MERCADO_HOOKS = [
    "Buenos Aires lidera mapeamento com {city1_count} startups na semana",
    "DevTools domina: {sector1_count} startups no setor mais quente da LATAM",
    "São Paulo fora do top 3 — a distribuição geográfica surpreende",
    "{city1}, {city2} e {city3}: as capitais da inovação na semana",
    "Fintech em baixa com apenas {fintech_count} startups — o que mudou?",
    "{company1} e {company2}: os destaques entre {total} startups",
    "Cybersecurity e CleanTech ganham espaço no ecossistema LATAM",
    "{total} startups em 5 cidades revelam o mapa real da inovação",
    "Edtech supera Fintech: {edtech_count} startups contra {fintech_count}",
    "Mexico City e Rio disputam 2ª posição no mapeamento semanal",
    "De Buenos Aires a Bogotá: onde a próxima unicórnio pode nascer",
    "{company1}: open source e DevTools direto de São Paulo",
    "Bogotá firma posição com {bogota_count} startups mapeadas",
    "O ecossistema que ninguém acompanha: {total} startups reveladas",
    "A geografia inesperada: {city1} tem mais startups que São Paulo",
    "{sector1} e {sector2}: os setores que definem a semana",
    "{total} startups, 5 países — o raio-x completo da LATAM",
    "Rio de Janeiro marca presença: {rio_count} startups na semana",
    "CleanTech na LATAM: ainda nicho, mas com sinais de aceleração",
    "Por que {city1} é a nova referência para startups tech?",
    "{company1}, {company3} e o pipeline de inovação latino-americano",
    "DevTools e Edtech lideram — Fintech surpreende com queda",
    "O mapeamento revela: inovação se descentraliza na LATAM",
    "{total} organizações e {sector_count} setores: o ecossistema cresce",
    "Da Poli USP ao GitHub: onde nasce a inovação brasileira",
    "5 cidades, {total} startups: o censo tech semanal da LATAM",
    "Infraestrutura dev lidera descobertas na América Latina",
    "{company2}: cybersecurity brasileira ganha maturidade",
    "Open source como motor: as startups mais ativas no GitHub",
    "O ranking das cidades: quem lidera a corrida tech na LATAM",
]

RADAR_HOOKS = [
    "{item1}: a ferramenta que chamou atenção na semana",
    "{item1} e {item2}: as tendências que não param de crescer",
    "IA & Machine Learning dominam {count} sinais analisados",
    "{item1} entre {count} sinais — o que o mercado está dizendo",
    "Open source e AI Agents: os temas mais quentes da semana",
    "De {count} sinais a 3 tendências: o filtro da semana",
    "{item1}: por que desenvolvedores estão prestando atenção",
    "Ferramentas dev e IA: os dois eixos da semana em {count} sinais",
    "{item2} e a evolução dos agentes autônomos",
    "Startups & Ecossistema: o que {count} sinais revelam",
    "{item1} e o futuro do teste automatizado com IA",
    "O radar capturou {count} sinais — 3 merecem atenção",
    "Machine Learning em produção: as ferramentas que estão ganhando tração",
    "{item1}: a startup que conecta IA e social media",
    "De HN ao GitHub: {count} sinais sobre o que vem por aí",
    "AI Agents ganham tração: {item1} lidera as conversas",
    "Desenvolvimento & Open Source: as tendências de infraestrutura",
    "{count} sinais de {sources} fontes: o resumo técnico da semana",
    "Quando IA encontra dev tools: as integrações que importam",
    "{item1} sinaliza nova geração de ferramentas autônomas",
    "O que {count} sinais tech dizem sobre os próximos 6 meses",
    "IA e automação: as 3 tendências que definirão Q2 2026",
    "Ferramentas low-code/no-code ganham inteligência artificial",
    "De pesquisa a produto: os papers que viraram ferramentas",
    "{item2}: análise social com IA para agentes inteligentes",
    "O mapa de tendências: IA lidera entre {count} sinais",
]

CODIGO_HOOKS = [
    "{item1}: o repo que merece sua atenção esta semana",
    "{item1} e {item2}: as ferramentas dev do momento",
    "{count} sinais dev analisados — os destaques da semana",
    "Chrome Extension com IA: a integração que surpreendeu",
    "{item1}: automação open-source ganha nova dimensão",
    "De {item1} a {item2}: a diversidade do open source LATAM",
    "{item1} e a nova onda de ferramentas para desenvolvedores",
    "{count} sinais dev: o que a comunidade está construindo",
    "Automação, segurança e IA — os 3 eixos do código esta semana",
    "O GitHub não para: {count} sinais relevantes na semana",
    "{item2}: o framework de segurança que está ganhando tração",
    "Entre repos e artigos: {count} descobertas para devs",
    "{item1}: por que este projeto merece uma estrela no GitHub",
    "IA em extensões de browser: a tendência que acelera",
    "De {item1} a Chrome extensions: infraestrutura dev evolui",
    "{count} sinais, 7 fontes: o resumo para CTOs da semana",
    "Open source LATAM: os repos mais relevantes da semana",
    "{item1} e o ecossistema de automação inteligente",
    "Infra como código e IA: como devs estão otimizando workflows",
    "O que {count} sinais dev dizem sobre DevOps em 2026",
    "Segurança e automação: os repos que merecem atenção",
    "{item2} e a convergência entre IA e desenvolvimento",
    "Chrome, GitHub e IA: os 3 ecosistemas que mais inovam",
    "As ferramentas que devs seniores estão adotando em 2026",
    "Do GitHub ao deploy: {count} sinais sobre infra moderna",
    "A próxima geração de dev tools: IA-native e open source",
    "{item1}: como automação redefine workflows de desenvolvimento",
    "Os repos mais ativos: {count} sinais de inovação dev",
    "{item1} e a comunidade open-source que não para",
    "Infraestrutura dev 2026: o mapa completo em {count} sinais",
]


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------


def _extract_mercado_data(entry: dict) -> dict:
    """Extract key data points from a MERCADO entry for title generation.

    Uses body text for city/sector distributions (more accurate than
    metadata items which only contain the top 10).
    """
    meta = entry.get("metadata_", {}) or {}
    items = meta.get("items", [])
    body = entry.get("body_md", "")

    # Extract cities from body "### CityName (N startups)" sections
    city_matches = re.findall(r"### (.+?) \((\d+) startups?\)", body)
    cities: Dict[str, int] = {}
    for city_name, count in city_matches:
        cities[city_name] = int(count)

    # Extract sectors from body "- **SectorName**: N startups"
    sector_matches = re.findall(r"\*\*(.+?)\*\*:\s*(\d+)\s*startups?", body)
    sectors: Dict[str, int] = {}
    for sector_name, count in sector_matches:
        if sector_name != "Top Setores":
            sectors[sector_name] = int(count)

    # Fallback to metadata items if body parsing failed
    if not cities:
        for item in items:
            city = item.get("city", "")
            if city:
                cities[city] = cities.get(city, 0) + 1
    if not sectors:
        for item in items:
            sector = item.get("sector", "")
            if sector and sector != "Outros":
                sectors[sector] = sectors.get(sector, 0) + 1

    companies: List[str] = []
    for item in items:
        name = item.get("company_name", "")
        if name and name not in companies:
            companies.append(name)

    sorted_cities = sorted(cities, key=lambda c: cities[c], reverse=True)
    sorted_sectors = sorted(sectors, key=lambda s: sectors[s], reverse=True)

    return {
        "total": meta.get("item_count", 120),
        "city1": sorted_cities[0] if len(sorted_cities) > 0 else "Buenos Aires",
        "city2": sorted_cities[1] if len(sorted_cities) > 1 else "Mexico City",
        "city3": sorted_cities[2] if len(sorted_cities) > 2 else "Rio de Janeiro",
        "city1_count": cities.get(sorted_cities[0], 30) if sorted_cities else 30,
        "city_count": len(cities),
        "sector1": sorted_sectors[0] if len(sorted_sectors) > 0 else "DevTools",
        "sector2": sorted_sectors[1] if len(sorted_sectors) > 1 else "Edtech",
        "sector1_count": sectors.get(sorted_sectors[0], 9) if sorted_sectors else 9,
        "sector2_count": sectors.get(sorted_sectors[1], 6) if len(sorted_sectors) > 1 else 6,
        "sector_count": len(sectors),
        "fintech_count": sectors.get("Fintech", 3),
        "edtech_count": sectors.get("Edtech", 6),
        "bogota_count": cities.get("Bogotá", 21),
        "rio_count": cities.get("Rio de Janeiro", 26),
        "company1": companies[0] if len(companies) > 0 else "Azuki",
        "company2": companies[1] if len(companies) > 1 else "Nova8",
        "company3": companies[2] if len(companies) > 2 else "Poli Júnior",
        "source_count": 36,
    }


def _extract_radar_data(entry: dict) -> dict:
    """Extract key data points from a RADAR entry."""
    meta = entry.get("metadata_", {}) or {}
    items = meta.get("items", [])

    titles = []
    for item in items[:5]:
        t = item.get("title", "")
        if t:
            # Clean HN-style prefixes
            clean = re.sub(r"^(Show HN|Ask HN|Tell HN):\s*", "", t)
            # Extract just the product name (before the dash/colon description)
            product = re.split(r"\s*[–—:]\s*", clean, maxsplit=1)[0].strip()
            if len(product) > 35:
                product = product[:32].rsplit(" ", 1)[0] + "..."
            titles.append(product)

    return {
        "count": meta.get("item_count", 591),
        "sources": meta.get("total_sources", 10),
        "item1": titles[0] if len(titles) > 0 else "AI Agents",
        "item2": titles[1] if len(titles) > 1 else "Open Source Tools",
    }


def _extract_codigo_data(entry: dict) -> dict:
    """Extract key data points from a CODIGO entry."""
    meta = entry.get("metadata_", {}) or {}
    items = meta.get("items", [])

    titles = []
    for item in items[:5]:
        t = item.get("title", "")
        if t:
            # For repo slugs (org/repo), use just the repo name
            if "/" in t and len(t.split("/")) == 2:
                t = t.split("/")[-1]
            if len(t) > 40:
                t = t[:37] + "..."
            titles.append(t)

    return {
        "count": meta.get("item_count", 265),
        "item1": titles[0] if len(titles) > 0 else "OpenPlanter",
        "item2": titles[1] if len(titles) > 1 else "zeroclaw",
    }


def _extract_funding_data(entry: dict) -> dict:
    """Extract key data points from a FUNDING entry."""
    meta = entry.get("metadata_", {}) or {}
    items = meta.get("items", [])

    companies = [i.get("company_name", "") for i in items if i.get("company_name")]
    total_usd = meta.get("funding_total_usd", 0)

    return {
        "count": meta.get("item_count", 2),
        "company1": companies[0] if companies else "EFEX",
        "company2": companies[1] if len(companies) > 1 else "Sendwave",
        "total_usd": total_usd,
    }


# ---------------------------------------------------------------------------
# Title generation
# ---------------------------------------------------------------------------


def generate_title(entry: dict, index: int) -> str:
    """Generate a hook-style title for a seed entry."""
    agent = entry.get("agent_name", "")

    if agent == "mercado":
        data = _extract_mercado_data(entry)
        pool = MERCADO_HOOKS
    elif agent == "radar":
        data = _extract_radar_data(entry)
        pool = RADAR_HOOKS
    elif agent == "codigo":
        data = _extract_codigo_data(entry)
        pool = CODIGO_HOOKS
    elif agent == "funding":
        data = _extract_funding_data(entry)
        companies = [data["company1"]]
        if data["company2"]:
            companies.append(data["company2"])
        if data["count"] and data["count"] > 0:
            return f"{' e '.join(companies)}: {data['count']} rodadas mapeadas na LATAM"
        return f"{companies[0]} levanta rodada — capital flow LATAM"
    elif agent == "sintese":
        # Keep existing SINTESE title or improve slightly
        meta = entry.get("metadata_", {}) or {}
        items = meta.get("items", [])
        if items:
            top_title = items[0].get("title", "")
            if top_title:
                clean = re.sub(r"^(Show HN|Ask HN):\s*", "", top_title)
                if len(clean) > 55:
                    clean = clean[:52] + "..."
                edition = meta.get("edition_number", "")
                if not edition:
                    m = re.search(r"(\d+)", entry.get("slug", ""))
                    edition = m.group(1) if m else ""
                return f"Sinal Semanal #{edition}: {clean}"
        return entry["title"]
    else:
        return entry["title"]

    # Pick a hook from the pool using index to rotate
    hook_template = pool[index % len(pool)]

    try:
        return hook_template.format(**data)
    except (KeyError, IndexError):
        return entry["title"]


# ---------------------------------------------------------------------------
# SINTESE entry generator
# ---------------------------------------------------------------------------

SINTESE_EDITORIAL_HOOKS = [
    "AI Agents, {city1} e {total_startups} startups: a semana em perspectiva",
    "{radar_item} e a revolução silenciosa das ferramentas autônomas",
    "De {city1} a {city2}: o mapa da inovação esta semana",
    "{codigo_item} lidera código aberto enquanto IA transforma dev tools",
    "O ecossistema LATAM em números: {total_startups} startups e {radar_count} sinais",
    "AI redefine o jogo: {radar_item} e mais tendências da semana",
    "DevTools em alta, Fintech em baixa — o que os dados mostram",
    "{total_startups} startups mapeadas e {codigo_count} sinais dev: o resumo",
    "A LATAM que constrói: destaques de 5 agentes em uma edição",
    "IA, open source e capital: os 3 eixos da semana tech",
    "De {radar_item} a {city1}: os sinais que importam",
    "Infraestrutura, tendências e mercado: a curadoria da semana",
    "{city1} lidera startups e {radar_item} lidera tendências",
    "O pulso tech da LATAM: {total_startups} startups e {radar_count} sinais",
    "{codigo_item}, {radar_item} e o que mais chamou atenção",
    "Quando IA encontra América Latina: as descobertas da semana",
    "Buenos Aires, DevTools e AI Agents: o triângulo da inovação",
    "A semana em dados: {total_startups} startups, {radar_count} sinais, 1 tendência",
    "{radar_item} mostra o futuro enquanto LATAM mapeia {total_startups} startups",
    "Open source e IA dominam — o resumo editorial da semana",
    "De código a capital: como {total_startups} startups moldam a LATAM",
    "{codigo_item} e a infraestrutura que sustenta a inovação",
    "Os números da semana: IA, startups e open source em perspectiva",
    "Mapa de inovação: {city1}, {city2} e {city3} lideram",
    "{radar_item}: a tendência que conecta 5 análises da semana",
    "A curadoria completa: de {city1} aos repos mais ativos",
    "Semana tech: {total_startups} descobertas, {codigo_count} sinais, 1 visão",
    "Por dentro do ecossistema: IA, DevTools e a LATAM real",
    "Do mapeamento ao código: o resumo que importa",
    "As 5 lentes da semana: sintese, radar, código, funding e mercado",
]

SINTESE_BODY_TEMPLATE = """# Sinal Semanal #{edition}

*{date} — Curadoria de Clara Medeiros (SINTESE)*

## Destaques da Semana

A semana {week} trouxe **{total_startups} startups** mapeadas no ecossistema LATAM, com **{radar_count} sinais** de tendência e **{codigo_count} sinais dev** analisados. {city1} continua liderando o mapeamento com {city1_count} organizações, seguida por {city2} e {city3}.

### Tendências em Destaque

O RADAR detectou movimentos relevantes em **{radar_topic1}** e **{radar_topic2}**. Entre os sinais mais fortes, **{radar_item1}** chamou atenção pela proposta de {radar_item1_context}.

### Código & Infraestrutura

No campo de desenvolvimento, **{codigo_item1}** e **{codigo_item2}** lideraram as descobertas entre {codigo_count} sinais analisados de 7 fontes. A tendência de {codigo_topic} segue ganhando tração na comunidade dev LATAM.

### Mercado LATAM

O mapeamento revelou {total_startups} organizações em {city_count} cidades, com **{sector1}** ({sector1_count} startups) e **{sector2}** ({sector2_count} startups) como setores mais ativos. {company1} e {company2} se destacaram entre os perfis de maior confiança.

## Metodologia

Esta edição combina dados de {source_count} fontes, processados por 5 agentes especializados. Scores de confiança DQ (Data Quality) e AC (Analytical Confidence) são calculados automaticamente para cada item.

---

*Sinal.lab — Inteligência aberta para quem constrói.*
"""


def _build_sintese_entry(
    week: int,
    edition: int,
    published_at: str,
    week_data: dict,
    index: int,
) -> dict:
    """Build a SINTESE entry for a given week from other agents' data."""
    mercado_data = week_data.get("mercado", {})
    radar_data = week_data.get("radar", {})
    codigo_data = week_data.get("codigo", {})

    # Compile data for title and body
    total_startups = mercado_data.get("total", 120)
    radar_count = radar_data.get("count", 591)
    codigo_count = codigo_data.get("count", 265)
    city1 = mercado_data.get("city1", "Buenos Aires")
    city2 = mercado_data.get("city2", "Mexico City")
    city3 = mercado_data.get("city3", "Rio de Janeiro")
    city1_count = mercado_data.get("city1_count", 30)
    radar_item = radar_data.get("item1", "AI Agents")
    codigo_item = codigo_data.get("item1", "OpenPlanter")

    hook_data = {
        "total_startups": total_startups,
        "radar_count": radar_count,
        "codigo_count": codigo_count,
        "city1": city1,
        "city2": city2,
        "city3": city3,
        "radar_item": radar_item,
        "codigo_item": codigo_item,
    }

    # Generate title
    hook_template = SINTESE_EDITORIAL_HOOKS[index % len(SINTESE_EDITORIAL_HOOKS)]
    try:
        title = hook_template.format(**hook_data)
    except (KeyError, IndexError):
        title = f"Sinal Semanal #{edition}: a semana tech da LATAM"

    # Generate body
    date_str = datetime.fromisoformat(published_at).strftime("%d/%m/%Y")
    body = SINTESE_BODY_TEMPLATE.format(
        edition=edition,
        week=week,
        date=date_str,
        total_startups=total_startups,
        radar_count=radar_count,
        codigo_count=codigo_count,
        city1=city1,
        city2=city2,
        city3=city3,
        city1_count=city1_count,
        city_count=mercado_data.get("city_count", 5),
        radar_topic1=radar_data.get("topic1", "Ferramentas de Desenvolvimento"),
        radar_topic2=radar_data.get("topic2", "IA & Machine Learning"),
        radar_item1=radar_data.get("item1", "AI Agents"),
        radar_item1_context=radar_data.get("item1_context", "automação inteligente"),
        codigo_item1=codigo_data.get("item1", "OpenPlanter"),
        codigo_item2=codigo_data.get("item2", "zeroclaw"),
        codigo_count_val=codigo_count,
        codigo_topic=codigo_data.get("topic", "automação e IA em ferramentas dev"),
        sector1=mercado_data.get("sector1", "DevTools"),
        sector2=mercado_data.get("sector2", "Edtech"),
        sector1_count=mercado_data.get("sector1_count", 9),
        sector2_count=mercado_data.get("sector2_count", 6),
        company1=mercado_data.get("company1", "Azuki"),
        company2=mercado_data.get("company2", "Nova8"),
        source_count=mercado_data.get("source_count", 36),
    )

    # Build metadata
    items = []
    for src_data in [radar_data, codigo_data]:
        for key in ["item1", "item2"]:
            name = src_data.get(key, "")
            if name:
                items.append({
                    "title": name,
                    "url": "",
                    "source_name": "aggregated",
                    "summary": "",
                    "composite_score": 0.75,
                })

    return {
        "slug": f"sinal-semanal-{edition}",
        "title": title,
        "subtitle": None,
        "body_md": body.strip(),
        "summary": f"Edicao #{edition} do Sinal Semanal — {total_startups} startups, {radar_count} sinais e {codigo_count} sinais dev analisados.",
        "content_type": "DATA_REPORT",
        "agent_name": "sintese",
        "agent_run_id": f"sintese-{datetime.now().strftime('%Y%m%d')}-{edition:03d}",
        "confidence_dq": 3.5,
        "confidence_ac": 3.8,
        "sources": [],
        "metadata_": {
            "hero_image": None,
            "featured_video": None,
            "callouts": [],
            "section_labels": {},
            "reading_time_minutes": 5,
            "edition_number": edition,
            "companies_mentioned": [
                mercado_data.get("company1", "Azuki"),
                mercado_data.get("company2", "Nova8"),
            ],
            "topics": ["AI", "LATAM", "startups", "open source"],
            "items": items,
            "item_count": total_startups + radar_count + codigo_count,
            "total_sources": 36,
        },
        "meta_description": f"Sinal Semanal #{edition}: {total_startups} startups mapeadas, {radar_count} sinais de tendência e {codigo_count} sinais dev na LATAM.",
        "published_at": published_at,
        "review_status": "published",
        "author_name": None,
    }


# ---------------------------------------------------------------------------
# FUNDING entry generator
# ---------------------------------------------------------------------------

FUNDING_HOOKS = [
    "EFEX e Sendwave: as rodadas que movimentaram a semana",
    "Logistics tech capta atenção: EFEX fecha rodada Pre-Seed",
    "Duas rodadas, US$600K — o capital flow LATAM na semana",
    "Capital semente: EFEX aposta em logistics para a LATAM",
    "Sendwave e o mercado de remessas: Pre-Seed na semana",
    "Pre-Seed em alta: 2 startups captam na semana",
    "EFEX fecha rodada de US$500K para logistics tech",
    "O mapa do capital: quem investiu na LATAM esta semana",
    "Rodadas Pre-Seed dominam: EFEX e Sendwave na lista",
    "Logistics e Fintech: os setores que atraíram capital",
    "US$600K em 2 rodadas: o funding tracker da semana",
    "Capital para infraestrutura: EFEX e o mercado logístico",
    "Sendwave capta Pre-Seed para pagamentos cross-border",
    "Duas rodadas mapeadas: o que investidores estão buscando",
    "O cenário de funding LATAM: Pre-Seed lidera em volume",
    "EFEX: a aposta em logistics tech que captou US$500K",
    "Capital flow semanal: 2 rodadas e US$600K mapeados",
    "Pre-Seed e infraestrutura: o perfil do investimento LATAM",
    "Quando logistics encontra tech: a rodada da EFEX",
    "Funding LATAM: as duas apostas da semana em early-stage",
    "Startups early-stage captam US$600K: os destaques",
    "EFEX e Sendwave mostram que Pre-Seed segue ativo na LATAM",
    "Capital para quem constrói: 2 rodadas mapeadas na semana",
    "Logistics e pagamentos: onde o capital está fluindo",
    "O tracker de rodadas: US$600K distribuídos em 2 startups",
    "Pre-Seed na LATAM: EFEX e Sendwave abrem a lista",
    "Rodadas da semana: logistics tech e pagamentos digitais",
    "EFEX fecha Pre-Seed — logistics tech esquenta na LATAM",
    "US$500K em logistics e US$100K em payments: a semana de funding",
    "Capital early-stage: as duas rodadas que mapeamos na semana",
]

FUNDING_BODY_TEMPLATE = """# FUNDING Report — Semana {week}/2026

*{date} — Monitorado por Rafael Oliveira (FUNDING)*

## Rodadas da Semana

A semana {week} registrou **{count} rodadas** de investimento no ecossistema LATAM, totalizando **US${total_formatted}** em capital mapeado.

### EFEX

**Rodada:** Pre-Seed · **Valor:** US$500,000
**Fonte:** Crunchbase

EFEX atua em logistics tech, um setor que vem ganhando tração na América Latina com a digitalização de cadeias de suprimento. A rodada Pre-Seed posiciona a empresa para escalar sua solução em mercados onde a logística ainda é um gargalo significativo para e-commerce e B2B.

### Sendwave

**Rodada:** Pre-Seed · **Valor:** US$100,000
**Fonte:** Crunchbase

Sendwave opera no mercado de pagamentos e remessas internacionais, um setor estratégico para a LATAM dado o volume de transações cross-border. A captação Pre-Seed indica interesse contínuo de investidores em fintech de infraestrutura.

## Resumo

| Empresa | Rodada | Valor | Setor |
|---------|--------|-------|-------|
| EFEX | Pre-Seed | US$500K | Logistics |
| Sendwave | Pre-Seed | US$100K | Fintech |

## Metodologia

Rodadas rastreadas via Crunchbase, TechCrunch e fontes primárias. Valores em USD. Confiança: B (fonte única verificada).

---

*Sinal.lab — Inteligência aberta para quem constrói.*
"""


def _build_funding_entry(
    week: int,
    published_at: str,
    index: int,
) -> dict:
    """Build a FUNDING entry for a given week."""
    title = FUNDING_HOOKS[index % len(FUNDING_HOOKS)]
    date_str = datetime.fromisoformat(published_at).strftime("%d/%m/%Y")

    body = FUNDING_BODY_TEMPLATE.format(
        week=week,
        date=date_str,
        count=2,
        total_formatted="600,000",
    )

    return {
        "slug": f"funding-semanal-{week}",
        "title": title,
        "subtitle": None,
        "body_md": body.strip(),
        "summary": f"Semana {week}: 2 rodadas analisadas de 1 fonte.",
        "content_type": "DATA_REPORT",
        "agent_name": "funding",
        "agent_run_id": f"funding-{datetime.now().strftime('%Y%m%d')}-{week:03d}",
        "confidence_dq": 2.5,
        "confidence_ac": 2.8,
        "sources": [
            "https://www.crunchbase.com/organization/efex",
            "https://www.crunchbase.com/organization/sendwave",
        ],
        "metadata_": {
            "items": [
                {
                    "company_name": "EFEX",
                    "company_slug": "efex",
                    "round_type": "Pre-Seed",
                    "amount_usd": 500000,
                    "currency": "USD",
                    "source_url": "https://www.crunchbase.com/organization/efex",
                    "source_name": "crunchbase",
                    "lead_investors": [],
                    "notes": "",
                },
                {
                    "company_name": "Sendwave",
                    "company_slug": "sendwave",
                    "round_type": "Pre-Seed",
                    "amount_usd": 100000,
                    "currency": "USD",
                    "source_url": "https://www.crunchbase.com/organization/sendwave",
                    "source_name": "crunchbase",
                    "lead_investors": [],
                    "notes": "",
                },
            ],
            "item_count": 2,
            "funding_total_usd": 600000,
        },
        "meta_description": f"Semana {week}: 2 rodadas Pre-Seed mapeadas na LATAM — EFEX (US$500K) e Sendwave (US$100K).",
        "published_at": published_at,
        "review_status": "published",
        "author_name": None,
    }


# ---------------------------------------------------------------------------
# Radar data extraction for SINTESE
# ---------------------------------------------------------------------------


def _extract_radar_body_topics(entry: dict) -> dict:
    """Extract topics from RADAR body H2 headers."""
    body = entry.get("body_md", "")
    h2s = re.findall(r"^## (.+)$", body, re.MULTILINE)
    # Filter out "Metodologia" header
    topics = [h for h in h2s if h != "Metodologia"]
    return {
        "topic1": topics[0] if len(topics) > 0 else "Ferramentas de Desenvolvimento",
        "topic2": topics[1] if len(topics) > 1 else "IA & Machine Learning",
    }


# ---------------------------------------------------------------------------
# Main enrichment logic
# ---------------------------------------------------------------------------


def enrich(data: List[dict], dry_run: bool = False) -> List[dict]:
    """Enrich seed data with better titles and additional entries."""
    # Index existing entries by agent and week
    by_agent_week: Dict[str, Dict[int, dict]] = defaultdict(dict)
    existing_slugs = {d["slug"] for d in data}

    for entry in data:
        agent = entry.get("agent_name", "")
        week_match = re.search(r"(?:week-|semanal-)(\d+)", entry["slug"])
        if week_match:
            week = int(week_match.group(1))
            by_agent_week[agent][week] = entry

    # Determine week range from MERCADO entries (consistent 1-30 weeks).
    # Don't include SINTESE/FUNDING — their slugs use edition numbers, not weeks.
    mercado_weeks = set(by_agent_week.get("mercado", {}).keys())
    if not mercado_weeks:
        mercado_weeks = set(by_agent_week.get("codigo", {}).keys())
    min_week = min(mercado_weeks) if mercado_weeks else 1
    max_week = max(mercado_weeks) if mercado_weeks else 30

    # Phase 1: Update titles for existing entries
    agent_counters: Dict[str, int] = defaultdict(int)
    for entry in data:
        agent = entry.get("agent_name", "")
        idx = agent_counters[agent]
        old_title = entry["title"]
        new_title = generate_title(entry, idx)
        if new_title != old_title:
            if dry_run:
                print(f"  [{agent}] {old_title}")
                print(f"       → {new_title}")
                print()
            entry["title"] = new_title
        agent_counters[agent] += 1

    # Phase 2: Generate missing SINTESE entries
    new_entries: List[dict] = []

    # Determine edition range for SINTESE (edition 19 + week offset)
    base_edition = 19  # First edition in the seed
    existing_sintese_weeks = set(by_agent_week.get("sintese", {}).keys())

    # Find SINTESE edition from existing entry
    for entry in data:
        if entry["agent_name"] == "sintese":
            m = re.search(r"(\d+)", entry["slug"])
            if m:
                existing_edition = int(m.group(1))
                # This was generated at week 9 (the real SINTESE)
                existing_week = by_agent_week["sintese"].keys()
                break

    sintese_count = 0
    for week in range(min_week, max_week + 1):
        edition = base_edition + (week - min_week)
        slug = f"sinal-semanal-{edition}"

        if slug in existing_slugs:
            continue

        # Gather data from other agents for this week
        week_agents_data = {}
        if week in by_agent_week.get("mercado", {}):
            week_agents_data["mercado"] = _extract_mercado_data(by_agent_week["mercado"][week])
        if week in by_agent_week.get("radar", {}):
            radar_entry = by_agent_week["radar"][week]
            rd = _extract_radar_data(radar_entry)
            rd.update(_extract_radar_body_topics(radar_entry))
            rd["item1_context"] = "automação inteligente e testes com IA"
            rd["topic"] = rd.get("topic1", "Ferramentas dev")
            week_agents_data["radar"] = rd
        if week in by_agent_week.get("codigo", {}):
            cd = _extract_codigo_data(by_agent_week["codigo"][week])
            cd["topic"] = "automação e IA em ferramentas dev"
            week_agents_data["codigo"] = cd

        # Published_at: use same date as MERCADO for that week
        mercado_entry = by_agent_week.get("mercado", {}).get(week)
        if mercado_entry:
            pub_at = mercado_entry["published_at"]
        else:
            # Fallback: compute from week offset
            base = datetime(2025, 9, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
            pub_at = (base + timedelta(weeks=week - 1)).isoformat()

        new_entry = _build_sintese_entry(week, edition, pub_at, week_agents_data, sintese_count)
        new_entries.append(new_entry)
        existing_slugs.add(slug)
        sintese_count += 1

        if dry_run:
            print(f"  [NEW sintese] {new_entry['title'][:70]}  ({slug})")

    # Phase 3: Generate missing FUNDING entries
    funding_count = 0
    for week in range(min_week, max_week + 1):
        slug = f"funding-semanal-{week}"
        if slug in existing_slugs:
            continue

        # Published_at: same as other agents for this week
        mercado_entry = by_agent_week.get("mercado", {}).get(week)
        if mercado_entry:
            pub_at = mercado_entry["published_at"]
        else:
            base = datetime(2025, 9, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
            pub_at = (base + timedelta(weeks=week - 1)).isoformat()

        new_entry = _build_funding_entry(week, pub_at, funding_count)
        new_entries.append(new_entry)
        existing_slugs.add(slug)
        funding_count += 1

        if dry_run:
            print(f"  [NEW funding] {new_entry['title'][:70]}  ({slug})")

    # Combine and sort by published_at
    all_entries = data + new_entries
    all_entries.sort(key=lambda e: e.get("published_at", ""))

    print(f"\nSummary:")
    print(f"  Original entries: {len(data)}")
    print(f"  New SINTESE entries: {sintese_count}")
    print(f"  New FUNDING entries: {funding_count}")
    print(f"  Total entries: {len(all_entries)}")

    # Show distribution
    from collections import Counter
    dist = Counter(e["agent_name"] for e in all_entries)
    print(f"\n  Distribution:")
    for agent, count in dist.most_common():
        print(f"    {agent}: {count}")

    return all_entries


def main():
    parser = argparse.ArgumentParser(description="Enrich seed data with better titles")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--output", type=str, default=None, help="Output path (default: in-place)")
    args = parser.parse_args()

    if not SEED_PATH.exists():
        print(f"ERROR: seed file not found: {SEED_PATH}")
        return

    with open(SEED_PATH) as f:
        data = json.load(f)
    print(f"Loaded {len(data)} entries from {SEED_PATH.name}")

    enriched = enrich(data, dry_run=args.dry_run)

    if args.dry_run:
        print("\n--- DRY RUN — no files written ---")
        return

    output_path = Path(args.output) if args.output else SEED_PATH
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"\nWritten to {output_path}")


if __name__ == "__main__":
    main()
