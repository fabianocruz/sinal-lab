# Sinal.lab — Project Context

## Projeto: Plataforma AI-Native LATAM Tech Intelligence

### Visao
Plataforma hibrida (media + research + community + data) em portugues
para fundadores tecnicos, CTOs e engenheiros seniores na America Latina.
Codename: Sinal.lab. Tagline: "Inteligencia aberta para quem constroi."

### Stack Tecnologico
- Frontend: Next.js 14+ (App Router, SSR para SEO)
- Backend API: Python 3.12 + FastAPI
- Agent Infrastructure: Python + Claude Agent SDK
- Database: PostgreSQL 16 (local dev via Docker), Redis (cache)
- Search: Elasticsearch 8 (future)
- Data Pipeline: Apache Airflow + dbt (future)
- CMS: Sanity.io (headless, future)
- Email: Resend (transactional), Beehiiv (newsletter)
- Analytics: PostHog (self-hosted, future)
- Hosting: Vercel (frontend), AWS (backend/data), Cloudflare (CDN)

### Estrutura de Diretorios
```
/
├── apps/
│   ├── web/                 # Next.js frontend
│   ├── api/                 # FastAPI backend
│   └── agents/              # AI agent infrastructure
│       ├── base/            # Shared framework: BaseAgent, CLI, persistence, orchestrator
│       ├── sources/         # Shared source layer: HTTP, RSS, GitHub, dedup
│       ├── # --- Agents de Dados (escopo: todo ecossistema LATAM) ---
│       ├── funding/         # Capital Flow Tracker — todas as rodadas LATAM
│       ├── mercado/         # Market Intelligence — ecossistema completo
│       ├── index/           # Startup Ranking — todas as startups LATAM (planned)
│       ├── # --- Agents de Conteudo (escopo: linha editorial) ---
│       ├── sintese/         # Newsletter Synthesizer — audiencia tecnica
│       ├── radar/           # Trend Intelligence — tendencias para publico tecnico
│       ├── codigo/          # Code & Infra Research — tecnologia e infraestrutura
│       ├── # --- Pipeline de Qualidade ---
│       ├── editorial/       # Editorial pipeline — filtra dados para publicacao
│       └── seo_engine/      # SEO Optimization — paginas programaticas (planned)
├── packages/
│   ├── shared/              # Tipos compartilhados, utils
│   ├── database/            # Schema, migrations, seeds
│   └── data-pipeline/       # Airflow DAGs, dbt models (future)
├── scripts/                 # Automacao, seeding, deploy
├── docs/                    # Documentacao tecnica
└── .claude/                 # Configuracao Claude Code
```

### Comandos Principais
- `pnpm dev` — Inicia frontend (porta 3000)
- `uvicorn apps.api.main:app --reload` — Inicia API (porta 8000)
- `pnpm test` — Roda testes frontend
- `pytest apps/api/tests/` — Roda testes backend
- `pytest packages/ apps/agents/ scripts/tests/ -v` — Roda todos os testes Python (957+)
- `pytest apps/agents/base/tests/ -v` — Testes do framework base + orchestrator
- `pytest apps/agents/sources/tests/ -v` — Testes da source layer compartilhada
- `pnpm build` — Build de producao
- `docker compose up -d` — Sobe PostgreSQL + Redis

### Convencoes de Codigo
- Python: Black formatter, isort imports, type hints obrigatorios
- TypeScript: Prettier + ESLint, strict mode
- Commits: Conventional Commits (feat:, fix:, docs:, refactor:)
- Branches: feature/, fix/, agent/ prefixes
- PRs: Sempre com descricao e link para issue

### Padroes de Arquitetura
- Cada AI agent e um modulo independente em apps/agents/
- Agents compartilham: source layer (sources/), CLI (base/cli.py), persistence (base/persistence.py), orchestrator (base/orchestrator.py)
- Orchestrator conecta agent.run() → editorial review → persist atomico → evidence items
- Agents se comunicam via Redis Streams (future)
- Dados normalizados em PostgreSQL, cache em Redis
- Frontend consome API REST + WebSocket para dashboards
- Programmatic SEO pages sao geradas via SSR com dados do banco
- Agents de dados (Funding, Mercado, Index) cobrem todo o ecossistema LATAM — sem filtro editorial
- Todo output destinado a publicacao passa pelo editorial pipeline (filtro editorial + quality check)

### Variaveis de Ambiente
- Ver .env.example para lista completa
- NUNCA commitar .env ou credenciais
- API keys em AWS Secrets Manager (producao)

### Regras Criticas
- NUNCA modificar migrations existentes, criar novas
- NUNCA commitar dados de teste no banco de producao
- Todos os endpoints precisam de validacao de input (Pydantic)
- Todo conteudo publicado precisa de confidence_score
- Programmatic SEO pages precisam de min. 300 palavras unicas
