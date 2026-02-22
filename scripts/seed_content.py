#!/usr/bin/env python3
"""Seed the content_pieces table with the 30 founding newsletters.

Usage:
    python scripts/seed_content.py                  # insert into DB
    python scripts/seed_content.py --dry-run        # preview without writing
    python scripts/seed_content.py --force           # re-insert (delete existing by slug)

Requires DATABASE_URL environment variable or .env file.

Editorial territories covered (target weights):
    T1 Fintech & Economia Digital (40%)
    T2 AI Aplicada & Infraestrutura (20%)
    T3 Cripto, Stablecoins & Ativos Digitais (10%)
    T4 Engenharia, Arquitetura & Infraestrutura (20%)
    T5 Venture Capital & Funding LATAM (15%)
    T6 Green Tech, AgriTech & Impacto (5%)
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
    # === Edições 47-42: Jan-Fev 2026 ===
    {
        "slug": "briefing-47-paradoxo-modelo-gratuito",
        "title": "O paradoxo do modelo gratuito: quando abundância de IA vira commodity e escassez vira produto",
        "subtitle": "TAMBEM: 14 rodadas mapeadas · US$287M total · Rust ganha tração em fintechs BR",
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
        "slug": "briefing-46-drex-real-digital-pagamentos",
        "title": "Drex: o real digital entra em fase 2 — o que muda para fintechs e bancos",
        "subtitle": "TAMBEM: 16 instituições na fase piloto · Smart contracts em real · DvP tokenizado",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": 4.0,
        "published_at": "2026-02-03",
        "meta_description": "Análise da fase 2 do Drex e o impacto para fintechs, bancos e infraestrutura de pagamentos no Brasil.",
        "body_md": """O Banco Central do Brasil iniciou a fase 2 do piloto do Drex com 16 instituições participantes — incluindo Nubank, Mercado Pago, BTG e Itaú. A diferença em relação à fase 1 é substancial: agora o foco é em casos de uso reais com smart contracts, não apenas em infraestrutura de liquidação.

Os três casos de uso prioritários confirmados: DvP (Delivery versus Payment) para títulos públicos tokenizados, crédito colateralizado por ativos digitais, e pagamentos programáveis entre instituições. O Banco Central estimou que só o DvP de títulos pode reduzir custos de liquidação em 60% — o que representa bilhões de reais por ano em eficiência operacional para o sistema financeiro.

Para fintechs, o sinal mais relevante é a decisão do BC de usar uma camada de privacidade baseada em zero-knowledge proofs, permitindo que transações em Drex sejam auditáveis pelo regulador mas invisíveis entre participantes. Isso resolve o principal bloqueio que bancos tinham com blockchain pública — e abre espaço para que fintechs construam produtos de crédito e investimento sobre uma infraestrutura que antes era exclusiva de grandes instituições.""",
    },
    {
        "slug": "briefing-45-rust-fintechs-migracao-infraestrutura",
        "title": "Por que fintechs LATAM estão migrando infraestrutura crítica para Rust",
        "subtitle": "TAMBEM: 3 vagas Rust em fintechs BR · Benchmarks de latência · Nubank open-source",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2026-01-27",
        "meta_description": "Análise técnica da migração de serviços críticos para Rust em fintechs da América Latina.",
        "body_md": """Uma tendência clara está surgindo entre as fintechs de grande escala na América Latina: a migração gradual de serviços críticos de Python e Go para Rust. O motivo não é performance pura, mas sim a combinação de segurança de memória, previsibilidade de latência e redução de custos de infraestrutura cloud que Rust proporciona em ambientes de alta throughput.

O caso mais documentado: uma fintech brasileira de pagamentos migrou seu serviço de autorização de transações Pix de Go para Rust e reportou redução de 73% no P99 de latência (de 45ms para 12ms) e 40% em custos de EC2. Em um sistema que processa 2 milhões de transações por dia, a economia de infra paga o investimento em reescrita em menos de 6 meses.

O sinal técnico mais interessante da semana: três vagas abertas em fintechs brasileiras exigindo Rust — duas para infraestrutura de pagamentos e uma para motor de regras de compliance. Há seis meses isso seria incomum. Agora sugere uma mudança estrutural na stack. Nubank contribuiu um crate open-source de serialização otimizada para mensagens do sistema financeiro brasileiro (SPB), sinalizando que a adoção é institucional, não experimental.""",
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
        "subtitle": "TAMBEM: Fintech domina 41% do capital · Seed rounds +40% em número",
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
        "subtitle": "TAMBEM: 3 M&As silenciosos · Nova onda de BaaS no México",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2026-01-06",
        "meta_description": "Mapeamento das fintechs LATAM: quem sobreviveu ao inverno de 2023-2024.",
        "body_md": """Começamos 2026 com um exercício de mapeamento: o que restou do boom de fintechs LATAM de 2020-2022? A resposta é mais nuançada do que o pessimismo do mercado sugere.

