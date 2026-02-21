# Sinal.lab — Technical Blueprint

## Vision

Sinal.lab is an AI-native intelligence platform for technical founders, CTOs, and senior engineers building in Latin America. The core product is a weekly curated newsletter ("Sinal Semanal") powered by specialized AI agents that aggregate, score, and synthesize 100+ tech news sources with full transparency, editorial governance, and data provenance.

**Tagline**: *Inteligencia aberta para quem constroi.*

---

## Core Principles

1. **One Wedge at a Time**: Start with the newsletter, prove value, then expand.
2. **Data Integrity First**: Every data point is traceable, scored, and transparent.
3. **Build for Trust**: Open methodology, confidence scores, provenance tracking.
4. **LATAM-Native**: Portuguese-first content, LATAM-specific scoring, local context.
5. **AI-Augmented, Human-Governed**: AI does the heavy lifting; editorial governance ensures quality.

---

## Agent Architecture

### Agent Lifecycle

Every agent follows the same 4-phase lifecycle:

```
collect -> process -> score -> output
```

- **collect**: Gather raw data from configured sources
- **process**: Clean, deduplicate, score, and rank
- **score**: Compute confidence metrics (Data Quality + Analysis Confidence)
- **output**: Generate structured Markdown with YAML frontmatter

### Active Agents

All 5 agents share a common runtime layer: shared CLI (`base/cli.py`), shared persistence (`base/persistence.py`), shared source layer (`sources/`), evidence writer (`base/evidence_writer.py`), and orchestrator with editorial-in-the-loop (`base/orchestrator.py`).

#### SINTESE (v0.1.0) — Newsletter Synthesizer
- **Category**: Content agent (filtered by editorial line)
- **Sources**: 37 RSS/Atom feeds across 7 categories + Twitter/X API
- **Scoring**: 4-dimensional relevance scoring (topic 35%, recency 25%, authority 15%, LATAM relevance 25%)
- **Output**: Curated newsletter draft with 18 items grouped by category
- **Diversity**: Max 3 items per source to prevent domination
- **Integration**: Resend Broadcasts for delivery, LLM writer with fallback
- **Persistence**: Shared CLI `--persist` saves AgentRun + ContentPiece to database

#### RADAR (v0.1.0) — Emerging Trend Detection
- **Category**: Content agent (filtered by editorial line)
- **Sources**: Hacker News, GitHub trending, Google Trends PT-BR, arXiv (via shared source layer)
- **Focus**: Weak signal detection for emerging technologies
- **Persistence**: DB persistence via shared persistence layer

#### CODIGO (v0.1.0) — Developer Ecosystem Signals
- **Category**: Content agent (filtered by editorial line)
- **Sources**: GitHub trending, npm/PyPI stats, Stack Overflow (via shared source layer)
- **Focus**: Mapping tools, languages, and frameworks gaining traction in LATAM
- **Persistence**: DB persistence via shared persistence layer

#### FUNDING (v0.1.0) — Investment Tracking
- **Category**: Data agent (broad LATAM coverage)
- **Sources**: 15 VC RSS feeds (Kaszek, Monashees, Valor Capital, etc.) + Dealroom API (freemium)
- **Focus**: Funding rounds, amounts, investors, round types (seed, Series A-G)
- **Features**: Currency normalization (BRL/MXN/ARS → USD), company fuzzy matching, multi-source deduplication
- **Output**: Weekly funding report grouped by round type (Series A+, Seed, Other)
- **Database**: Populates `funding_rounds` table via domain-specific `db_writer`, updates `Company.metadata_` with funding stats
- **Confidence Logic**: Multi-source verification (2+ sources → 0.8 DQ), amount conflict detection

