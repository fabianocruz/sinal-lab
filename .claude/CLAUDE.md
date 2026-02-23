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
- Email: Resend (transactional + broadcasts)
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
│       ├── index/           # LATAM Startup Index — collectors, pipeline, scorer, persistence
│       ├── # --- Agents de Conteudo (escopo: linha editorial) ---
│       ├── sintese/         # Newsletter Synthesizer — audiencia tecnica
│       ├── radar/           # Trend Intelligence — tendencias para publico tecnico
│       ├── codigo/          # Code & Infra Research — tecnologia e infraestrutura
│       ├── # --- Pipeline de Qualidade ---
│       ├── editorial/       # Editorial pipeline — filtra dados para publicacao
│       └── seo_engine/      # SEO Optimization — paginas programaticas (future)
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
- `pytest apps/api/tests/test_content.py -v` — Testes do content router (13 testes)
- `pytest apps/api/tests/test_companies.py -v` — Testes do companies router (20 testes)
- `pytest packages/ apps/agents/ scripts/tests/ -v` — Roda todos os testes Python (1370+)
- `pytest apps/agents/base/tests/ -v` — Testes do framework base + orchestrator
- `pytest apps/agents/sources/tests/ -v` — Testes da source layer compartilhada
- `pnpm build` — Build de producao
- `docker compose up -d` — Sobe PostgreSQL + Redis
- `python scripts/seed_content.py --dry-run` — Preview seed das newsletters
- `DATABASE_URL=<url> python scripts/seed_content.py` — Seed newsletters no banco

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
- Newsletter pages (/newsletter, /newsletter/[slug]) sao SSR com ISR (revalidate: 60s lista, 300s detalhe)
- Startup pages (/startups, /startup/[slug]) sao SSR com ISR — mesma pattern das newsletters
- Startup detail pages incluem JSON-LD Organization (schema.org) para SEO
- Componentes Pagination e SearchBar sao generalizados com prop `basePath` (reutilizados em /newsletter e /startups)
- Frontend faz fallback para FALLBACK_NEWSLETTERS quando API esta offline

### API — Contratos de Resposta
- `GET /api/content` retorna envelope paginado: `{ items: [...], total, limit, offset }`
- `GET /api/content/{slug}` retorna ContentDetailResponse (objeto unico)
- `GET /api/content/newsletter/latest` retorna ContentResponse (objeto unico)
- `GET /api/companies` retorna envelope paginado: `{ items: [...], total, limit, offset }`
- `GET /api/companies/{slug}` retorna CompanyDetailResponse (objeto unico, 22 campos)
- Frontend usa `?status=published` por padrao nas chamadas de listagem de content
- Companies usa `?status=active` por padrao (omitir status retorna apenas active)
- Filtros content: `content_type`, `agent_name`, `status`, `search` (ilike no titulo)
- Filtros companies: `sector`, `city`, `country`, `tags`, `search` (ilike no nome), `status`

### Testes — SQLite com StaticPool
- Todos os testes de API usam SQLite in-memory com `poolclass=StaticPool`
- StaticPool garante que todas as threads compartilham a mesma conexao
- Sem StaticPool, o thread pool do FastAPI cria conexoes separadas que nao veem as tabelas
- Fixtures devem usar `created_at` explicito para ordenacao deterministica (SQLite tem resolucao de segundo)

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