Das 340 fintechs que mapeamos em 2022, 187 ainda estão operacionais. Dessas, 43 pivotaram significativamente o modelo de negócios. E 12 passaram por aquisições silenciosas — deals que nunca foram anunciados publicamente mas que confirmamos por registros corporativos e movimentações de equipe no LinkedIn.

O padrão dos sobreviventes é consistente: focaram em um vertical estreito, priorizaram rentabilidade sobre crescimento entre 2023 e 2024, e construíram defensibilidade regulatória. A empresa que tentou ser banco, wallet, crédito e investimento ao mesmo tempo geralmente não está mais aqui.""",
    },
    # === Edição Especial: Retrospectiva 2025 ===
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
    # === Edições 41-29: Dez/2025 → Set/2025 ===
    {
        "slug": "briefing-41-kubernetes-latam-infraestrutura",
        "title": "Kubernetes na LATAM: do hype à infraestrutura real",
        "subtitle": "TAMBEM: 3 clouds regionais ganham tração · GitOps em fintechs BR",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-12-22",
        "meta_description": "Como Kubernetes passou de buzzword a infraestrutura crítica em startups LATAM.",
        "body_md": """A adoção de Kubernetes na América Latina seguiu um caminho diferente do que os evangelistas previam. Em vez da migração massiva de monolitos para microserviços, o que vimos em 2025 foi algo mais pragmático: empresas adotando Kubernetes como plataforma de deploy, não como arquitetura.

O dado mais relevante da semana: três provedores de cloud regionais — Magalu Cloud (Brasil), KIO Networks (México) e Mercado Libre Cloud (Argentina) — reportaram crescimento de 200% em clusters Kubernetes gerenciados. O padrão é claro: startups LATAM querem a ergonomia do Kubernetes sem a complexidade operacional.

O sinal técnico mais interessante: GitOps está se consolidando como o workflow padrão em fintechs brasileiras reguladas pelo Banco Central. ArgoCD e Flux aparecem em 67% das vagas de SRE/Platform Engineering postadas no último mês. A razão é regulatória — auditoria de deploys é requisito do Open Finance.""",
    },
    {
        "slug": "briefing-40-mapa-ia-generativa-latam",
        "title": "O mapa de IA generativa aplicada na América Latina",
        "subtitle": "TAMBEM: 23 startups mapeadas · US$89M em rodadas de IA · LLMs em português",
        "agent_name": "sintese",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-12-15",
        "meta_description": "Mapeamento completo de startups de IA generativa aplicada na América Latina.",
        "body_md": """Mapeamos 23 startups na América Latina que estão construindo produtos de IA generativa aplicada — não wrappers de API, mas empresas com diferenciação real em dados, distribuição ou domínio vertical. O resultado é um panorama que surpreende pela maturidade.

O padrão dominante: IA generativa aplicada a problemas de compliance e regulação. Sete das 23 empresas mapeadas atacam alguma variante de "transformar regulação complexa em ação automatizada" — desde compliance tributário no Brasil até KYC na Colômbia. A razão é estrutural: a América Latina tem a regulação mais fragmentada do mundo em desenvolvimento, e LLMs são excepcionalmente bons em navegar ambiguidade regulatória.

As rodadas confirmam a tese: US$89M foram investidos em startups de IA generativa LATAM nos últimos 90 dias. O ticket médio subiu de US$1.2M para US$3.8M, indicando que investidores estão passando de "seed exploratório" para "aposta com convicção".""",
    },
    {
        "slug": "briefing-39-climate-tech-capital-latam",
        "title": "Climate tech LATAM: o capital está chegando — mas para quem?",
        "subtitle": "TAMBEM: Créditos de carbono tokenizados · Energia solar descentralizada",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-12-08",
        "meta_description": "Análise do fluxo de capital para climate tech na América Latina.",
        "body_md": """O sinal mais consistente das últimas semanas vem de um setor que historicamente foi ignorado pelo venture capital latino-americano: climate tech. Três fundos globais — Breakthrough Energy, Lowercarbon Capital e Congruent Ventures — abriram operações ou contrataram partners dedicados à região nos últimos 60 dias.

O que mudou não é a urgência climática (essa já existia) mas a viabilidade econômica. Créditos de carbono no mercado voluntário atingiram preços que tornam projetos de conservação na Amazônia e no Cerrado economicamente competitivos com soja e pecuária. Startups como Moss e Carbonext estão na interseção exata entre tech e carbono.

O dado mais interessante: o Brasil concentra 34% de todos os créditos de carbono de natureza emitidos globalmente, mas apenas 3% do capital de venture dedicado a climate tech. Esse gap é a oportunidade — e os fundos que estão chegando sabem disso.""",
    },
    {
        "slug": "briefing-38-novembro-rodadas-series-b",
        "title": "Novembro: 18 rodadas, US$342M e 3 Series B que ninguém esperava",
        "subtitle": "TAMBEM: Seed médio sobe para US$2.4M · YC aceita recorde de LATAM founders",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-12-01",
        "meta_description": "Análise das 18 rodadas de novembro 2025: US$342M investidos em startups LATAM.",
        "body_md": """Novembro fechou com 18 rodadas mapeadas totalizando US$342M — o melhor mês desde março de 2022. Mas o número absoluto esconde o que realmente importa: a composição mudou radicalmente.

