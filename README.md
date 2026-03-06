# Sinal.lab

**Inteligencia aberta para quem constroi.**

AI-native intelligence platform for the LATAM tech ecosystem. Weekly curated newsletter powered by specialized AI agents with full data provenance, editorial governance, and transparency.

**Live:** [sinal.tech](https://sinal.tech) | **API:** sinalapi-prod.up.railway.app

---

## Quick Start

### Prerequisites

- **Node.js** >= 20
- **pnpm** >= 9
- **Python** >= 3.12
- **Docker** (for PostgreSQL + Redis)

### Setup

```bash
# Clone the repository
git clone <repo-url> && cd sinal-lab

# Install JavaScript dependencies
pnpm install

# Install Python dependencies
pip install -r packages/database/requirements.txt
pip install -r apps/agents/requirements.txt
pip install feedparser httpx pytest python-dotenv

# Copy environment variables
cp .env.example .env

# Start infrastructure (PostgreSQL + Redis)
docker compose up -d

# Run database migrations
alembic -c packages/database/alembic.ini upgrade head

# Seed initial company data
python scripts/seed_companies.py

# Start the API server
uvicorn apps.api.main:app --reload --port 8000

# Start the Next.js dev server (in a new terminal)
pnpm dev
```

### Running Agents

```bash
# Subprocess mode (default) -- each agent runs in its own process
python scripts/run_agents.py sintese --dry-run --verbose
python scripts/run_agents.py sintese --edition 1 --persist
python scripts/run_agents.py sintese --edition 1 --persist --send
python scripts/run_agents.py all --persist

# Orchestrate mode -- in-process with editorial review + evidence persistence
python scripts/run_agents.py radar --week 8 --orchestrate
python scripts/run_agents.py all --week 8 --orchestrate
python scripts/run_agents.py funding --week 8 --orchestrate --no-editorial
python scripts/run_agents.py all --week 8 --orchestrate --no-evidence

# Generate cover images for newsletters
python scripts/generate_covers.py --edition 49 --verbose
python scripts/generate_covers.py --edition 49 --sync-to <prod_url>

# Generate cover images for articles
python scripts/generate_article_covers.py --dry-run
python scripts/generate_article_covers.py --database-url <prod_url> --force
```

### Running Tests

```bash
# All Python tests (1970+ tests)
python -m pytest packages/ apps/agents/ scripts/tests/ -v

# All frontend tests (998 tests)
cd apps/web && pnpm test

# Specific test suites
python -m pytest apps/agents/base/tests/ -v           # Base framework + orchestrator
python -m pytest apps/agents/sources/tests/ -v         # Shared source layer
python -m pytest apps/agents/sintese/tests/ -v         # SINTESE agent
python -m pytest apps/agents/funding/tests/ -v         # FUNDING agent
python -m pytest apps/agents/mercado/tests/ -v         # MERCADO agent
python -m pytest apps/agents/covers/tests/ -v          # Cover image pipeline
python -m pytest apps/agents/editorial/tests/ -v       # Editorial pipeline
python -m pytest packages/editorial/tests/ -v          # Editorial rules (classifier, validator)
python -m pytest scripts/tests/ -v                     # Agent runner + article cover CLI tests

# Next.js type check + build
pnpm build
```

---

## Architecture

```
sinal-lab/
├── apps/
│   ├── web/                  # Next.js 14 App Router
│   │   ├── app/              # Pages: landing, /newsletter, /artigos, /startups, /agentes
│   │   ├── components/       # Navbar, Footer, newsletter/, article/, startup/ components
│   │   └── lib/              # API client, types, constants, JSON-LD utilities
│   ├── api/                  # FastAPI backend
│   │   ├── routers/          # health, agents, content, companies, waitlist, editorial
│   │   └── schemas/          # Pydantic response models
│   └── agents/               # AI agent system
│       ├── base/             # Shared framework: BaseAgent, CLI, persistence, orchestrator
│       ├── sources/          # Shared source layer: HTTP, RSS, GitHub, dedup
│       ├── covers/           # Cover image pipeline: LLM prompt, Recraft V3, Pillow overlay, Vercel Blob
│       ├── sintese/          # Newsletter synthesizer (RSS + Twitter -> scored -> newsletter)
│       ├── radar/            # Emerging trend detection (HN, GitHub, arXiv)
│       ├── codigo/           # Developer ecosystem signals (GitHub, npm, PyPI)
│       ├── funding/          # Investment tracking (VC rounds, Dealroom)
│       ├── mercado/          # LATAM startup mapping (GitHub Search, Dealroom)
│       ├── index/            # LATAM Startup Index (collectors, pipeline, scorer, persistence)
│       └── editorial/        # Editorial governance: guidelines, editorial-in-the-loop
├── packages/
│   ├── database/             # SQLAlchemy models + Alembic migrations
│   │   ├── models/           # 9 tables: companies, content_pieces, agent_runs, evidence_items, etc.
│   │   └── migrations/       # Version-controlled schema changes
│   ├── editorial/            # Editorial rules: classifier, validator, guidelines
│   ├── shared/               # Shared TypeScript utilities
│   └── data-pipeline/        # Data ingestion pipeline (future)
├── scripts/
│   ├── run_agents.py         # Unified agent runner (subprocess + orchestrate modes)
│   ├── generate_covers.py    # Newsletter cover image generation
│   ├── generate_article_covers.py  # Article cover image generation
│   ├── seed_companies.py     # Company data seeder
│   ├── seed_content.py       # Newsletter seed data
│   └── cron.example          # Production cron schedule
├── docs/                     # Technical documentation
├── docker-compose.yml        # PostgreSQL 16 + Redis 7
├── CLAUDE.md                 # Engineering preferences & workflow standards
└── .env.example              # Environment variable template
```

### Agent System

| Agent | Category | Role | Status |
|-------|----------|------|--------|
| **SINTESE** | Content | Newsletter curation & synthesis | Built |
| **RADAR** | Content | Emerging trend detection | Built |
| **CODIGO** | Content | Developer ecosystem signals | Built |
| **FUNDING** | Data | Investment tracking (VC rounds, amounts, investors) | Built |
| **MERCADO** | Data | LATAM startup mapping & ecosystem intelligence | Built |
| **INDEX** | Data | LATAM startup ranking engine (collectors, pipeline, scorer) | Built |
| **EDITORIAL** | Quality | 6-layer editorial governance pipeline | Built |
| **COVERS** | Quality | AI cover image generation (LLM art direction + Recraft V3) | Built |
| SEO ENGINE | Quality | Programmatic SEO page generation | Planned |

Each agent follows the `collect -> process -> score -> output` lifecycle with mandatory confidence scoring and data provenance tracking. The orchestrator connects agents to the editorial pipeline and persistence layer in a single atomic transaction.

### Cover Image Pipeline

AI-generated editorial cover images for newsletters and articles:

```
Editorial content -> LLM art director (Claude Sonnet) -> Recraft V3 prompt
    -> Image generation (realistic_image, 1820x1024)
    -> Pillow overlay (brand badge, gradient, color bar)
    -> Resize to 1200x628 (OG standard)
    -> Upload to Vercel Blob
    -> Update metadata.hero_image in DB
```

- **Newsletter covers**: Agent-specific color + badge (SINTESE, RADAR, etc.)
- **Article covers**: Topic-driven metaphors (not generic monitors), ARTIGO badge, author badge, 5-color bottom bar
- **Art direction**: LLM generates unique prompts per content, enforcing physical-world metaphors and visual diversity

### Editorial Governance Pipeline

Every piece of content passes through a 6-layer review pipeline before publication:

```
PESQUISA -> VALIDACAO -> VERIFICACAO -> VIES -> SEO.engine -> SINTESE_FINAL
```

1. **PESQUISA**: Source provenance validation (URLs, timestamps, extraction methods)
2. **VALIDACAO**: Data quality cross-referencing (multi-source for financials, freshness)
3. **VERIFICACAO**: Structural fact-checking (percentages, dates, URLs, duplicates)
4. **VIES**: Bias detection (geographic, sectoral, source concentration)
5. **SEO.engine**: Search optimization (titles, meta, headers, JSON-LD)
6. **SINTESE_FINAL**: Final assembly (byline, confidence badge, source list)

Content that fails any critical layer is flagged for human review.

**Editorial-in-the-loop**: The agent orchestrator integrates editorial review into the agent lifecycle. When running in `--orchestrate` mode, agents automatically pass through the editorial pipeline. Content graded as `publish_ready` is set to `approved`; everything else routes to `pending_review` for human review.

### Email Dispatch

Newsletter delivery via Resend API:

- LLM-generated subject lines (Claude Sonnet) with edition number
- HTML email with hero image, SINTESE article cards, markdown body
- Triggered via `--send` flag: `python scripts/run_agents.py sintese --persist --send`

### Data Integrity

- **Confidence Scoring**: DQ (Data Quality) + AC (Analysis Confidence) on a 1-5 scale with A-D grades
- **Provenance Tracking**: Every data point traced to source, method, and timestamp
- **Source Diversity**: Max 3 items per source in newsletter curation

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Pydantic, SQLAlchemy 2.0 |
| Database | PostgreSQL 16, Alembic |
| Cache | Redis 7 |
| Agents | Python, feedparser, httpx, Anthropic SDK |
| Cover Images | Recraft V3 API, Pillow, Vercel Blob |
| Email | Resend (transactional + broadcasts) |
| SEO | JSON-LD, dynamic sitemaps, hreflang |
| Hosting | Vercel (frontend), Railway (API + DB) |
| Monorepo | pnpm workspaces |

---

## Frontend Pages

| Route | Description | Rendering |
|-------|-------------|-----------|
| `/` | Landing page | SSR |
| `/newsletter` | Newsletter archive (paginated) | SSR + ISR (60s) |
| `/newsletter/[slug]` | Newsletter detail (gated content) | SSR + ISR (300s) |
| `/artigos` | Articles listing (paginated) | SSR + ISR (60s) |
| `/artigos/[slug]` | Article detail (gated content) | SSR + ISR (300s) |
| `/startups` | Startup map listing (search, filters) | SSR + ISR (60s) |
| `/startup/[slug]` | Startup detail + JSON-LD | SSR + ISR (300s) |
| `/agentes/[name]` | Agent dashboard | SSR |
| `/sobre` | About page | SSR |
| `/metodologia` | Methodology / transparency | SSR |
| `/login` | Login (credentials + Google OAuth) | Client |
| `/cadastro` | Signup | Client |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/agents/runs` | List agent execution history |
| GET | `/api/agents/summary` | Latest run per agent (for /transparencia) |
| POST | `/api/agents/runs/{name}/trigger` | Trigger agent run |
| GET | `/api/content` | List content (filter by type, agent, status) |
| GET | `/api/content/{slug}` | Get content by slug (full body) |
| GET | `/api/content/newsletter/latest` | Latest published newsletter |
| GET | `/api/companies` | List tracked companies (search, filter by sector/country/tags) |
| GET | `/api/companies/{slug}` | Company detail (22 fields) |
| POST | `/api/waitlist` | Join founding member waitlist |
| GET | `/api/waitlist/count` | Waitlist size |
| POST | `/api/editorial/review` | Run editorial pipeline on content |
| GET | `/api/editorial/queue` | Content pending review |
| POST | `/api/editorial/approve/{slug}` | Approve content for publication |

---

## Deployment

### Frontend (Vercel)

Deployed via Git integration (auto-deploy on push to `main`).

**Build command:** `pnpm --filter @sinal/web build`

**Environment variables:** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXTAUTH_URL`, `NEXTAUTH_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

### Backend (Railway)

Deployed via Dockerfile at repo root.

**Environment variables:** `DATABASE_URL`, `PORT=8000`, `CORS_ORIGINS`, `API_ENV`

### Scheduling Agents

See `scripts/cron.example` for production cron schedule. Agents can also be triggered via the API.

---

## Development Workflow

See [CLAUDE.md](CLAUDE.md) for full engineering preferences and workflow standards.

- **Plan Before You Code**: Every feature starts with a plan
- **TDD**: Tests written before or alongside implementation
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, etc.
- **Branch Strategy**: `feature/`, `fix/`, `agent/`, `docs/` prefixes
- **Run tests before every commit**: `pytest apps/ packages/ -v && pnpm test`

---

## License

Private. All rights reserved.
