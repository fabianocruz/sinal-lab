---
# Metadados para o Admin da Sinal
title: "120 commits, 5 agentes e nenhuma linha de frontend"
subtitle: "Semana 0 do diário de construção — como nasceu a infraestrutura de agentes da Sinal em três dias"
author_name: "Santos de Machine"
content_type: ARTICLE
summary: "Em três dias construímos 5 agentes de IA, 15 fontes de dados, um pipeline editorial com LLM, um orchestrator e 800+ testes. Sem frontend, sem deploy, sem domínio. Só o motor."
meta_description: "Diário de construção da Sinal, semana 0. Cinco agentes de IA, 15 fontes de dados, pipeline editorial com Claude e 800 testes — construídos em três dias antes de qualquer frontend existir."
sources:
  - https://sinal.tech
  - https://github.com/fabianocruz/sinal-lab
---

Começamos na segunda-feira com um repositório vazio e terminamos na quarta com cinco agentes de IA rodando, 15 fontes de dados integradas, um pipeline editorial com LLM no loop, e mais de 800 testes automatizados. Sem frontend. Sem deploy. Sem domínio registrado. A decisão foi deliberada: construir o motor antes da carroceria.

A tese da Sinal é que inteligência proprietária sobre o ecossistema tech LATAM vale mais do que o modelo de IA que a produz. Modelos são commodity — todo mundo tem acesso ao Claude, ao GPT, ao Gemini. O que diferencia é o dado, a curadoria, e a camada de confiança que você constrói por cima. Então começamos por ali.

## Cinco agentes em um dia

No primeiro dia, o repositório ganhou 120 commits. Não é um número que deveria impressionar — é um número que deveria preocupar. Velocidade assim sugere que ou estamos cortando corners, ou que a arquitetura está funcionando. Nesse caso, foi o segundo.

Cada agente da Sinal segue a mesma anatomia: config, collector, pipeline, synthesizer, writer, main. O SINTESE faz curadoria de notícias tech para uma audiência técnica brasileira. O RADAR rastreia tendências emergentes antes de virarem consenso. O CODIGO cobre o ecossistema de desenvolvedores — repos, packages, ferramentas. O FUNDING persegue rodadas de investimento. O MERCADO mapeia startups e players do ecossistema.

A decisão que permitiu a velocidade foi construir um framework compartilhado antes de qualquer agente individual. Uma shared source layer que abstrai HTTP com retry, RSS parsing, e coleta do GitHub. Um shared CLI que dá a qualquer agente `--dry-run`, `--verbose`, `--persist` de graça. Uma shared persistence layer que sabe persistir no banco com rollback em caso de falha. Um orchestrator que conecta coleta, editorial e persistência em um fluxo atômico.

Quando o framework ficou pronto, cada agente novo era basicamente configuração. Quais fontes usar, como pontuar relevância, o que passar para o LLM sintetizar. O FUNDING levou menos de uma hora para ficar operacional depois que o SINTESE estava rodando — porque a infraestrutura era a mesma.

## O LLM como editor, não como autor

Uma decisão que tomamos cedo e que está se provando correta: o LLM não é o autor do conteúdo. Ele é o editor.

Cada agente coleta dados de fontes reais — RSS feeds, APIs, repositórios. O collector traz o material bruto. O scorer pontua relevância. O synthesizer organiza a narrativa. Só aí o writer manda para o Claude com um prompt editorial específico por território. O LLM recebe dados factuais com fontes, não um pedido vago de "escreva sobre startups". Ele edita, não inventa.

Isso resolve dois problemas de uma vez. Primeiro, proveniência: cada dado no output tem rastreabilidade até a fonte original, com URL, timestamp e método de extração. Segundo, alucinação: se o LLM recebe fatos verificados como input, a margem para inventar é menor. Não é zero — mas é mensurável, e o pipeline editorial pega as discrepâncias.

O pipeline editorial é outra camada. Cada output de agente passa por um classifier que verifica aderência ao território editorial (o SINTESE tem um território diferente do CODIGO), um validator que checa completude, e um sistema de confiança em duas dimensões: data quality e analysis confidence. Conteúdo com confiança abaixo do threshold vai para revisão humana. Conteúdo acima pode ser publicado automaticamente.

## 15 fontes e a lição do Google News

Nos dias dois e três, focamos em expandir a camada de fontes. Google News RSS, Google Trends, ProductHunt GraphQL, Crunchbase (API e dataset aberto), Reddit, LinkedIn via RapidAPI, Bluesky via AT Protocol. Cada fonte é um módulo independente com seus próprios testes.

Duas lições desses dias.

Primeira: APIs sociais são hostis por padrão. LinkedIn cobra por dados básicos. Reddit exige OAuth com client credentials para qualquer query. Bluesky tem rate limits agressivos na search pública. Twitter cobra caro pelo tier mínimo. A consequência prática é que a camada de fontes tem que ser resiliente a falha — qualquer fonte pode sumir amanhã, e o agente precisa continuar operando com as que restam.

Segunda: o Google News é uma fonte incrivelmente rica que quase ninguém usa programaticamente. O RSS do Google News aceita queries e retorna resultados recentes com título, fonte, data e URL. Não precisa de API key. É limitado em volume, mas para monitoramento editorial de nicho — que é exatamente o nosso caso — é ouro. Viraria a fonte primária do SINTESE e do FUNDING.

## O que não fizemos

Três dias, nenhuma linha de frontend. Nenhum CSS. Nenhum deploy. O domínio sinal.tech existia registrado, mas apontava para lugar nenhum. A landing page era um arquivo HTML estático de referência do design system, não uma aplicação rodando.

A tentação de colocar algo no ar é enorme. Mas a decisão de postergar o frontend foi estratégica. Se a API não funciona, o frontend é cosmético. Se os agentes não produzem conteúdo de qualidade, a newsletter é ruído. Melhor ter um backend sólido sem interface do que uma interface bonita sem substância por trás.

O custo dessa decisão: três dias sem nada para mostrar para ninguém. Nenhum link para mandar. Nenhuma screenshot para postar. É um custo real quando você está construindo em público e precisa de feedback. Aceitamos o custo.

## Onde terminou a semana 0

No final de quarta-feira, a Sinal tinha:

- 5 agentes rodando localmente com `python scripts/run_agents.py all`
- 15 fontes de dados integradas e testadas
- Pipeline editorial com LLM no loop (Claude como editor)
- Orchestrator conectando coleta → editorial → persistência
- Evidence system para deduplicação cross-agent
- 800+ testes automatizados cobrindo agents, sources, editorial e scripts
- PostgreSQL local com schema, migrations e seed
- Zero frontend, zero deploy, zero usuários

A base estava pronta. Agora precisava sair do localhost.

---

*Infraestrutura não tem screenshot. Mas tem compound interest.*