Três Series B dominaram o mês: uma fintech de crédito para PMEs no México (US$85M), uma infraestrutura de pagamentos cross-border no Brasil (US$62M) e uma plataforma de BaaS colombiana (US$48M). As três compartilham um perfil: fundadas entre 2019 e 2020, sobreviveram ao inverno com unit economics positivos, e agora estão expandindo com disciplina. Nenhuma queimou capital para crescer — cresceram para merecer capital.

O dado de seed é igualmente relevante: o ticket médio de seed rounds subiu de US$1.6M para US$2.4M. Mais capital por empresa, menos empresas financiadas. Os investidores estão concentrando apostas, não dispersando. YC aceitou 14 startups LATAM no batch de inverno — recorde absoluto.""",
    },
    {
        "slug": "briefing-37-super-apps-falharam-latam",
        "title": "Por que as super apps falharam na América Latina (e o que veio no lugar)",
        "subtitle": "TAMBEM: Rappi pivota para fintech · Mercado Pago vs Nubank",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-11-24",
        "meta_description": "Análise de por que o modelo de super app não funcionou na América Latina.",
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
        "body_md": """Conduzimos um survey com 340 data engineers em seis países (Brasil, México, Argentina, Colômbia, Chile e Peru) para mapear o estado real da engenharia de dados na região. Os resultados contradizem várias narrativas populares.

Descoberta 1: dbt é a ferramenta de transformação dominante (72% de adoção), mas Airflow está perdendo terreno para Dagster e Prefect entre equipes menores. A razão é operacional — manter Airflow em produção exige um SRE dedicado que startups em estágio inicial não têm.

Descoberta 2: o salário médio de data engineer sênior no Brasil (US$4.200/mês) está convergindo com o do México (US$3.800/mês), mas a diferença com a Argentina (US$2.100/mês) está aumentando — criando uma arbitragem de talento que empresas remotas estão explorando ativamente.

Descoberta 3: o gap mais crítico não é técnico, é de governança. Apenas 18% dos respondentes reportam ter um data catalog em produção. A maioria opera com "conhecimento tribal" — e isso se torna insustentável acima de 10 pessoas na equipe de dados.""",
    },
    {
        "slug": "briefing-35-stablecoins-trilho-pagamento-latam",
        "title": "Stablecoins como trilho de pagamento: a adoção silenciosa na América Latina",
        "subtitle": "TAMBEM: USDT domina remessas · Circle abre operação em SP · Regulação MiCA effect",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": 4.0,
        "published_at": "2025-11-10",
        "meta_description": "Como stablecoins estão se tornando infraestrutura de pagamento na América Latina.",
        "body_md": """A narrativa dominante sobre cripto na América Latina ainda é especulação — mas os dados contam outra história. O uso de stablecoins como trilho de pagamento, não como investimento, cresceu 280% na região nos últimos 12 meses. USDT (Tether) processa mais volume em remessas Brasil-Venezuela e Argentina-Paraguai do que Western Union.

O dado mais revelador: 67% do volume de stablecoins na LATAM é USDT em redes de baixo custo (Tron, Polygon), não USDC em Ethereum. O perfil de uso é pragmático — trabalhadores enviando US$200-500 por transação para familiares, PMEs pagando fornecedores internacionais sem Swift, e freelancers recebendo em dólar digital. Nenhum desses use cases aparece em relatórios de exchanges tradicionais porque acontecem peer-to-peer.

Circle abriu escritório em São Paulo na última semana e anunciou integração direta com Pix para on/off-ramp de USDC. Para fintechs brasileiras, isso cria uma ponte entre o sistema financeiro regulado (Pix) e a economia de stablecoins — exatamente o tipo de infraestrutura que habilita novos produtos de pagamento cross-border sem depender de correspondentes bancários.""",
    },
    {
        "slug": "briefing-34-mexico-unicornios-mudanca",
        "title": "México supera Brasil em novos unicórnios pela primeira vez: o que mudou",
        "subtitle": "TAMBEM: Nearshoring tech acelera · Monterrey como hub de IA",
        "agent_name": "mercado",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-11-03",
        "meta_description": "México ultrapassa Brasil em novos unicórnios tech em 2025.",
        "body_md": """Pela primeira vez desde que o ecossistema tech LATAM existe como categoria de investimento, o México produziu mais novos unicórnios que o Brasil em um ano calendário. Em 2025: México 4, Brasil 2. O número absoluto é pequeno, mas o sinal direcional é inequívoco.

As razões são estruturais, não conjunturais. O nearshoring — a migração de cadeias produtivas dos EUA da China para o México — criou uma demanda massiva por infraestrutura digital que simplesmente não existia três anos atrás. Cada fábrica nova precisa de ERP, logística, fintech B2B, e compliance automatizado. Startups mexicanas estão na posição certa, no momento certo.