#### MERCADO (v0.1.0) — LATAM Startup Mapping & Ecosystem Intelligence
- **Category**: Data agent (broad LATAM coverage)
- **Sources**: 5 GitHub Search APIs (São Paulo, Rio, Mexico City, Buenos Aires, Bogotá) + Dealroom API (freemium)
- **Focus**: Company profiles, sector classification, tech stack mapping, ecosystem metrics by city
- **Features**: Keyword-based sector classification (8 sectors: Fintech, HealthTech, Edtech, SaaS, etc.), GitHub org analysis, tag generation
- **Output**: Weekly ecosystem snapshot with city breakdown, sector distribution, notable startups
- **Database**: Populates `companies` table via domain-specific `db_writer`, updates `ecosystems` table with aggregated stats
- **Confidence Logic**: Field completeness scoring (12 fields), API source boost, long description boost

### Shared Infrastructure

- **Shared Source Layer** (`apps/agents/sources/`): HTTP client with retry, RSS parser, GitHub collector, dedup utilities, async variants
- **Evidence System**: Unified `EvidenceItem` dataclass, normalizer (converts agent-specific types), evidence writer (confidence-based upsert), `EvidenceItemDB` ORM model
- **Entity Resolver** (`base/entity_resolver.py`): Cross-agent entity deduplication (fuzzy matching across funding rounds, company profiles)
- **Editorial Integration**: `GuidelinesPack` facade connecting `packages/editorial/` rules to the editorial pipeline, editorial-in-the-loop orchestrator
- **Shared CLI** (`base/cli.py`): `run_agent_cli()` reduces each agent's `main.py` from ~100 lines to ~15-25 lines
- **Agent Orchestrator** (`base/orchestrator.py`): `orchestrate_agent_run()` — agent.run() → editorial review → atomic persist → evidence items → domain records

### Planned Agents

- **INDEX**: LATAM startup ranking engine (growth metrics, investor backing, tech adoption)
- **SEO ENGINE**: Programmatic SEO page generation for company profiles

---

## Editorial Governance Pipeline

All agent output passes through a 6-layer sequential review before publication:

```
PESQUISA → VALIDACAO → VERIFICACAO → VIES → SEO.engine → SINTESE_FINAL
```

| Layer | Responsibility | Can Block? |
|-------|---------------|-----------|
| PESQUISA | Source provenance validation | Yes |
| VALIDACAO | Data quality cross-referencing | Yes |
| VERIFICACAO | Structural fact-checking | Yes |
| VIES | Bias detection (geographic, sectoral, source) | No (warning) |
| SEO.engine | Search optimization | No (modifications) |
| SINTESE_FINAL | Final assembly & publish readiness | Yes |

Content that receives a BLOCKER flag is routed to the human review queue (`GET /api/editorial/queue`).

---

## Data Model

### Core Tables (9 tables)

- **companies**: LATAM tech companies with sector, location, tags, tech stack
- **content_pieces**: All generated content with confidence scores, review status, body Markdown/HTML
- **agent_runs**: Complete audit trail of agent executions (timing, metrics, errors)
- **data_provenance**: Source tracking for every data point (URL, method, confidence)
- **evidence_items**: Unified cross-agent evidence store with content_hash dedup and confidence-based upsert
- **investors**: VC funds, angels, accelerators with portfolio data
- **funding_rounds**: Investment events linking companies to investors
- **ecosystems**: City/region tech ecosystem profiles with metrics
- **users**: Waitlist subscribers and platform members

### Confidence Framework

Every output includes two independent metrics:

- **Data Quality (DQ)**: How good is the underlying data? (source count, verification, freshness)
- **Analysis Confidence (AC)**: How confident is the analysis? (methodology, cross-validation)

Composite score = (DQ * 0.6 + AC * 0.4), mapped to grades A-D and a 1-5 display scale.

---

## Content Strategy

### Newsletter ("Sinal Semanal")

- **Frequency**: Weekly (Saturdays)
- **Audience**: Technical founders, CTOs, senior engineers in LATAM
- **Sections**: AI & ML, Startups & Funding, Fintech, Infrastructure & Dev Tools, LATAM Ecosystem
- **Format**: 18 curated items with source attribution, summaries, and category grouping
- **Tone**: Technical, data-driven, Portuguese-first
- **Delivery**: Resend (broadcasts + transactional)

---

## Frontend Pages

