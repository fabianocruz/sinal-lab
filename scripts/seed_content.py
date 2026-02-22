#!/usr/bin/env python3
"""Seed the content_pieces table with the 30 founding newsletters.

Usage:
    python scripts/seed_content.py                  # insert into DB
    python scripts/seed_content.py --dry-run        # preview without writing
    python scripts/seed_content.py --force           # re-insert (delete existing by slug)

Requires DATABASE_URL environment variable or .env file.
"""

import argparse
import json
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
        "sources": [
            "https://techcrunch.com/2026/02/08/deepseek-r2-open-source-strategy-commoditization",
            "https://restofworld.org/2026/latam-ai-startups-proprietary-data-advantage",
            "https://bloomberg.com/news/articles/2026-02-09/qwen3-mistral-open-source-llm-race",
        ],
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
        "sources": [
            "https://restofworld.org/2026/latam-healthtech-mexico-colombia-growth",
            "https://lavca.org/2026/q4-2025-healthtech-latam-report",
            "https://techcrunch.com/2026/01/31/latam-digital-health-ai-diagnostics-hospitals",
        ],
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
        "sources": [
            "https://github.com/crewAIInc/crewAI",
            "https://techcrunch.com/2026/01/24/crewai-50k-github-stars-latam-developers",
            "https://restofworld.org/2026/rust-fintechs-brazil-infrastructure-shift",
        ],
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
        "sources": [
            "https://lavca.org/2026/embedded-finance-b2b-latam-deep-dive",
            "https://sifted.eu/articles/embedded-finance-latam-b2b-opportunity",
            "https://ft.com/content/latam-b2b-embedded-finance-infrastructure-2026",
        ],
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
        "sources": [
            "https://lavca.org/2026/q4-2025-latam-venture-capital-report",
            "https://pitchbook.com/news/articles/latam-q4-2025-funding-1-2-billion",
            "https://bloomberg.com/news/articles/2026-01-10/latam-startups-q4-2025-venture-capital",
        ],
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
        "sources": [
            "https://lavca.org/2026/latam-fintech-landscape-survivors-2025",
            "https://restofworld.org/2026/latam-fintechs-pivot-acquisition-2025",
            "https://crunchbase.com/organization/latam-fintech-consolidation-2025",
        ],
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
        "sources": [
            "https://lavca.org/2025/year-in-review-latam-tech-ecosystem",
            "https://restofworld.org/2025/latam-tech-2025-retrospective",
            "https://techcrunch.com/2025/12/28/latam-tech-2025-year-review",
        ],
        "body_md": """2025 foi o ano em que o ecossistema tech latino-americano parou de se definir por comparação com o Vale do Silício e começou a ter identidade própria. Este é o nosso relatório de fim de ano: os 10 sinais que, em retrospecto, foram os mais preditivos do que aconteceu.

Sinal 1: O colapso do modelo "crescimento primeiro" chegou atrasado na LATAM, mas chegou com mais violência. As empresas que não ajustaram o modelo entre 2022 e 2023 não sobreviveram até 2025.

Sinal 2: A infraestrutura financeira aberta (Open Finance no Brasil, PLD-FT na Colômbia) criou uma janela de oportunidade que as fintechs nativas digitais aproveitaram melhor que os incumbentes.

Sinal 3: A concentração de talento técnico sênior em três cidades (São Paulo, Cidade do México, Buenos Aires) começou a se dispersar. Medellín, Bogotá e Montevidéu absorveram engenheiros que antes não considerariam se mudar.""",
    },
    # --- Edições 41-29: backlog de ~3 meses (dez/2025 → set/2025) ---
    {
        "slug": "briefing-41-kubernetes-latam-infraestrutura",
        "title": "Kubernetes na LATAM: do hype à infraestrutura real",
        "subtitle": "TAMBÉM: 3 clouds regionais ganham tração · GitOps em fintechs BR",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-12-22",
        "meta_description": "Como Kubernetes passou de buzzword a infraestrutura crítica em startups LATAM.",
        "sources": [
            "https://techcrunch.com/2025/12/19/kubernetes-latam-regional-cloud-providers",
            "https://github.com/argoproj/argo-cd",
            "https://restofworld.org/2025/gitops-brazil-open-finance-compliance",
        ],
        "body_md": """A adoção de Kubernetes na América Latina seguiu um caminho diferente do que os evangelistas previam. Em vez da migração massiva de monolitos para microserviços, o que vimos em 2025 foi algo mais pragmático: empresas adotando Kubernetes como plataforma de deploy, não como arquitetura.

O dado mais relevante da semana: três provedores de cloud regionais — Magalu Cloud (Brasil), KIO Networks (México) e Mercado Libre Cloud (Argentina) — reportaram crescimento de 200% em clusters Kubernetes gerenciados. O padrão é claro: startups LATAM querem a ergonomia do Kubernetes sem a complexidade operacional.

O sinal técnico mais interessante: GitOps está se consolidando como o workflow padrão em fintechs brasileiras reguladas pelo Banco Central. ArgoCD e Flux aparecem em 67% das vagas de SRE/Platform Engineering postadas no último mês. A razão é regulatória — auditoria de deploys é requisito do Open Finance.""",
    },
    {
        "slug": "briefing-40-mapa-ia-generativa-latam",
        "title": "O mapa de IA generativa aplicada na América Latina",
        "subtitle": "TAMBÉM: 23 startups mapeadas · US$89M em rodadas de IA · LLMs em português",
        "agent_name": "sintese",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-12-15",
        "meta_description": "Mapeamento completo de startups de IA generativa aplicada na América Latina.",
        "sources": [
            "https://lavca.org/2025/generative-ai-latam-startups-89m-funding",
            "https://techcrunch.com/2025/12/12/latam-generative-ai-compliance-regtech",
            "https://pitchbook.com/news/articles/latam-ai-generative-startups-2025-mapping",
        ],
        "body_md": """Mapeamos 23 startups na América Latina que estão construindo produtos de IA generativa aplicada — não wrappers de API, mas empresas com diferenciação real em dados, distribuição ou domínio vertical. O resultado é um panorama que surpreende pela maturidade.

O padrão dominante: IA generativa aplicada a problemas de compliance e regulação. Sete das 23 empresas mapeadas atacam alguma variante de "transformar regulação complexa em ação automatizada" — desde compliance tributário no Brasil até KYC na Colômbia. A razão é estrutural: a América Latina tem a regulação mais fragmentada do mundo em desenvolvimento, e LLMs são excepcionalmente bons em navegar ambiguidade regulatória.

As rodadas confirmam a tese: US$89M foram investidos em startups de IA generativa LATAM nos últimos 90 dias. O ticket médio subiu de US$1.2M para US$3.8M, indicando que investidores estão passando de "seed exploratório" para "aposta com convicção".""",
    },
    {
        "slug": "briefing-39-climate-tech-capital-latam",
        "title": "Climate tech LATAM: o capital está chegando — mas para quem?",
        "subtitle": "TAMBÉM: Créditos de carbono tokenizados · Energia solar descentralizada",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-12-08",
        "meta_description": "Análise do fluxo de capital para climate tech na América Latina.",
        "sources": [
            "https://techcrunch.com/2025/12/05/breakthrough-energy-lowercarbon-latam-climate-tech",
            "https://ft.com/content/latam-carbon-credits-amazon-cerrado-investment",
            "https://bloomberg.com/news/articles/2025-12-06/latam-climate-tech-venture-capital-gap",
        ],
        "body_md": """O sinal mais consistente das últimas semanas vem de um setor que historicamente foi ignorado pelo venture capital latino-americano: climate tech. Três fundos globais — Breakthrough Energy, Lowercarbon Capital e Congruent Ventures — abriram operações ou contrataram partners dedicados à região nos últimos 60 dias.

O que mudou não é a urgência climática (essa já existia) mas a viabilidade econômica. Créditos de carbono no mercado voluntário atingiram preços que tornam projetos de conservação na Amazônia e no Cerrado economicamente competitivos com soja e pecuária. Startups como Moss e Carbonext estão na interseção exata entre tech e carbono.

O dado mais interessante: o Brasil concentra 34% de todos os créditos de carbono de natureza emitidos globalmente, mas apenas 3% do capital de venture dedicado a climate tech. Esse gap é a oportunidade — e os fundos que estão chegando sabem disso.""",
    },
    {
        "slug": "briefing-38-novembro-rodadas-series-b",
        "title": "Novembro: 18 rodadas, US$342M e 3 Series B que ninguém esperava",
        "subtitle": "TAMBÉM: Seed médio sobe para US$2.4M · YC aceita recorde de LATAM founders",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-12-01",
        "meta_description": "Análise das 18 rodadas de novembro 2025: US$342M investidos em startups LATAM.",
        "sources": [
            "https://lavca.org/2025/november-2025-latam-funding-342m",
            "https://pitchbook.com/news/articles/latam-november-2025-series-b-rounds",
            "https://techcrunch.com/2025/11/29/yc-winter-batch-14-latam-startups-record",
        ],
        "body_md": """Novembro fechou com 18 rodadas mapeadas totalizando US$342M — o melhor mês desde março de 2022. Mas o número absoluto esconde o que realmente importa: a composição mudou radicalmente.

Três Series B dominaram o mês: uma fintech de crédito para PMEs no México (US$85M), uma healthtech de diagnóstico por IA no Brasil (US$62M) e uma logtech colombiana (US$48M). As três compartilham um perfil: fundadas entre 2019 e 2020, sobreviveram ao inverno com unit economics positivos, e agora estão expandindo com disciplina. Nenhuma queimou capital para crescer — cresceram para merecer capital.

O dado de seed é igualmente relevante: o ticket médio de seed rounds subiu de US$1.6M para US$2.4M. Mais capital por empresa, menos empresas financiadas. Os investidores estão concentrando apostas, não dispersando. YC aceitou 14 startups LATAM no batch de inverno — recorde absoluto.""",
    },
    {
        "slug": "briefing-37-super-apps-falharam-latam",
        "title": "Por que as super apps falharam na América Latina (e o que veio no lugar)",
        "subtitle": "TAMBÉM: Rappi pivota para fintech · Mercado Pago vs Nubank",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-11-24",
        "meta_description": "Análise de por que o modelo de super app não funcionou na América Latina.",
        "sources": [
            "https://restofworld.org/2025/super-app-latam-failure-rappi-nubank",
            "https://techcrunch.com/2025/11/21/mercado-pago-nubank-super-app-latam",
            "https://bloomberg.com/news/articles/2025-11-22/latam-super-app-death-pix-api-ecosystem",
        ],
        "body_md": """A tese do super app latino-americano morreu silenciosamente em 2025. Nenhuma das empresas que tentaram — Rappi, Mercado Libre, Nubank — conseguiu replicar o modelo WeChat/Grab na região. A pergunta relevante agora não é "quem será o super app LATAM?" mas "por que o modelo não funciona aqui?"

A resposta é regulatória e comportamental. Regulatória: cada vertical (pagamentos, transporte, delivery, crédito) tem um regulador diferente, e a arbitragem regulatória que permitiu super apps na Ásia simplesmente não existe na LATAM. Comportamental: o consumidor latino-americano demonstrou preferência por apps especializados com UX superior em cada vertical.

O que emergiu no lugar é mais interessante: um ecossistema de APIs e integrações que permite que apps especializados conversem entre si. O Pix no Brasil é o exemplo mais claro — uma camada de infraestrutura neutra que conecta todos sem que nenhum precise ser o "super app". É a filosofia Unix aplicada a fintech: faça uma coisa bem feita.""",
    },
    {
        "slug": "briefing-36-estado-engenharia-dados-latam",
        "title": "O estado da engenharia de dados na LATAM: ferramentas, salários e gaps",
        "subtitle": "DEEP DIVE: Survey com 340 data engineers em 6 países",
        "agent_name": "codigo",
        "content_type": "DEEP_DIVE",
        "confidence_dq": 4.0,
        "published_at": "2025-11-17",
        "meta_description": "Deep dive sobre engenharia de dados na América Latina com survey de 340 profissionais.",
        "sources": [
            "https://techcrunch.com/2025/11/14/dbt-dagster-prefect-latam-data-engineering-survey",
            "https://restofworld.org/2025/data-engineer-salaries-latam-brazil-mexico-argentina",
            "https://bloomberg.com/news/articles/2025-11-15/data-governance-gap-latam-startups",
        ],
        "body_md": """Conduzimos um survey com 340 data engineers em seis países (Brasil, México, Argentina, Colômbia, Chile e Peru) para mapear o estado real da engenharia de dados na região. Os resultados contradizem várias narrativas populares.

Descoberta 1: dbt é a ferramenta de transformação dominante (72% de adoção), mas Airflow está perdendo terreno para Dagster e Prefect entre equipes menores. A razão é operacional — manter Airflow em produção exige um SRE dedicado que startups em estágio inicial não têm.

Descoberta 2: o salário médio de data engineer sênior no Brasil (US$4.200/mês) está convergindo com o do México (US$3.800/mês), mas a diferença com a Argentina (US$2.100/mês) está aumentando — criando uma arbitragem de talento que empresas remotas estão explorando ativamente.

Descoberta 3: o gap mais crítico não é técnico, é de governança. Apenas 18% dos respondentes reportam ter um data catalog em produção. A maioria opera com "conhecimento tribal" — e isso se torna insustentável acima de 10 pessoas na equipe de dados.""",
    },
    {
        "slug": "briefing-35-edtech-segunda-onda",
        "title": "Edtech 2.0: a segunda onda de educação digital chega com IA e B2B",
        "subtitle": "TAMBÉM: Platzi atinge 5M alunos · Descomplica pivota para enterprise",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-11-10",
        "meta_description": "A segunda onda de edtech na América Latina: IA e modelos B2B.",
        "sources": [
            "https://techcrunch.com/2025/11/07/latam-edtech-second-wave-b2b-ai",
            "https://restofworld.org/2025/platzi-enterprise-descomplica-b2b-pivot",
            "https://sifted.eu/articles/latam-edtech-workforce-reskilling-2025",
        ],
        "body_md": """A edtech LATAM teve uma primeira onda turbulenta: crescimento explosivo durante a pandemia, seguido de retração brutal em 2022-2023. Metade das startups do setor fechou ou pivotou. Mas os dados das últimas semanas mostram algo inesperado — uma segunda onda está emergindo, com perfil completamente diferente.

A Edtech 2.0 tem três características que a distinguem da primeira: é B2B (vende para empresas, não para consumidores), é powered by IA (conteúdo adaptativo gerado por LLMs), e tem unit economics positivo desde o primeiro cliente. Exemplos: Platzi Enterprise cresceu 180% em receita corporativa, e a Descomplica pivotou silenciosamente de B2C para treinamento corporativo em fintechs.

O sinal mais forte: três empresas de edtech B2B LATAM captaram rodadas seed acima de US$3M nas últimas 6 semanas. Todas atacam o mesmo problema — requalificação de força de trabalho para economia digital — com abordagens diferentes mas convergentes.""",
    },
    {
        "slug": "briefing-34-mexico-unicornios-mudanca",
        "title": "México supera Brasil em novos unicórnios pela primeira vez: o que mudou",
        "subtitle": "TAMBÉM: Nearshoring tech acelera · Monterrey como hub de IA",
        "agent_name": "mercado",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-11-03",
        "meta_description": "México ultrapassa Brasil em novos unicórnios tech em 2025.",
        "sources": [
            "https://techcrunch.com/2025/10/30/mexico-unicorns-surpass-brazil-2025",
            "https://bloomberg.com/news/articles/2025-10-31/monterrey-ai-hub-latam-nearshoring",
            "https://restofworld.org/2025/mexico-nearshoring-tech-startup-boom",
        ],
        "body_md": """Pela primeira vez desde que o ecossistema tech LATAM existe como categoria de investimento, o México produziu mais novos unicórnios que o Brasil em um ano calendário. Em 2025: México 4, Brasil 2. O número absoluto é pequeno, mas o sinal direcional é inequívoco.

As razões são estruturais, não conjunturais. O nearshoring — a migração de cadeias produtivas dos EUA da China para o México — criou uma demanda massiva por infraestrutura digital que simplesmente não existia três anos atrás. Cada fábrica nova precisa de ERP, logística, fintech B2B, e compliance automatizado. Startups mexicanas estão na posição certa, no momento certo.

Monterrey emergiu como o hub de IA mais relevante da América Latina em 2025, com 47 startups de IA catalogadas (vs 23 em 2024). A combinação de proximidade com os EUA, talento do Tec de Monterrey, e capital de VCs americanos que veem o México como extensão natural do mercado US está criando um cluster que não existia há dois anos.""",
    },
    {
        "slug": "briefing-33-semana-redefiniu-vc-latam",
        "title": "A semana que redefiniu o venture capital na América Latina",
        "subtitle": "TAMBÉM: SoftBank volta · Novo fundo de US$500M focado em LATAM",
        "agent_name": "sintese",
        "content_type": "ANALYSIS",
        "confidence_dq": 5.0,
        "published_at": "2025-10-27",
        "meta_description": "Como uma semana de anúncios redefiniu o venture capital LATAM.",
        "sources": [
            "https://techcrunch.com/2025/10/24/softbank-500m-latam-fund-kaszek-a16z",
            "https://ft.com/content/softbank-latam-fund-discipline-2025",
            "https://sifted.eu/articles/a16z-latam-first-bet-brazil-fintech",
        ],
        "body_md": """Em cinco dias, três anúncios mudaram o panorama do venture capital na América Latina. SoftBank anunciou um novo fundo de US$500M dedicado à região (metade do Latin America Fund II original, mas com tese radicalmente diferente). Kaszek fechou seu Fund V de US$800M. E a16z fez sua primeira aposta direta na região — uma fintech de crédito em São Paulo.

O que esses três movimentos têm em comum: disciplina. O SoftBank de 2025 não é o SoftBank de 2021. O novo fundo tem tickets menores (US$10-30M vs US$50-100M), exige break-even antes de Series B, e tem um comitê de investimento que inclui operators latino-americanos. É uma admissão implícita de que a estratégia anterior — cheques grandes em empresas pre-revenue — falhou na região.

Para fundadores, o sinal é ambíguo: há mais capital disponível, mas com mais condições. A era do "crescimento a qualquer custo" acabou definitivamente. A era do "crescimento eficiente com métricas reais" começou.""",
    },
    {
        "slug": "briefing-32-mapa-capital-startups-latam",
        "title": "De onde vem o dinheiro: mapeando os 50 investidores mais ativos em LATAM",
        "subtitle": "TAMBÉM: Corporate venture cresce 60% · Family offices entram no jogo",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-10-20",
        "meta_description": "Mapeamento dos 50 investidores mais ativos no ecossistema tech LATAM.",
        "sources": [
            "https://lavca.org/2025/top-50-investors-latam-startups-2025",
            "https://crunchbase.com/organization/kaszek-nxtp-valor-canary-latam-ranking",
            "https://pitchbook.com/news/articles/latam-corporate-vc-family-office-2025",
        ],
        "body_md": """Mapeamos os 50 investidores mais ativos em startups LATAM nos últimos 12 meses por número de deals. O ranking revela uma mudança estrutural: pela primeira vez, investidores regionais dominam os top 10, deslocando fundos americanos que lideravam há três anos.

Kaszek lidera com 34 deals, seguido por NXTP (28), Valor Capital (24) e Canary (22). A surpresa é a ascensão de corporate ventures: Itaú Unibanco Ventures, Mercado Libre Fund e Globo Ventures entraram no top 20 pela primeira vez. Corporate VC cresceu 60% em número de deals — as corporações estão comprando opções no futuro através de investimento em startups.

O dado mais interessante: family offices representam agora 15% dos cheques em seed rounds LATAM (vs 4% em 2022). São famílias de industriais brasileiros e mexicanos que estão diversificando de real estate e agro para tech. O ticket médio é menor (US$200-500K), mas a velocidade de decisão é muito maior que a de VCs tradicionais.""",
    },
    {
        "slug": "briefing-31-open-source-latam-contribuidores",
        "title": "Open source na LATAM: de consumidores a contribuidores",
        "subtitle": "TAMBÉM: Elixir cresce em São Paulo · Terraform LATAM community",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-10-13",
        "meta_description": "Como a América Latina está passando de consumidora a contribuidora de open source.",
        "sources": [
            "https://github.com/trending/developers?since=monthly&spoken_language_code=pt",
            "https://techcrunch.com/2025/10/10/latam-open-source-contributors-github-2025",
            "https://restofworld.org/2025/elixir-terraform-rust-latam-developer-communities",
        ],
        "body_md": """A comunidade open source latino-americana atingiu um ponto de inflexão em 2025. Pela primeira vez, contribuições de desenvolvedores LATAM para projetos top-100 do GitHub representam mais de 5% do total global. Parece pouco, mas em 2020 era 1.2%.

O padrão de contribuição é revelador: desenvolvedores LATAM não estão criando novos frameworks — estão melhorando documentação, escrevendo adapters para casos de uso regionais (compliance brasileiro, integração com Pix, suporte a espanhol), e construindo ferramentas de developer experience. É contribuição pragmática, não acadêmica.

Três comunidades se destacam: Elixir em São Paulo (impulsionada pela adoção massiva de Phoenix LiveView em fintechs), Terraform na Colômbia (driven by cloud migration em empresas tradicionais), e Rust em Buenos Aires (com foco em infraestrutura de pagamentos). O fio condutor é o mesmo: linguagens e ferramentas que resolvem problemas reais de infraestrutura na região.""",
    },
    {
        "slug": "briefing-30-consolidacao-ecommerce-latam",
        "title": "A consolidação silenciosa do e-commerce LATAM: quem está comprando quem",
        "subtitle": "TAMBÉM: Mercado Libre adquire 2 fintechs · Shopify LATAM cresce 140%",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-10-06",
        "meta_description": "Análise da onda de consolidação no e-commerce da América Latina.",
        "sources": [
            "https://techcrunch.com/2025/10/03/mercado-libre-vtex-ecommerce-latam-acquisitions",
            "https://bloomberg.com/news/articles/2025-10-04/ecommerce-latam-consolidation-silent-deals",
            "https://restofworld.org/2025/shopify-latam-140-percent-growth-marketplace",
        ],
        "body_md": """Uma onda de consolidação está varrendo o e-commerce latino-americano, mas acontecendo de forma tão silenciosa que a maioria dos observadores não percebeu. Nos últimos 90 dias, contamos 8 aquisições no setor — nenhuma com press release público. Descobrimos por movimentações no LinkedIn e registros corporativos.

O padrão é claro: empresas maiores estão comprando tecnologia, não mercado. Mercado Libre adquiriu duas fintechs pequenas com infraestrutura de crédito para sellers. VTEX comprou um starter kit de marketplace. Magazine Luiza absorveu uma logtech de last-mile. Nenhuma dessas aquisições foi sobre receita adicional — todas foram sobre capacidades técnicas que seria mais lento construir internamente.

Para startups de e-commerce infrastructure, o sinal é importante: o exit mais provável não é IPO, é aquisição por um incumbente que precisa da sua tecnologia. Isso muda como você deve construir — otimize para integração, não para independência.""",
    },
    {
        "slug": "briefing-29-regulacao-ia-cinco-paises",
        "title": "Regulação de IA na América Latina: 5 países, 5 abordagens, zero consenso",
        "subtitle": "DEEP DIVE: Análise comparativa de marcos regulatórios com 18 fontes",
        "agent_name": "radar",
        "content_type": "DEEP_DIVE",
        "confidence_dq": 4.0,
        "published_at": "2025-09-29",
        "meta_description": "Deep dive comparativo sobre regulação de IA em 5 países da América Latina.",
        "sources": [
            "https://restofworld.org/2025/latam-ai-regulation-five-countries-comparison",
            "https://ft.com/content/brazil-mexico-colombia-chile-argentina-ai-law-2025",
            "https://bloomberg.com/news/articles/2025-09-26/latam-ai-regulation-fragmentation-regtech",
        ],
        "body_md": """A América Latina está regulando inteligência artificial de cinco formas diferentes em cinco países. Brasil, México, Colômbia, Chile e Argentina seguem caminhos divergentes — e essa fragmentação está criando tanto riscos quanto oportunidades para startups de IA na região.

Brasil lidera com o PL 2338/2023, a regulação mais detalhada e prescritiva da região: classificação de risco obrigatória, sandbox regulatório, e uma autoridade dedicada (que ainda não existe). México optou por uma abordagem de soft law — diretrizes voluntárias sem força de lei. Colômbia criou um framework setorial (regulações diferentes para IA em saúde, finanças e governo). Chile apostou em princípios éticos sem mecanismos de enforcement. Argentina simplesmente não tem regulação — e algumas startups de IA estão se incorporando lá exatamente por isso.

Para quem está construindo: a fragmentação regulatória é um moat para startups que conseguem navegar múltiplas jurisdições. RegTech de IA — ferramentas que ajudam empresas a cumprir regulações de IA em diferentes países LATAM — é uma vertical que não existia há 12 meses e que agora tem pelo menos 4 startups financiadas.""",
    },
    # --- Edições 28-19: backlog estendido (set/2025 → jul/2025) ---
    {
        "slug": "briefing-28-infraestrutura-pagamentos-latam",
        "title": "A guerra invisível da infraestrutura de pagamentos na América Latina",
        "subtitle": "TAMBÉM: Pix internacional · SPEI evolui · Transferencias 3.0 na Argentina",
        "agent_name": "sintese",
        "content_type": "DATA_REPORT",
        "confidence_dq": 5.0,
        "published_at": "2025-09-22",
        "meta_description": "Análise da competição entre infraestruturas de pagamento na América Latina.",
        "sources": [
            "https://restofworld.org/2025/pix-spei-transferencias-latam-payment-war",
            "https://bloomberg.com/news/articles/2025-09-19/pix-international-mercosul-2026-announcement",
            "https://techcrunch.com/2025/09/20/latam-payments-infrastructure-api-unification",
        ],
        "body_md": """A batalha mais consequente do ecossistema tech latino-americano não está acontecendo no nível de aplicação — está na camada de infraestrutura de pagamentos. Três sistemas nacionais estão evoluindo em paralelo: Pix no Brasil, SPEI/CoDi no México e Transferencias 3.0 na Argentina.

O Pix completou três anos processando mais de 4 bilhões de transações mensais. O dado mais relevante desta semana: o Banco Central anunciou que o Pix internacional entrará em operação no segundo trimestre de 2026, permitindo transferências instantâneas entre Brasil e países do Mercosul. Isso muda fundamentalmente o cenário para fintechs de remessas.

Para quem está construindo: a interoperabilidade entre sistemas de pagamento nacionais vai criar uma camada de infraestrutura que não existe hoje. Startups que consigam abstrair as diferenças entre Pix, SPEI e Transferencias 3.0 em uma API unificada estão posicionadas para capturar valor desproporcional.""",
    },
    {
        "slug": "briefing-27-devtools-latam-emergem",
        "title": "DevTools made in LATAM: 8 ferramentas que estão ganhando tração global",
        "subtitle": "TAMBÉM: CLI tools em Rust · Observability para edge · DX como diferencial",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-09-15",
        "meta_description": "Mapeamento de developer tools criadas na América Latina com tração global.",
        "sources": [
            "https://github.com/explore",
            "https://techcrunch.com/2025/09/12/latam-devtools-global-traction-8-tools",
            "https://restofworld.org/2025/latam-developer-tools-payment-webhook-observability",
        ],
        "body_md": """Historicamente, a América Latina consumiu ferramentas de desenvolvimento criadas em outros lugares. Em 2025, isso está mudando. Mapeamos 8 developer tools criadas por equipes LATAM que atingiram mais de 1.000 stars no GitHub ou mais de 500 usuários ativos.

O padrão é consistente: nenhuma dessas ferramentas tenta reinventar categorias existentes. Todas resolvem problemas de nicho que os grandes players ignoram — debugging de webhooks em ambientes de pagamento fragmentados, testing de integrações bancárias em sandbox, observability otimizado para edge functions em regiões com alta latência.

O sinal mais forte: duas dessas ferramentas foram aceitas no programa de open source do GitHub (GitHub Sponsors) e uma está no pipeline de aquisição de uma empresa de DevEx americana. Developer tools é uma vertical onde a proximidade com problemas reais de infraestrutura LATAM se torna vantagem competitiva global.""",
    },
    {
        "slug": "briefing-26-venture-debt-latam",
        "title": "Venture debt chega à América Latina: alternativa ou armadilha?",
        "subtitle": "TAMBÉM: 5 deals mapeados · US$120M em dívida · Silicon Valley Bank effect",
        "agent_name": "funding",
        "content_type": "ANALYSIS",
        "confidence_dq": 4.0,
        "published_at": "2025-09-08",
        "meta_description": "Análise da chegada do venture debt como instrumento de financiamento na América Latina.",
        "sources": [
            "https://techcrunch.com/2025/09/05/venture-debt-latam-triplepoint-hercules",
            "https://bloomberg.com/news/articles/2025-09-06/latam-venture-debt-svb-effect-120m",
            "https://sifted.eu/articles/venture-debt-latam-alternative-dilution-2025",
        ],
        "body_md": """Venture debt — dívida estruturada para startups que já captaram equity — está chegando à América Latina com dois anos de atraso em relação ao mercado americano. Nos últimos 90 dias, mapeamos 5 deals de venture debt na região totalizando US$120M. É o começo de um mercado que nos EUA movimenta US$30B por ano.

A chegada é impulsionada por dois fatores: o colapso do SVB abriu espaço para novos players, e o custo de equity na LATAM ficou tão alto que fundadores estão buscando alternativas não-dilutivas. TriplePoint, Hercules e um player local (ainda não anunciado) estão ativando operações na região.

O risco é real: venture debt na LATAM opera em um ambiente onde recuperação de crédito é significativamente mais lenta e complexa que nos EUA. A empresa que usa dívida para estender runway sem resolver unit economics está apenas adiando o problema — com juros. Para as certas (receita recorrente, churn baixo, path to profitability claro), é uma ferramenta poderosa.""",
    },
    {
        "slug": "briefing-25-agritech-latam-dados-satelite",
        "title": "Agritech LATAM: dados de satélite e IA estão transformando o agro",
        "subtitle": "TAMBÉM: 3 Series A no setor · US$67M investidos · Precision agriculture",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-09-01",
        "meta_description": "Como dados de satélite e IA estão revolucionando o agritech na América Latina.",
        "sources": [
            "https://techcrunch.com/2025/08/29/latam-agritech-satellite-ai-series-a-67m",
            "https://bloomberg.com/news/articles/2025-08-30/brazil-argentina-precision-agriculture-adoption",
            "https://restofworld.org/2025/agritech-latam-starlink-iot-cooperative-distribution",
        ],
        "body_md": """O agritech latino-americano está passando por uma transformação silenciosa impulsionada pela convergência de três tecnologias: imagens de satélite de alta resolução (agora acessíveis a US$0.50/hectare), modelos de IA treinados em dados agrícolas regionais, e IoT de baixo custo com conectividade via satélite (Starlink).

Três startups de agritech LATAM fecharam Series A nas últimas 6 semanas — duas no Brasil e uma na Argentina — totalizando US$67M. Todas compartilham uma tese: o agro latino-americano opera com margem bruta alta mas eficiência operacional baixa. Cada 1% de melhoria em rendimento por hectare representa bilhões de dólares em valor capturado.

O dado mais relevante: a adoção de precision agriculture por fazendas acima de 1.000 hectares no Brasil saltou de 12% para 34% entre 2023 e 2025. A barreira não é mais tecnológica — é de go-to-market. Startups que conseguem distribuir via cooperativas e revendas agrícolas estão crescendo 3x mais rápido que as que vendem direto.""",
    },
    {
        "slug": "briefing-24-cybersecurity-latam-gap",
        "title": "O gap de cybersecurity na LATAM: problema de US$8B que ninguém resolve",
        "subtitle": "DEEP DIVE: Mapeamento com 15 fontes e 6 entrevistas",
        "agent_name": "sintese",
        "content_type": "DEEP_DIVE",
        "confidence_dq": 5.0,
        "published_at": "2025-08-25",
        "meta_description": "Deep dive sobre o gap de cybersecurity na América Latina e oportunidades para startups.",
        "sources": [
            "https://theinformation.com/articles/latam-cybersecurity-8b-market-gap",
            "https://restofworld.org/2025/latam-cybersecurity-sme-enterprise-gap",
            "https://bloomberg.com/news/articles/2025-08-22/latam-cybersecurity-startups-mid-market",
        ],
        "body_md": """A América Latina tem o maior gap de cybersecurity per capita entre regiões emergentes — e esse gap está crescendo. Com a digitalização acelerada pós-pandemia, a superfície de ataque expandiu massivamente, mas o investimento em segurança não acompanhou. Estimamos o mercado endereçável em US$8B, com menos de 15% servido por soluções locais.

Entrevistamos 6 CISOs de empresas brasileiras e mexicanas de grande porte. O consenso: soluções americanas e israelenses dominam o mercado enterprise, mas são caras demais para o mid-market e completamente inacessíveis para PMEs. O gap real não está no topo da pirâmide — está no meio e na base, onde 90% das empresas LATAM operam sem qualquer proteção além de antivírus básico.

Mapeamos 12 startups de cybersecurity na região. A maioria ataca o segmento enterprise, competindo com incumbentes globais. As duas com melhor traction atacam o mid-market com modelos self-service de preço acessível — exatamente onde o gap é maior. É a mesma lógica que funcionou para fintechs: democratizar acesso a serviços que antes eram exclusivos de grandes empresas.""",
    },
    {
        "slug": "briefing-23-legaltech-compliance-automatizado",
        "title": "Legaltech LATAM: compliance automatizado é a killer app",
        "subtitle": "TAMBÉM: 4 startups de RegTech · NLP jurídico em português · Automação fiscal",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-08-18",
        "meta_description": "Como legaltech e compliance automatizado estão crescendo na América Latina.",
        "sources": [
            "https://techcrunch.com/2025/08/15/latam-legaltech-regtech-nlp-compliance-automation",
            "https://restofworld.org/2025/latam-legal-complexity-nlp-startup-opportunity",
            "https://bloomberg.com/news/articles/2025-08-16/latam-regtech-big4-pilot-compliance",
        ],
        "body_md": """Se existe uma vertical onde a complexidade regulatória da América Latina se torna vantagem em vez de obstáculo, é legaltech. A região tem a legislação tributária mais complexa do mundo (o Brasil sozinho tem mais de 60 tributos diferentes), e cada mudança regulatória cria demanda por automação.

Quatro startups de RegTech LATAM captaram nos últimos 60 dias, todas na interseção de NLP + compliance. O caso de uso dominante: monitoramento automático de mudanças regulatórias com alertas contextualizados por setor e jurisdição. Parece simples, mas a execução exige modelos de linguagem treinados em jargão jurídico em português e espanhol — algo que modelos genéricos fazem mal.

O sinal mais forte desta semana: uma das big four de auditoria está testando internamente uma solução de compliance automatizado desenvolvida por uma startup brasileira. Se o piloto escalar, é validação institucional que pode acelerar a adoção por todo o mercado enterprise. A legaltech LATAM está onde a fintech estava em 2017 — prestes a explodir.""",
    },
    {
        "slug": "briefing-22-proptech-real-estate-digital",
        "title": "PropTech LATAM: o real estate encontra a digitalização (finalmente)",
        "subtitle": "TAMBÉM: Tokenização de imóveis · Marketplace B2B · Credit scoring imobiliário",
        "agent_name": "radar",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-08-11",
        "meta_description": "Análise da digitalização do mercado imobiliário na América Latina via proptech.",
        "sources": [
            "https://techcrunch.com/2025/08/08/latam-proptech-31-startups-tokenization-real-estate",
            "https://bloomberg.com/news/articles/2025-08-09/brazil-cvm-sandbox-real-estate-tokens",
            "https://restofworld.org/2025/latam-proptech-credit-scoring-alternative-data",
        ],
        "body_md": """O mercado imobiliário é a última grande vertical da economia latino-americana a ser digitalizada — e 2025 é o ano em que isso começou a mudar de verdade. Mapeamos 31 proptechs ativas na região, 14 delas fundadas nos últimos 18 meses. O capital acumulado no setor: US$280M.

A tokenização de imóveis emergiu como o caso de uso mais promissor, especialmente no Brasil, onde a CVM (regulador de valores mobiliários) criou um sandbox regulatório específico para tokens imobiliários. Três plataformas já operam com licença experimental, e o volume transacionado triplicou no último trimestre.

Mas o impacto maior pode vir de uma aplicação menos sexy: credit scoring imobiliário baseado em dados alternativos. Na LATAM, 60% dos compradores de primeiro imóvel não têm histórico de crédito tradicional suficiente. Startups que usam dados de aluguel, utilities e comportamento digital para gerar scores estão desbloqueando uma demanda reprimida gigantesca.""",
    },
    {
        "slug": "briefing-21-cloud-soberania-latam",
        "title": "Soberania digital: por que LATAM precisa de clouds regionais",
        "subtitle": "TAMBÉM: LGPD enforcement cresce · Data residency no México · Edge computing",
        "agent_name": "codigo",
        "content_type": "DEEP_DIVE",
        "confidence_dq": 4.0,
        "published_at": "2025-08-04",
        "meta_description": "Deep dive sobre soberania digital e a necessidade de infraestrutura cloud regional na América Latina.",
        "sources": [
            "https://techcrunch.com/2025/08/01/latam-sovereign-cloud-lgpd-mexico-data-residency",
            "https://bloomberg.com/news/articles/2025-08-02/magalu-cloud-kio-claro-regional-cloud-latam",
            "https://restofworld.org/2025/latam-cloud-sovereignty-hybrid-workloads",
        ],
        "body_md": """A discussão sobre soberania digital na América Latina saiu do campo acadêmico e entrou no operacional. Com a LGPD brasileira emitindo suas primeiras multas significativas e o México implementando requisitos de data residency para o setor financeiro, a pergunta "onde estão nossos dados?" deixou de ser teórica.

Os três grandes hyperscalers (AWS, Azure, GCP) têm regiões na América Latina — Brasil e Chile para AWS, Brasil para Azure, Chile e Brasil para GCP. Mas para setores regulados (saúde, finanças, governo), regiões de hyperscalers nem sempre satisfazem os requisitos de soberania. Dados precisam estar em infraestrutura auditável por reguladores locais.

Isso está criando espaço para clouds regionais especializadas. Magalu Cloud no Brasil, KIO Networks no México e Claro Cloud na Colômbia estão investindo pesado em certificações de segurança e compliance. O mercado de cloud soberana na LATAM vai de US$200M em 2024 para uma projeção de US$1.2B em 2027. Para startups de infraestrutura, a oportunidade está em ferramentas que facilitem workloads híbridos entre hyperscalers e clouds regionais.""",
    },
    {
        "slug": "briefing-20-talent-war-engenheiros-senior",
        "title": "A guerra silenciosa por engenheiros sênior na América Latina",
        "subtitle": "TAMBÉM: Remote-first vs presencial · Salários em dólar · Brain drain reverso",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-07-28",
        "meta_description": "Análise da competição por talento técnico sênior na América Latina.",
        "sources": [
            "https://bloomberg.com/news/articles/2025-07-25/latam-senior-engineers-talent-war-remote",
            "https://restofworld.org/2025/latam-brain-drain-reverse-startup-founders",
            "https://techcrunch.com/2025/07/26/brazil-mexico-argentina-engineer-salaries-2025",
        ],
        "body_md": """Existe uma guerra silenciosa acontecendo na América Latina por um recurso escasso: engenheiros de software com mais de 8 anos de experiência e fluência em inglês. Empresas americanas contratando remotamente, startups locais, big techs com escritórios na região e consultoras de nearshoring estão todas competindo pelo mesmo pool de ~50 mil profissionais.

O impacto é direto nos salários: um engenheiro sênior em São Paulo que ganhava R$25k/mês em 2022 agora recebe R$35-45k (ou US$6-8k se contratado por empresa americana). A escalada está forçando startups locais — que pagam em reais — a competir em cultura, equity e missão, porque não podem competir em cash.

O fenômeno mais interessante: um brain drain reverso está começando. Engenheiros sênior LATAM que trabalharam 3-5 anos em big techs americanas remotamente estão voltando para startups locais, aceitando salários menores em troca de equity significativo e impacto direto no produto. É o ciclo de maturidade do ecossistema se completando — experiência acumulada retornando como capital humano fundador.""",
    },
    {
        "slug": "briefing-19-marketplace-b2b-verticalizacao",
        "title": "Marketplaces B2B verticais: a próxima fronteira do e-commerce LATAM",
        "subtitle": "TAMBÉM: Supply chain digital · GPO models · Unit economics de B2B marketplaces",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-07-21",
        "meta_description": "Análise do crescimento de marketplaces B2B verticais na América Latina.",
        "sources": [
            "https://techcrunch.com/2025/07/18/latam-b2b-vertical-marketplaces-340m-investment",
            "https://lavca.org/2025/b2b-marketplace-latam-supply-chain-embedded-finance",
            "https://bloomberg.com/news/articles/2025-07-19/latam-b2b-marketplace-financing-unit-economics",
        ],
        "body_md": """Enquanto marketplaces B2C (Mercado Libre, Amazon, Rappi) dominam as manchetes, uma revolução silenciosa está acontecendo no B2B. Mapeamos 19 marketplaces B2B verticais na América Latina — plataformas que conectam compradores e fornecedores em setores específicos: insumos industriais, materiais de construção, insumos agrícolas, material hospitalar.

O investimento acumulado nesses 19 marketplaces: US$340M nos últimos 24 meses. O ticket médio de transação é 40x maior que em B2C, e o churn é significativamente menor — empresas que encontram um fornecedor confiável raramente trocam. Os unit economics são fundamentalmente diferentes e mais favoráveis.

O padrão de sucesso é claro: marketplaces B2B que vencem na LATAM não competem em preço (race to the bottom) mas em confiabilidade e crédito. Oferecer financing para o comprador e garantia de pagamento para o fornecedor é o que desbloqueia liquidez. É embedded finance aplicado a supply chain — e os dados mostram que startups com essa feature crescem 2.5x mais rápido que as sem.""",
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
                    review_status, published_at, meta_description, sources
                ) VALUES (
                    :id, :title, :slug, :subtitle, :body_md, :summary,
                    :content_type, :agent_name, :confidence_dq,
                    :review_status, :published_at, :meta_description, :sources
                )
            """),
            {
                "id": str(uuid.uuid4()),
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
                "sources": json.dumps(item.get("sources")),
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