Monterrey emergiu como o hub de IA mais relevante da América Latina em 2025, com 47 startups de IA catalogadas (vs 23 em 2024). A combinação de proximidade com os EUA, talento do Tec de Monterrey, e capital de VCs americanos que veem o México como extensão natural do mercado US está criando um cluster que não existia há dois anos.""",
    },
    {
        "slug": "briefing-33-semana-redefiniu-vc-latam",
        "title": "A semana que redefiniu o venture capital na América Latina",
        "subtitle": "TAMBEM: SoftBank volta · Novo fundo de US$500M focado em LATAM",
        "agent_name": "sintese",
        "content_type": "ANALYSIS",
        "confidence_dq": 5.0,
        "published_at": "2025-10-27",
        "meta_description": "Como uma semana de anúncios redefiniu o venture capital LATAM.",
        "body_md": """Em cinco dias, três anúncios mudaram o panorama do venture capital na América Latina. SoftBank anunciou um novo fundo de US$500M dedicado à região (metade do Latin America Fund II original, mas com tese radicalmente diferente). Kaszek fechou seu Fund V de US$800M. E a16z fez sua primeira aposta direta na região — uma fintech de crédito em São Paulo.

O que esses três movimentos têm em comum: disciplina. O SoftBank de 2025 não é o SoftBank de 2021. O novo fundo tem tickets menores (US$10-30M vs US$50-100M), exige break-even antes de Series B, e tem um comitê de investimento que inclui operators latino-americanos. É uma admissão implícita de que a estratégia anterior — cheques grandes em empresas pre-revenue — falhou na região.

Para fundadores, o sinal é ambíguo: há mais capital disponível, mas com mais condições. A era do "crescimento a qualquer custo" acabou definitivamente. A era do "crescimento eficiente com métricas reais" começou.""",
    },
    {
        "slug": "briefing-32-mapa-capital-startups-latam",
        "title": "De onde vem o dinheiro: mapeando os 50 investidores mais ativos em LATAM",
        "subtitle": "TAMBEM: Corporate venture cresce 60% · Family offices entram no jogo",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-10-20",
        "meta_description": "Mapeamento dos 50 investidores mais ativos no ecossistema tech LATAM.",
        "body_md": """Mapeamos os 50 investidores mais ativos em startups LATAM nos últimos 12 meses por número de deals. O ranking revela uma mudança estrutural: pela primeira vez, investidores regionais dominam os top 10, deslocando fundos americanos que lideravam há três anos.

Kaszek lidera com 34 deals, seguido por NXTP (28), Valor Capital (24) e Canary (22). A surpresa é a ascensão de corporate ventures: Itaú Unibanco Ventures, Mercado Libre Fund e Globo Ventures entraram no top 20 pela primeira vez. Corporate VC cresceu 60% em número de deals — as corporações estão comprando opções no futuro através de investimento em startups.

O dado mais interessante: family offices representam agora 15% dos cheques em seed rounds LATAM (vs 4% em 2022). São famílias de industriais brasileiros e mexicanos que estão diversificando de real estate e agro para tech. O ticket médio é menor (US$200-500K), mas a velocidade de decisão é muito maior que a de VCs tradicionais.""",
    },
    {
        "slug": "briefing-31-open-source-latam-contribuidores",
        "title": "Open source na LATAM: de consumidores a contribuidores",
        "subtitle": "TAMBEM: Elixir cresce em São Paulo · Terraform LATAM community",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-10-13",
        "meta_description": "Como a América Latina está passando de consumidora a contribuidora de open source.",
        "body_md": """A comunidade open source latino-americana atingiu um ponto de inflexão em 2025. Pela primeira vez, contribuições de desenvolvedores LATAM para projetos top-100 do GitHub representam mais de 5% do total global. Parece pouco, mas em 2020 era 1.2%.

O padrão de contribuição é revelador: desenvolvedores LATAM não estão criando novos frameworks — estão melhorando documentação, escrevendo adapters para casos de uso regionais (compliance brasileiro, integração com Pix, suporte a espanhol), e construindo ferramentas de developer experience. É contribuição pragmática, não acadêmica.

Três comunidades se destacam: Elixir em São Paulo (impulsionada pela adoção massiva de Phoenix LiveView em fintechs), Terraform na Colômbia (driven by cloud migration em empresas tradicionais), e Rust em Buenos Aires (com foco em infraestrutura de pagamentos). O fio condutor é o mesmo: linguagens e ferramentas que resolvem problemas reais de infraestrutura na região.""",
    },
    {
        "slug": "briefing-30-open-finance-brasil-dashboard-adocao",
        "title": "Open Finance Brasil: dashboard de adoção — APIs ativas, consentimentos e quem lidera",
        "subtitle": "TAMBEM: 22M consentimentos ativos · Nubank lidera em dados · Recebiveis como colateral",
        "agent_name": "mercado",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-10-06",
        "meta_description": "Dashboard de adoção do Open Finance Brasil: métricas de APIs, consentimentos e instituições líderes.",
        "body_md": """O Open Finance Brasil atingiu 22 milhões de consentimentos ativos — mas o número mascara uma realidade mais interessante. A adoção está profundamente concentrada: cinco instituições respondem por 78% dos consentimentos de dados, e apenas três oferecem produtos reais baseados em dados compartilhados (portabilidade de crédito, agregação de contas, e score alternativo).