| Route | Description | Data Source |
|-------|-------------|------------|
| `/` | Landing page with waitlist form | Static + API waitlist count |
| `/transparencia` | Agent methodology, pipeline, confidence scale | `GET /api/agents/summary` |
| `/newsletter` | Newsletter archive (published editions) | `GET /api/content?content_type=DATA_REPORT&status=published` |
| `/newsletter/[slug]` | Individual newsletter with sidebar metadata | `GET /api/content/{slug}` |

All pages include programmatic SEO: JSON-LD structured data, canonical URLs, Open Graph, hreflang, dynamic sitemap.

---

## Execution Roadmap

### Sprint 1 (Complete)
- Monorepo scaffold + configuration
- Database models + Alembic migrations setup
- Base agent framework (confidence, provenance, output)
- SINTESE agent (RSS collection, scoring, newsletter synthesis)
- Landing page with waitlist form
- Documentation

### Sprint 2 (Complete)
- RADAR + CODIGO agents
- Expanded database schema (investors, funding rounds, ecosystems, users)
- FastAPI backend with REST endpoints
- Company and content API routers

### Sprint 3 (Complete)
- Full editorial governance pipeline (6 layers)
- Frontend pages: /transparencia, /newsletter archive, /newsletter/[slug]
- Programmatic SEO (JSON-LD, sitemaps, hreflang)
- Navbar, Footer, ConfidenceBadge components

### Sprint 4 (Complete)
- Database alignment (unified PostgreSQL config)
- Initial Alembic migration (8 tables)
- Company seeding script + CSV (20 LATAM startups)
- Frontend→Backend wiring (API proxy, waitlist, live data fetching)
- Newsletter delivery integration (Resend Broadcasts)
- Unified agent runner script + cron schedule
- Deployment configs (Vercel, Docker, Procfile)
- Full README rewrite + blueprint update

### Phase 1: Shared Source Layer (Complete)
- Agent classification system (data vs content vs quality agents)
- Editorial classifier, validator, and expanded guidelines (`packages/editorial/`)
- SINTESE: Twitter/X API integration, multi-source routing, LLM editorial writer
- Shared HTTP client with retry, RSS parser, GitHub collector, dedup utilities (`agents/sources/`)
- Collector refactors: all 4 agents (SINTESE, RADAR, CODIGO, FUNDING) use shared source layer
- Unified EvidenceItem model + DB migration (`evidence_items` table)
- Evidence normalizer (converts agent-specific types to EvidenceItem)
- Entity resolver (cross-agent fuzzy matching for companies/funding)
- GuidelinesPack facade connecting editorial rules to pipeline
- Async RSS and GitHub fetching support

### Phase 2: Agent Runtime (Complete)
- Shared persistence layer (`persist_agent_run`, `persist_content_piece`, `persist_agent_output`)
- EvidenceItemDB ORM model + evidence writer (confidence-based upsert)
- Shared CLI (`run_agent_cli`) — reduced 5 agent `main.py` files from ~100 lines to ~15-25 lines each
- Agent orchestrator with editorial-in-the-loop (`orchestrate_agent_run`)
- `run_agents.py` updated with `--orchestrate` mode (in-process with editorial review)
- RADAR and CODIGO get DB persistence for the first time
- Removed `sys.path.insert` hacks from 16 test files
- 957+ tests passing across the full suite

### Next Priorities
- Production deployment (Vercel + Railway/Render)
- First real newsletter edition
- User dashboard with personalized feeds
- Community features (company submission, feedback loop)
- INDEX agent implementation (startup ranking)
- SEO ENGINE agent (programmatic page generation)

---

## Infrastructure

| Component | Technology | Environment |
|-----------|-----------|-------------|
| Database | PostgreSQL 16 | Docker (dev), managed (prod) |
| Cache | Redis 7 | Docker (dev), managed (prod) |
| Frontend | Next.js 14 | Vercel |
| Backend | FastAPI | Docker / Railway / Render |
| Agents | Python (cron-scheduled) | Server / GitHub Actions |
| Monorepo | pnpm workspaces | — |

---

*Last updated: February 2026*
