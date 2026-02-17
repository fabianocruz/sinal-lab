# Sinal.lab

**Inteligencia aberta para quem constroi.**

AI-native intelligence platform for the LATAM tech ecosystem. Weekly curated newsletter powered by specialized AI agents with full data provenance, editorial governance, and transparency.

---

## Quick Start

### Prerequisites

- **Node.js** >= 20
- **pnpm** >= 9
- **Python** >= 3.9
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
# Subprocess mode (default) — each agent runs in its own process
python scripts/run_agents.py sintese --dry-run --verbose
python scripts/run_agents.py sintese --edition 1 --persist
python scripts/run_agents.py sintese --edition 1 --persist --send
python scripts/run_agents.py all --persist

# Orchestrate mode — in-process with editorial review + evidence persistence
python scripts/run_agents.py radar --week 8 --orchestrate
python scripts/run_agents.py all --week 8 --orchestrate
python scripts/run_agents.py funding --week 8 --orchestrate --no-editorial
python scripts/run_agents.py all --week 8 --orchestrate --no-evidence
```

### Running Tests

```bash
# All Python tests (957+ tests)
python -m pytest packages/ apps/agents/ scripts/tests/ -v

# Specific test suites
python -m pytest apps/agents/base/tests/ -v           # Base framework + orchestrator
python -m pytest apps/agents/sources/tests/ -v         # Shared source layer
python -m pytest apps/agents/sintese/tests/ -v         # SINTESE agent
python -m pytest apps/agents/funding/tests/ -v         # FUNDING agent
python -m pytest apps/agents/mercado/tests/ -v         # MERCADO agent
python -m pytest apps/agents/editorial/tests/ -v       # Editorial pipeline
python -m pytest packages/editorial/tests/ -v          # Editorial rules (classifier, validator)
python -m pytest scripts/tests/ -v                     # Agent runner CLI tests

# Next.js type check + build
pnpm build
```

---

## Architecture

```
sinal-lab/
├── apps/
│   ├── web/                  # Next.js 14 App Router
│   │   ├── src/app/          # Pages: landing, /transparencia, /newsletter
│   │   ├── src/components/   # Navbar, Footer, WaitlistForm, ConfidenceBadge
│   │   └── src/lib/          # API client, JSON-LD utilities
│   ├── api/                  # FastAPI backend
│   │   ├── routers/          # health, agents, content, companies, waitlist, editorial
│   │   └── schemas/          # Pydantic response models
│   └── agents/               # AI agent system
│       ├── base/             # Shared framework: BaseAgent, CLI, persistence, orchestrator
│       ├── sources/          # Shared source layer: HTTP, RSS, GitHub, dedup
│       ├── sintese/          # Newsletter synthesizer (RSS + Twitter → scored → newsletter)
│       ├── radar/            # Emerging trend detection (HN, GitHub, arXiv)
│       ├── codigo/           # Developer ecosystem signals (GitHub, npm, PyPI)
│       ├── funding/          # Investment tracking (VC rounds, Dealroom)
│       ├── mercado/          # LATAM startup mapping (GitHub Search, Dealroom)
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
│   ├── seed_companies.py     # Company data seeder
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
| **EDITORIAL** | Quality | 6-layer editorial governance pipeline | Built |
| INDEX | Data | Startup ranking engine | Planned |
| SEO ENGINE | Quality | Programmatic SEO page generation | Planned |

Each agent follows the `collect → process → score → output` lifecycle with mandatory confidence scoring and data provenance tracking. The orchestrator connects agents to the editorial pipeline and persistence layer in a single atomic transaction.

### Editorial Governance Pipeline

Every piece of content passes through a 6-layer review pipeline before publication:

```
PESQUISA → VALIDACAO → VERIFICACAO → VIES → SEO.engine → SINTESE_FINAL
```