O dado mais relevante para quem está construindo: a API de recebíveis de cartão (fase 4) entrou em operação e já está sendo usada como colateral em operações de crédito para PMEs. Uma fintech brasileira reportou que consegue aprovar crédito para pequenos negócios em 4 horas usando dados de recebíveis via Open Finance — versus 15 dias via análise tradicional. A diferença de conversão é de 3x.

A oportunidade mais subestimada: a API de investimentos (fase 3b) permite que fintechs agreguem posições de fundos, ações e renda fixa de diferentes corretoras em uma única tela. Quem construir o "Mint brasileiro" sobre Open Finance vai capturar o segmento de alta renda que hoje está fragmentado entre 3-4 plataformas. Os dados mostram que 40% dos investidores PF no Brasil têm posições em mais de uma corretora.""",
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
        "body_md": """A América Latina está regulando inteligência artificial de cinco formas diferentes em cinco países. Brasil, México, Colômbia, Chile e Argentina seguem caminhos divergentes — e essa fragmentação está criando tanto riscos quanto oportunidades para startups de IA na região.

Brasil lidera com o PL 2338/2023, a regulação mais detalhada e prescritiva da região: classificação de risco obrigatória, sandbox regulatório, e uma autoridade dedicada (que ainda não existe). México optou por uma abordagem de soft law — diretrizes voluntárias sem força de lei. Colômbia criou um framework setorial (regulações diferentes para IA em saúde, finanças e governo). Chile apostou em princípios éticos sem mecanismos de enforcement. Argentina simplesmente não tem regulação — e algumas startups de IA estão se incorporando lá exatamente por isso.

Para quem está construindo: a fragmentação regulatória é um moat para startups que conseguem navegar múltiplas jurisdições. RegTech de IA — ferramentas que ajudam empresas a cumprir regulações de IA em diferentes países LATAM — é uma vertical que não existia há 12 meses e que agora tem pelo menos 4 startups financiadas.""",
    },
    # === Edições 28-19: Set/2025 → Jul/2025 ===
    {
        "slug": "briefing-28-infraestrutura-pagamentos-latam",
        "title": "A guerra invisível da infraestrutura de pagamentos na América Latina",
        "subtitle": "TAMBEM: Pix internacional · SPEI evolui · Transferencias 3.0 na Argentina",
        "agent_name": "sintese",
        "content_type": "DATA_REPORT",
        "confidence_dq": 5.0,
        "published_at": "2025-09-22",
        "meta_description": "Análise da competição entre infraestruturas de pagamento instantâneo na América Latina.",
        "body_md": """A batalha mais consequente do ecossistema fintech latino-americano não está acontecendo no nível de aplicação — está na camada de infraestrutura de pagamentos. Três sistemas nacionais estão evoluindo em paralelo: Pix no Brasil (4 bilhões de transações/mês), SPEI/CoDi no México (780 milhões/mês), e Transferencias 3.0 na Argentina (120 milhões/mês).

O dado mais relevante desta semana: o Banco Central do Brasil anunciou que o Pix internacional entrará em operação no segundo trimestre de 2026, permitindo transferências instantâneas entre Brasil e países do Mercosul. Isso muda fundamentalmente o cenário para fintechs de remessas — o custo médio de enviar US$200 do Brasil para a Argentina deve cair de US$12 (Western Union) para menos de US$1 (Pix internacional).

Para quem está construindo: a interoperabilidade entre sistemas de pagamento nacionais vai criar uma camada de infraestrutura que não existe hoje. Startups que consigam abstrair as diferenças entre Pix, SPEI e Transferencias 3.0 em uma API unificada estão posicionadas para capturar valor desproporcional. Três empresas já estão construindo isso — nenhuma anunciou publicamente.""",
    },
    {
        "slug": "briefing-27-custos-inferencia-llm-startups-latam",
        "title": "O custo real de rodar LLMs em produção: benchmark para startups LATAM",
        "subtitle": "TAMBEM: GPU cloud na região · Fine-tuning vs RAG · Otimização de prompts",
        "agent_name": "codigo",
        "content_type": "ANALYSIS",
        "confidence_dq": 4.0,
        "published_at": "2025-09-15",
        "meta_description": "Benchmark de custos de inferência LLM para startups na América Latina.",
        "body_md": """Coletamos dados de custos reais de 14 startups LATAM que operam LLMs em produção — não benchmarks teóricos, mas faturas mensais reais de cloud e API. O resultado desmistifica várias suposições sobre o custo de operar IA generativa na região.

O dado mais surpreendente: startups que migraram de API pura (OpenAI/Anthropic) para modelos open-source hospedados (Llama 3, Mistral) em GPU cloud regional (AWS São Paulo, Oracle Mexico City) reduziram custos em 60-80%, mas aumentaram latência em 40%. Para aplicações real-time (chatbots, copilots), a API é mais barata quando o volume é abaixo de 500K tokens/dia. Acima disso, self-hosting compensa — mas exige um engenheiro de ML dedicado que custa US$5-8K/mês no Brasil.

A otimização mais impactante não é infra, é prompt engineering. Três das 14 startups reportaram redução de 50% em custos apenas com cache de embeddings e prompt compression — sem mudar modelo ou provedor. Para quem está construindo produtos de IA na LATAM, a recomendação é clara: otimize prompts antes de otimizar infraestrutura.""",
    },
    {
        "slug": "briefing-26-credito-sub-bancarizados-ai-scoring",
        "title": "Scoring de crédito para sub-bancarizados: os modelos de AI que fintechs LATAM estão usando",
        "subtitle": "TAMBEM: 40M sem score tradicional no BR · Dados alternativos · Default rates comparados",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-09-08",
        "meta_description": "Como fintechs LATAM usam AI e dados alternativos para scoring de crédito de sub-bancarizados.",
        "body_md": """Quarenta milhões de brasileiros adultos não têm score de crédito no Serasa ou SPC — são invisíveis para o sistema financeiro tradicional. Na América Latina como um todo, o número é 200 milhões. Cinco fintechs na região captaram um total de US$180M nos últimos 18 meses para resolver exatamente esse problema, usando AI e dados alternativos.

Os modelos convergem em três fontes de dados: comportamento de pagamento de utilities (luz, água, telefone), dados transacionais de Pix (com consentimento via Open Finance), e sinais digitais (regularidade de uso de smartphone, padrões de e-commerce). O melhor modelo público da região — de uma fintech colombiana — reporta uma taxa de default de 4.2% em empréstimos para clientes sem score tradicional, versus 3.8% do mercado tradicional com score. A diferença é marginal, mas o TAM é gigantesco.

O risco regulatório é real: a ANPD (autoridade de proteção de dados brasileira) está investigando dois modelos de scoring alternativo por possível discriminação algorítmica — modelos treinados em dados de localização e consumo podem reproduzir viés socioeconômico. Para quem está construindo: explicabilidade do modelo não é feature, é requisito de sobrevivência regulatória.""",
    },
    {
        "slug": "briefing-25-tokenizacao-ativos-cvm-sandbox",
        "title": "Tokenização de ativos no Brasil: os primeiros resultados do sandbox da CVM",
        "subtitle": "TAMBEM: R$2.1B tokenizados · 8 plataformas operando · Recebíveis lideram",
        "agent_name": "radar",
        "content_type": "ANALYSIS",
        "confidence_dq": 4.0,
        "published_at": "2025-09-01",
        "meta_description": "Primeiros resultados do sandbox da CVM para tokenização de ativos no Brasil.",
        "body_md": """O sandbox regulatório da CVM para tokenização de ativos completou 12 meses com 8 plataformas operando e R$2.1 bilhões em ativos tokenizados. O número impressiona, mas a composição revela onde está o valor real: 72% são recebíveis (duplicatas, precatórios, aluguéis), 18% são imóveis fracionados, e apenas 10% são tokens de equity ou dívida corporativa.

A dominância de recebíveis não é acidente — é o caso de uso onde tokenização resolve uma dor real e mensurável. No mercado tradicional, antecipar recebíveis custa 2-4% ao mês para PMEs. Via tokenização com smart contracts, o custo cai para 1-1.5% porque a liquidação é automática e o risco de fraude documental é eliminado. Uma plataforma brasileira reporta que origina R$80M/mês em recebíveis tokenizados com inadimplência de 0.3%.

Para o ecossistema de cripto/ativos digitais na LATAM, o sinal é claro: o caso de uso que escala não é especulação nem DeFi puro, é a ponte entre ativos reais (real-world assets) e infraestrutura blockchain. A CVM sinalizou que vai transformar o sandbox em regulação permanente no Q1 2026, o que pode abrir o mercado para instituições que esperavam segurança jurídica antes de entrar.""",
    },
    {
        "slug": "briefing-24-ai-fraude-pix-arquiteturas",
        "title": "AI para detecção de fraude no Pix: arquiteturas, modelos e taxas de false positive",
        "subtitle": "DEEP DIVE: Como 5 fintechs brasileiras estão combatendo fraude em tempo real",
        "agent_name": "sintese",
        "content_type": "DEEP_DIVE",
        "confidence_dq": 5.0,
        "published_at": "2025-08-25",
        "meta_description": "Deep dive técnico sobre detecção de fraude no Pix com AI: arquiteturas e benchmarks de 5 fintechs.",
        "body_md": """O Pix processa 4 bilhões de transações por mês — e fraudes cresceram 47% em 2025 segundo dados do Banco Central. As cinco maiores fintechs brasileiras investiram coletivamente R$400M em sistemas de detecção de fraude baseados em AI no último ano. Investigamos as arquiteturas por trás desses sistemas.