1. **PESQUISA**: Source provenance validation (URLs, timestamps, extraction methods)
2. **VALIDACAO**: Data quality cross-referencing (multi-source for financials, freshness)
3. **VERIFICACAO**: Structural fact-checking (percentages, dates, URLs, duplicates)
4. **VIES**: Bias detection (geographic, sectoral, source concentration)
5. **SEO.engine**: Search optimization (titles, meta, headers, JSON-LD)
6. **SINTESE_FINAL**: Final assembly (byline, confidence badge, source list)

Content that fails any critical layer is flagged for human review.

**Editorial-in-the-loop**: The agent orchestrator integrates editorial review into the agent lifecycle. When running in `--orchestrate` mode, agents automatically pass through the editorial pipeline. Content graded as `publish_ready` is set to `approved`; everything else routes to `pending_review` for human review. Editorial failures are treated as safety nets and default to human review.

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
| SEO | JSON-LD, dynamic sitemaps, hreflang |
| Monorepo | pnpm workspaces |

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
| GET | `/api/companies` | List tracked companies |
| POST | `/api/waitlist` | Join founding member waitlist |
| GET | `/api/waitlist/count` | Waitlist size |
| POST | `/api/editorial/review` | Run editorial pipeline on content |
| GET | `/api/editorial/queue` | Content pending review |
| POST | `/api/editorial/approve/{slug}` | Approve content for publication |

---

## Admin Console

The admin console provides a web interface for managing agents, reviewing content, tracking companies, and managing the waitlist.

### Accessing the Admin Console

1. **Start the backend:**
   ```bash
   uvicorn apps.api.main:app --reload --port 8000
   ```

2. **Start the frontend:**
   ```bash
   pnpm dev
   ```

3. **Access at:** http://localhost:3000/admin

### Features

#### 1. Agent Management (`/admin/agents`)
- View all agent runs with status, items processed, and confidence scores
- See detailed metrics for each run (duration, data sources, errors)
- Trigger manual agent runs with a single click
- Filter by agent name and status

**Key Components:**
- `AgentRunsTable` - Paginated table of agent runs
- `TriggerAgentButton` - Manual agent execution trigger
- `StatusBadge` - Color-coded status indicators

#### 2. Content Review (`/admin/content`)
- Browse review queue of pending content
- Run editorial pipeline on content pieces
- Approve and publish content after review
- View confidence scores and source lists

**Workflow:**
1. Click content from review queue
2. Review content preview and confidence scores
3. Click "Run Editorial Pipeline"
4. If `publish_ready = true`, click "Approve & Publish"

**Key Components:**
- `ContentReviewTable` - Review queue with confidence badges
- `ReviewActions` - Pipeline and approval actions

#### 3. Company Management (`/admin/companies`)
- View all tracked LATAM tech companies
- Filter by sector, city, country
- See company details (website, status, location)
- Stats dashboard (sectors, countries, active companies)

**Key Components:**
- `CompaniesTable` - Filterable companies list
- `StatusBadge` - Company status (active/inactive)

#### 4. Waitlist Management (`/admin/waitlist`)
- View all waitlist signups
- Export to CSV with one click
- See stats (total signups, roles, companies)
- Ordered by waitlist position

**Export Format:** CSV with columns: Email, Name, Role, Company, Position, Created At

**Key Components:**
- `WaitlistTable` - Sortable waitlist display
- `ExportButton` - Client-side CSV generation

### Components & Architecture

#### Reusable UI Components
Located in `apps/web/src/components/admin/`:

- **StatusBadge** - Color-coded status indicators (completed, running, failed, etc.)
- **EmptyState** - Placeholder for empty tables
- **AdminSidebar** - Navigation sidebar (responsive, mobile-friendly)

#### Utility Functions
Located in `apps/web/src/lib/utils.ts`:

- `formatDate(isoString)` - ISO timestamp → "DD/MM HH:mm"
- `formatDuration(start, end)` - Duration → "2m 34s" or "1h 12m"
- `truncate(text, maxLength)` - Text truncation with ellipsis
- `confidenceToDisplay(score)` - Convert 0-1 to 1-5 scale
- `confidenceToGrade(score)` - Convert 0-1 to letter grade (A-D)

#### API Integration
All admin functions in `apps/web/src/lib/api.ts`:

```typescript
// Agent Management
fetchAgentRuns(agentName?, status?, limit, offset)
fetchAgentRunDetail(runId)
triggerAgent(agentName)

// Content Review
fetchReviewQueue(limit, offset)
runEditorialPipeline(slug)
approveContent(slug, reviewerName?)

// Companies
fetchCompanies(sector?, city?, country?, limit, offset)
fetchCompanyBySlug(slug)

// Waitlist
fetchWaitlistUsers(limit, offset)
```

### Testing

**Unit Tests:** `apps/web/src/lib/__tests__/utils.test.ts`
```bash
# Run frontend tests
pnpm test:web
```

**Test Fixtures:** `apps/web/src/lib/__tests__/fixtures.ts`
- Mock agent runs, summaries, content, companies, waitlist users
- Use in integration tests and Storybook

**Manual Testing Checklist:**
- [ ] Agent runs display correctly
- [ ] Trigger agent button works (check Network tab)
- [ ] Content review queue shows items
- [ ] Editorial pipeline runs successfully
- [ ] Approve content updates status
- [ ] Waitlist CSV export downloads
- [ ] Mobile responsive (sidebar collapses)
- [ ] Loading skeletons display
- [ ] Error boundaries show on API failure

### Security

⚠️ **CRITICAL:** The admin console has **NO AUTHENTICATION** in MVP.

**Before deploying to production:**
1. Add authentication (NextAuth.js recommended)
2. Protect `/admin` route with middleware
3. Add auth checks to all admin API endpoints
4. Implement rate limiting on POST endpoints
5. Restrict CORS to trusted origins

**Endpoints exposing PII:**
- `GET /api/waitlist/list` - Exposes user emails

### API Documentation

Full API reference: [docs/admin-api.md](docs/admin-api.md)

Quick examples:
```bash
# List agent runs
curl http://localhost:8000/api/agents/runs?limit=10

# Trigger SINTESE agent
curl -X POST http://localhost:8000/api/agents/runs/sintese/trigger

# Get review queue
curl http://localhost:8000/api/editorial/queue

# Approve content
curl -X POST http://localhost:8000/api/editorial/approve/my-content-slug \
  -H "Content-Type: application/json" \
  -d '{"reviewer_name": "Admin"}'
```

### Troubleshooting

**Admin page shows empty tables:**
- Check backend is running: `curl http://localhost:8000/api/health`
- Check browser console for API errors
- Verify database has seed data: `python scripts/seed_companies.py`

**Trigger agent doesn't work:**
- Check Network tab for POST request
- Verify endpoint returns 200 status
- Note: Actual agent execution is a placeholder in MVP

**CSV export has no data:**
- Verify waitlist has entries: `curl http://localhost:8000/api/waitlist/list`
- Check browser console for JavaScript errors

---

## Deployment

### Frontend (Vercel)

```bash
# Deploy via Vercel CLI or Git integration
vercel --prod
```

Configuration in `vercel.json`. Environment variables: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`.

### Backend (Docker / Railway / Render)

```bash
# Build the API Docker image
docker build -t sinal-api -f apps/api/Dockerfile .

# Run with environment variables
docker run -p 8000:8000 --env-file .env sinal-api
```

### Scheduling Agents

See `scripts/cron.example` for production cron schedule. Agents can also be triggered via the API.

---

## Development Workflow

See [CLAUDE.md](CLAUDE.md) for full engineering preferences and workflow standards.

- **Plan Before You Code**: Every feature starts with a plan
- **TDD**: Tests written before or alongside implementation
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, etc.

---

## License

Private. All rights reserved.