O padrão arquitetural dominante: pipeline de 3 estágios em tempo real. Estágio 1: regras determinísticas (blocklists, limites de valor, geofencing) — filtra 85% das transações em <5ms. Estágio 2: modelo de ML (gradient boosting ou neural network) analisa as 15% restantes em <50ms usando features como device fingerprint, grafo social de transações, e padrões temporais. Estágio 3: modelo de linguagem analisa o contexto semântico de transações suspeitas (mensagens em chaves Pix, padrões de engenharia social) — <200ms.

O trade-off mais crítico é false positive rate. Uma fintech reportou que reduzir fraude em 0.5% custou 2% em transações legítimas bloqueadas — cada transação bloqueada é um cliente irritado. O sweet spot que as 5 fintechs convergiram: taxa de detecção de 92-94% com false positive rate de 0.8-1.2%. Ir além de 94% de detecção dispara o false positive exponencialmente. Para quem está construindo: invista mais em explicabilidade da decisão para o cliente do que em accuracy marginal do modelo.""",
    },
    {
        "slug": "briefing-23-neobanks-unit-economics-latam",
        "title": "Unit economics dos neobanks LATAM: Nubank, Ualá e Mercado Pago comparados",
        "subtitle": "TAMBEM: CAC vs LTV por país · Revenue per user · Custo de servir vs receita",
        "agent_name": "mercado",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-08-18",
        "meta_description": "Análise comparativa de unit economics dos neobanks na América Latina.",
        "body_md": """Pela primeira vez, conseguimos comparar unit economics de três dos maiores neobanks da América Latina usando dados de seus relatórios trimestrais e estimativas de analistas. O resultado revela modelos de negócio mais diferentes do que os nomes similares sugerem.

Nubank: 100M de clientes, ARPAC (receita média por cliente ativo) de US$11/mês, custo de servir US$0.80/mês. O moat é escala e cross-sell — 37% dos clientes usam 3+ produtos. O CAC caiu para US$5 via referral orgânico. Ualá (Argentina/México): 8M clientes, ARPAC de US$3.20/mês (muito menor por mix de renda e câmbio), mas custo de servir de US$0.40/mês. Modelo mais enxuto, focado em pagamentos e remessas. Mercado Pago: integrado ao marketplace, o CAC efetivo é zero (o cliente já está no ecossistema), mas ARPAC de US$6.50/mês porque a monetização é dominada por acquiring de sellers, não por produtos bancários.

O dado mais relevante para fundadores de fintech: o custo de adquirir um cliente bancário no Brasil caiu de US$35 (2022) para US$5-12 (2025), principalmente por causa do Pix como canal de aquisição. Mas o custo de ativar esse cliente (fazê-lo usar 3+ produtos) continua em US$20-30. A guerra agora não é aquisição — é engagement.""",
    },
    {
        "slug": "briefing-22-baas-banking-as-a-service-latam",
        "title": "Banking-as-a-Service LATAM: quem fornece a infraestrutura das fintechs",
        "subtitle": "TAMBEM: 7 plataformas comparadas · Regulação BaaS no Brasil · Compliance como moat",
        "agent_name": "radar",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-08-11",
        "meta_description": "Mapeamento das plataformas de Banking-as-a-Service na América Latina.",
        "body_md": """Para cada fintech visível ao consumidor, existe pelo menos uma empresa invisível fornecendo a infraestrutura por trás: licença bancária, ledger, compliance KYC/AML, e conexão com o sistema de pagamentos. Esse é o mercado de Banking-as-a-Service — e na América Latina, está passando por uma transformação.

Mapeamos 7 plataformas de BaaS ativas na região: Swap (Brasil), Dock (Brasil/México), Pomelo (Argentina/Colômbia), Bankly (Brasil), QI Tech (Brasil), Zoop (Brasil) e Ualá BaaS (Argentina/México). A diferenciação principal não é tecnológica (todas oferecem APIs similares) — é regulatória. As plataformas que conseguem garantir compliance com Banco Central, CNBV (México) e Superfinanciera (Colômbia) simultaneamente estão capturando clientes que querem operar em múltiplos países sem montar equipes regulatórias locais.

O mercado de BaaS LATAM cresceu de US$400M em 2023 para US$1.1B em 2025. A projeção para 2027 é US$2.8B. O driver principal: empresas não-financeiras (varejo, telecom, logística) embarcando serviços financeiros nos seus apps. Para cada fintech-first que nasce, três empresas tradicionais estão adicionando fintech como feature — e todas precisam de BaaS para fazê-lo em compliance.""",
    },
    {
        "slug": "briefing-21-observability-pagamentos-stack-sre",
        "title": "Observability em sistemas de pagamento: o stack real de SREs em fintechs brasileiras",
        "subtitle": "DEEP DIVE: Datadog vs Grafana · Alerting em tempo real · SLOs de transações Pix",
        "agent_name": "codigo",
        "content_type": "DEEP_DIVE",
        "confidence_dq": 4.0,
        "published_at": "2025-08-04",
        "meta_description": "Deep dive sobre observability e SRE em fintechs brasileiras que processam Pix.",
        "body_md": """Quando uma transação Pix falha, o SLA do Banco Central exige resolução em 10 minutos. Para fintechs que processam milhões de transações por dia, isso significa que observability não é nice-to-have — é a diferença entre manter e perder a licença de participante do Pix. Investigamos o stack real de 6 fintechs brasileiras.

O stack dominante: Grafana + Prometheus + Loki para métricas e logs (4 de 6 fintechs), com OpenTelemetry para tracing distribuído. Datadog aparece em 2 das 6 — as que processam mais volume e justificam o custo premium pelo APM mais maduro. O padrão mais interessante: todas as 6 usam synthetic monitoring customizado que simula transações Pix reais (end-to-end, incluindo SPB) a cada 30 segundos. Se o synthetic falha, o alerta dispara antes que qualquer cliente real seja afetado.

Os SLOs (Service Level Objectives) convergem: 99.95% de disponibilidade para o serviço de autorização Pix, P99 de latência abaixo de 100ms, e taxa de erro abaixo de 0.01%. O gap mais comum: 4 de 6 fintechs não têm SLOs formais para o fluxo de conciliação — que é onde a maioria dos problemas reais acontece (transação aparece como pendente por horas). A lição: monitore o caminho feliz e o caminho de exceção com a mesma seriedade.""",
    },
    {
        "slug": "briefing-20-mlops-startups-latam-stack-real",
        "title": "MLOps em startups LATAM: o stack real de quem opera AI em produção",
        "subtitle": "TAMBEM: Feature stores · Model monitoring · Custos de GPU vs API",
        "agent_name": "mercado",
        "content_type": "ANALYSIS",
        "confidence_dq": None,
        "published_at": "2025-07-28",
        "meta_description": "Stack real de MLOps em startups de AI na América Latina que operam modelos em produção.",
        "body_md": """A distância entre "temos AI" e "operamos AI em produção" continua sendo o maior gap no ecossistema de startups LATAM. Entrevistamos 10 startups da região que operam modelos de ML em produção (não PoCs, não demos — modelos que processam dados reais e geram receita) para mapear o stack real de MLOps.

O padrão dominante surpreende pela simplicidade: 7 de 10 usam MLflow para experiment tracking + registro de modelos, deployam via container Docker simples (não Kubernetes), e monitoram drift com scripts custom em Python que rodam diariamente. Ferramentas enterprise de MLOps (Weights & Biases, Neptune, Seldon) aparecem em apenas 2 startups — as que captaram Series A e têm equipes de ML acima de 5 pessoas. Para startups em estágio seed, o custo de licenças de MLOps enterprise é proibitivo.

O problema mais citado (8 de 10): model monitoring em produção. Detectar que um modelo degradou antes que o impacto chegue ao cliente é difícil quando seus dados mudam rápido — que é exatamente o caso de modelos de fraude, crédito e pricing na LATAM, onde o contexto macroeconômico é volátil. A startup mais madura da amostra roda shadow models em paralelo e compara predictions — é caro computacionalmente, mas flagra degradação em horas, não semanas.""",
    },
    {
        "slug": "briefing-19-agritech-credito-rural-satelite",
        "title": "AgriTech + Fintech: crédito rural via dados de satélite está desbloqueando o agro LATAM",
        "subtitle": "TAMBEM: R$340B mercado crédito rural BR · Scoring por NDVI · 3 fintechs no setor",
        "agent_name": "funding",
        "content_type": "DATA_REPORT",
        "confidence_dq": 4.0,
        "published_at": "2025-07-21",
        "meta_description": "Como fintechs estão usando dados de satélite para scoring de crédito rural na América Latina.",
        "body_md": """O crédito rural no Brasil é um mercado de R$340 bilhões por ano — e 70% é intermediado por bancos públicos (Banco do Brasil, BNDES) usando processos que exigem visita presencial à propriedade. Três fintechs brasileiras estão atacando esse gap com uma abordagem que combina dados de satélite (NDVI, índice de vegetação), registros climáticos e histórico de produtividade para aprovar crédito remotamente em 48 horas.

O modelo de scoring é elegante: imagens de satélite Sentinel-2 (gratuitas, resolução de 10m) alimentam um modelo de ML que estima produtividade por hectare com precisão de 85%. Combinado com dados de preço de commodities e histórico de chuva, o modelo gera um score de risco agrícola que substitui a vistoria presencial. Uma das fintechs reporta inadimplência de 2.1% — menor que a média do crédito rural tradicional (3.4%).

Para o ecossistema de venture: as três fintechs captaram um total de US$67M em 2025, e o investor mais ativo no setor é o IFC (braço de investimento do Banco Mundial), que vê AgriTech + Fintech como vetor de inclusão financeira para 5 milhões de pequenos produtores que não acessam crédito bancário. É a interseção de T1 (Fintech), T2 (AI), e T6 (AgriTech) — exatamente onde os territórios editoriais convergem.""",
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
