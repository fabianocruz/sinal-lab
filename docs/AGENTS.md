# AI Agents — Development Guide

Este documento define padrões e guidelines para desenvolvimento de AI agents na plataforma Sinal.lab.

---

## Classificação de Agentes

Os agents da plataforma se dividem em três categorias com escopos distintos:

### Agents de Dados (cobertura ampla — todo o ecossistema LATAM)

Coletam, normalizam e indexam dados sobre **todas** as startups e empresas de tecnologia da América Latina, independente da linha editorial. São a base de dados da plataforma.

| Agent | Função | Escopo |
|-------|--------|--------|
| **FUNDING** | Capital Flow Tracker | Todas as rodadas de investimento LATAM |
| **MERCADO** | Market Intelligence | Inteligência de mercado do ecossistema completo |
| **INDEX** *(planned)* | Startup Ranking | Ranking abrangente de startups LATAM |

### Agents de Conteúdo (filtrados pela linha editorial)

Produzem análises e conteúdo direcionado ao público-alvo da plataforma: fundadores técnicos, CTOs e engenheiros seniores. Operam dentro do recorte editorial definido em [EDITORIAL.md](EDITORIAL.md).

| Agent | Função | Escopo |
|-------|--------|--------|
| **SINTESE** | Newsletter Synthesizer | Sintetiza conteúdo para a audiência técnica |
| **RADAR** | Trend Intelligence | Tendências relevantes para o público técnico |
| **CÓDIGO** | Code & Infra Research | Pesquisa sobre tecnologia e infraestrutura |

### Pipeline de Qualidade

Agents transversais que garantem qualidade antes da publicação.

| Agent | Função | Escopo |
|-------|--------|--------|
| **EDITORIAL** | Editorial Pipeline | Filtra e adapta outputs dos agents de dados para publicação, aplicando o recorte editorial |
| **SEO ENGINE** *(planned)* | SEO Optimization | Otimização de páginas programáticas para busca |

### Relação entre categorias

```
┌─────────────────────────────────────────────────────┐
│           AGENTS DE DADOS (escopo amplo)             │
│         FUNDING · MERCADO · INDEX                    │
│     Cobertura: todas as startups LATAM               │
└──────────────────────┬──────────────────────────────┘
                       │ dados brutos
                       ▼
┌─────────────────────────────────────────────────────┐
│          PIPELINE DE QUALIDADE                       │
│              EDITORIAL                               │
│     Filtra pelo recorte editorial +                  │
│     valida qualidade + confidence scoring            │
└──────────────────────┬──────────────────────────────┘
                       │ conteúdo validado
                       ▼
┌─────────────────────────────────────────────────────┐
│        AGENTS DE CONTEÚDO (escopo editorial)         │
│       SINTESE · RADAR · CÓDIGO                       │
│     Produzem para: fundadores técnicos,              │
│     CTOs, engenheiros seniores                       │
└──────────────────────┬──────────────────────────────┘
                       │ conteúdo final
                       ▼
┌─────────────────────────────────────────────────────┐
│              SEO ENGINE                              │
│     Otimiza e distribui para publicação              │
└─────────────────────────────────────────────────────┘
```

**Princípio fundamental:** Os agents de dados alimentam a base completa do ecossistema LATAM. O pipeline editorial decide o que vira conteúdo publicado para a audiência-alvo.

---

## Arquitetura de Agentes

### Lifecycle: collect → process → score → output

Todos os agentes seguem o mesmo ciclo de vida de 4 fases:

```python
class MyAgent(BaseAgent):
    def collect(self) -> list[Any]:
        """Gather raw data from configured sources."""
        ...

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Transform, classify, and filter collected data."""
        ...

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Compute confidence scores for processed data."""
        ...

    def output(self, processed_data: list[Any], scores: list[ConfidenceScore]) -> AgentOutput:
        """Format results into publishable content."""
        ...
```

### Estrutura de Diretórios (OBRIGATÓRIA)

```
apps/agents/{agent_name}/
├── __init__.py          # Exports main agent class
├── config.py            # Data sources, parameters, scheduling
├── collector.py         # Data collection from sources
├── processor.py         # Processing workflow (normalize, dedupe, etc.)
├── scorer.py            # Confidence scoring logic
├── synthesizer.py       # Content formatting (Markdown/HTML)
├── writer.py            # LLM editorial writer (optional, uses base/llm.py)
├── db_writer.py         # Database persistence (optional)
├── agent.py             # Main agent class (inherits BaseAgent)
├── main.py              # CLI entry point
└── tests/
    ├── __init__.py
    ├── test_collector.py
    ├── test_processor.py
    ├── test_scorer.py
    ├── test_synthesizer.py
    ├── test_writer.py    # LLM writer tests (if applicable)
    ├── test_agent.py     # End-to-end agent tests
    └── test_db_writer.py # Database tests (if applicable)
```

---

## LLM Editorial Writer Layer

All agents support an optional LLM-powered editorial writer (`writer.py`) that generates contextualized content using the shared `LLMClient` in `apps/agents/base/llm.py`. When `ANTHROPIC_API_KEY` is set, writers produce editorial commentary; when absent, synthesizers fall back to template-based output.

### Shared Infrastructure

- **`apps/agents/base/llm.py`** — `LLMClient` (Anthropic Claude API) + shared utilities:
  - `strip_code_fences()` — removes ````json ... ```` wrappers from LLM JSON output
  - `strip_html()` — strips HTML tags, decodes entities (`&#8230;` → `…`, `&amp;` → `&`), collapses whitespace, optionally truncates
- Model: `claude-sonnet-4-5-20250929`, temperature 0.7
- All writers import from `base/llm.py` — no direct SDK usage in agent modules

### Writer Patterns

| Agent | Pattern | API Calls | Methods |
|-------|---------|-----------|---------|
| **SINTESE** | sections → items | 1 intro + N sections | `write_newsletter_intro()`, `write_section_content()` |
| **RADAR** | sections → items | 1 intro + N sections | `write_report_intro()`, `write_section_content()` |
| **CODIGO** | sections → items | 1 intro + N sections | `write_report_intro()`, `write_section_content()` |
| **FUNDING** | aggregate + highlights | 2 total | `write_report_intro()`, `write_deal_highlights()` |
| **MERCADO** | aggregate + highlights | 2 total | `write_snapshot_intro()`, `write_highlight_descriptions()` |

**Content agents** (SINTESE, RADAR, CODIGO) use per-section rewriting with `SectionContent(intro, summaries)`.
**Data agents** (FUNDING, MERCADO) use aggregate narratives + top-N highlight descriptions (too many items for per-section calls).

### Adding a Writer to a New Agent

1. Create `writer.py` with agent-specific `SYSTEM_PROMPT` and writer class
2. Add `writer: Optional["AgentWriter"] = None` parameter to the synthesizer function
3. Try LLM first, fall back to existing template on `None` return
4. Instantiate writer in `agent.py` and pass to synthesizer
5. All writer methods must return `Optional` — never raise on failure

### Graceful Degradation

Every LLM call returns `Optional`. Synthesizers check `writer.is_available` before calling and handle `None` returns. No agent breaks without `ANTHROPIC_API_KEY`.

### Editorial Copy Guidelines

All writer `SYSTEM_PROMPT`s enforce:

- **Language:** PT-BR obrigatório (`"Escreva SEMPRE em portugues brasileiro"`)
- **Anti-AI tells:** Evitar frases típicas de IA (`"vale ressaltar"`, `"neste contexto"`, `"é importante destacar"`, `"no cenário atual"`)
- **Specificity:** Números e exemplos concretos > afirmações vagas

Synthesizer templates (fallback sem LLM) também usam nomes de categorias e labels em PT-BR.

**Contexto editorial:** O arquivo [`.claude/product-marketing-context.md`](../.claude/product-marketing-context.md) define audiência, tom de voz, regras de copy e territórios editoriais. É consultado automaticamente pelo skill de copywriting e serve como referência para todos os writers. Derivado de [`docs/EDITORIAL.md`](EDITORIAL.md).

---

## Data Quality Pipeline

Collector-level data quality improvements that run before scoring and synthesis.

### FUNDING — Deduplication and Note Cleaning

**Deduplication by (company, round):** `FundingEvent.content_hash` uses `compute_composite_hash(company_name.lower().strip(), round_type)` — intentionally excludes `source_url` so the same deal from different RSS sources (e.g., startupi.com.br + latamlist.com) is deduplicated. First-seen source wins.

**RSS boilerplate stripping:** `clean_rss_notes()` in `funding/collector.py` removes common RSS boilerplate patterns before storing notes:
- English: `"The post {title} appeared first on {site}."`
- Portuguese: `"O post {title} apareceu primeiro em {site}."`

**HTML entity decoding:** `strip_html()` in `base/llm.py` decodes HTML entities (`&#8230;` → `…`, `&amp;` → `&`) in addition to stripping HTML tags. Applied to all RSS summaries and notes in synthesizers.

### MERCADO — Organization Filtering, Classification, and Enrichment

#### Startup Filter (`mercado/collector.py`)

`is_likely_startup()` filters GitHub organizations using a two-mechanism approach:

**1. Exact-login blocklist** (`_KNOWN_NON_STARTUP_LOGINS` frozenset): For short or ambiguous names where substring matching would cause false positives.
- Large companies: `vtex`, `vtex-apps`, `globocom`, `globo`, `wizeline`, `mercadolibre`, `mercadolivre`, `totvs`
- Academic groups: `udistrital`, `uspgamedev`, `thesoftwaredesignlab`, `capitulojaverianoacm`, `thunderatz`
- Nonprofits/orgs: `bireme`, `hacklabr`, `openingdesign`
- Personal: `geosaber`

**2. Categorized substring patterns** (8 categories, ~60 patterns total):

| Category | Examples | Rationale |
|----------|----------|-----------|
| `_GOVT_PATTERNS` | prefeitura, gobierno, ministerio | Government orgs |
| `_UNIVERSITY_PATTERNS` | universid, faculdade, fatec, fiap, puc-, unam, unicamp | Universities and faculties |
| `_EDUCATION_PATTERNS` | escola, school, curso, alura, platzi, bootcamp | Training/education platforms |
| `_ACADEMIC_PATTERNS` | -lab, research-, capitulo, -acm, gamedev | Research labs and student chapters |
| `_NONPROFIT_PATTERNS` | bireme, paho, -ngo, fundacion | NGOs and international orgs |
| `_PERSONAL_PATTERNS` | -eti, consulting, consultoria | Freelancers and consultants |
| `_KNOWN_LARGE_COMPANIES` | globo, wizeline, mercadolibre, totvs, embraer | Established companies, not startups |
| `_ARCHIVE_PATTERNS` | archive, mirror, backup | Mirror/archive repos |

Matching is case-insensitive against `login + description`. The exact-login check runs first (O(1) frozenset lookup), then substring patterns.

**False-positive safety:** Legitimate startups like `nubank`, `stone`, `entria`, `creditas`, `cloudwalk`, `nuvemshop`, `loft` are verified to pass the filter.

#### Sector Classifier (`mercado/classifier.py`)

**14 sectors** with weighted keyword matching:

| Sector | Example Keywords |
|--------|-----------------|
| Fintech | payment, credit, pix, neobank, crypto, blockchain, checkout |
| HealthTech | saude, health, telemedicine, hospital, pharma |
| Edtech | educacao, learning, escola, curso, student |
| E-commerce | marketplace, loja, varejo, shop, inventory, fulfillment |
| SaaS | saas, enterprise, crm, erp, b2b, dashboard, workflow |
| Logistics | logistica, delivery, transporte, frete, shipping |
| Agritech | agricultura, agro, farm, crop, plantio |
| PropTech | imovel, real estate, property, aluguel, housing |
| DevTools | developer, devops, ci/cd, sdk, open-source, kubernetes, terraform |
| Cybersecurity | security, segurança, cyber, encryption, fraud |
| CleanTech | solar, renewable, energia, sustentavel, carbono, climate |
| HRTech | recruiting, talent, hiring, payroll, workforce |
| InsurTech | seguro, insurance, insurtech, sinistro |
| LegalTech | juridico, legal, contrato, compliance, lawtech |

**Weighted matching** uses three text sources with different weights:
- Description match: **1.0** per keyword (most reliable)
- Tags match: **0.7** per keyword (from Crunchbase/LinkedIn categories)
- Name/slug match: **0.5** per keyword (less reliable for short names)

The highest-scoring sector wins. This ensures an org with a strong description match is not overridden by a weaker name-only match.

#### GitHub Org Enrichment (`mercado/enricher.py`)

`enrich_from_github_org()` calls the GitHub `/orgs/{login}` API for each profile, enriching:

| API Field | Profile Field | Logic |
|-----------|--------------|-------|
| `blog` | `website` | Only if profile has no website; auto-prepends `https://` |
| `description` | `description` | Only if API description is longer than existing |
| `name` | `name` | Only if different from login |
| `created_at` | `founded_date` | Parsed as `date.fromisoformat()` |
| `public_repos` | `tags` | Added as `repos:N` tag |

**Rate limiting:** 0.1s sleep between org API calls. With ~120 orgs/run, stays well within GitHub's 5000 req/hour (authenticated) limit.

**Auth:** Uses `GITHUB_TOKEN` env var if set (5000 req/hour). Without it, falls back to unauthenticated (60 req/hour) — will hit rate limits on typical runs.

**Pipeline order:** Enricher runs before classifier in `agent.py`, so richer descriptions from the org API feed directly into sector classification.

#### Other MERCADO Patterns

**Display name formatting:** `_format_display_name()` converts GitHub logins to title-cased names (`stone-payments` → `Stone Payments`). The raw login is preserved as `slug`.

**Realistic distribution:** GitHub search `per_page` set to 30 (not 100) to avoid artificial uniform counts across cities.

---

## Padrões Obrigatórios

### 1. Type Hints

**OBRIGATÓRIO** em todas as funções públicas e métodos:

```python
# ✅ CORRETO
def normalize_currency(event: FundingEvent) -> FundingEvent:
    """Convert local currency to USD."""
    ...

def collect_all_sources(
    sources: list[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str,
    run_id: str,
) -> list[FundingEvent]:
    """Collect from all sources."""
    ...

# ❌ INCORRETO
def normalize_currency(event):
    ...
```

### 2. Docstrings

**OBRIGATÓRIO** em:
- Todas as classes
- Todas as funções públicas
- Todos os métodos públicos

**Formato**:
```python
def function_name(arg1: Type1, arg2: Type2) -> ReturnType:
    """Short one-line summary (ends with period).

    Longer description if needed. Explain what the function does,
    not how it does it. Focus on the "why" and "what".

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When X happens
        KeyError: When Y is missing
    """
    ...
```

### 3. Logging Estruturado

**NUNCA** usar `print()`. **SEMPRE** usar `logging`:

```python
import logging

logger = logging.getLogger(__name__)

# ✅ CORRETO
logger.info("Collected %d events from %s", len(events), source.name)
logger.warning("Currency %s not supported, skipping", currency)
logger.error("Failed to fetch feed %s: %s", source.name, error, exc_info=True)

# ❌ INCORRETO
print(f"Collected {len(events)} events")
```

### 4. Confidence Scoring

**OBRIGATÓRIO** incluir confidence score em todos os outputs:

- **Data Quality (DQ)**: 0-1 scale, quão bons são os dados?
  - Source count, verification, freshness
- **Analysis Confidence (AC)**: 0-1 scale, quão confiante é a análise?
  - Methodology, cross-validation

```python
from apps.agents.base.confidence import ConfidenceScore, compute_confidence

confidence = compute_confidence(
    source_count=3,
    sources_verified=2,
    data_freshness_days=1,
)
# Returns: ConfidenceScore(dq=0.8, ac=0.75, grade="A")
```

**Grades**:
- A: 0.8-1.0 (Very high confidence)
- B: 0.6-0.8 (High confidence)
- C: 0.4-0.6 (Medium confidence)
- D: 0.0-0.4 (Low confidence)

### 5. Provenance Tracking

**OBRIGATÓRIO** rastrear proveniência de **TODOS** os dados:

```python
from apps.agents.base.provenance import ProvenanceTracker

provenance = ProvenanceTracker()

# Para cada data point coletado
provenance.add_record(
    source_url="https://source.com/article",
    source_name="source_rss",
    extraction_method="rss",
    agent_name="funding",
    run_id=self.run_id,
)

# No output
sources = provenance.get_source_urls()[:20]  # Top 20 sources
summary = provenance.summary()  # Stats
```

### 6. Error Handling

**SEMPRE** fazer error handling explícito:

```python
# ✅ CORRETO
try:
    response = httpx.get(url, timeout=15.0)
    response.raise_for_status()
except httpx.TimeoutException:
    logger.error("Timeout fetching %s", url)
    return []
except httpx.HTTPError as e:
    logger.error("HTTP error fetching %s: %s", url, e)
    return []
except Exception as e:
    logger.error("Unexpected error: %s", e, exc_info=True)
    return []

# ❌ INCORRETO
response = httpx.get(url)  # Can crash entire agent
```

### 7. Testes

**Mínimo de 80% de cobertura** por agente.

**Obrigatório testar**:
- ✅ Happy path (dados válidos)
- ✅ Edge cases (empty lists, None values, missing fields)
- ✅ Error cases (network failures, invalid data, database errors)
- ✅ Integration (full agent run end-to-end)

```python
# apps/agents/{name}/tests/test_collector.py
def test_collect_valid_feed():
    """Test collecting from valid RSS feed."""
    ...

def test_collect_empty_feed():
    """Test handling empty feed."""
    ...

def test_collect_network_error():
    """Test handling network timeout."""
    ...
```

---

## Data Sources

### Tipos Suportados

1. **RSS/Atom feeds** (`source_type="rss"`)
   - Use `feedparser`
   - Timeout: 15s
   - Handle `bozo` (malformed XML)

2. **REST APIs** (`source_type="api"`)
   - Use `httpx` (async)
   - Rate limiting via `rate_limit_per_minute`
   - API key via `api_key_env` (environment variable)

3. **Web scraping** (`source_type="scraper"`)
   - Use `BeautifulSoup4`
   - Respect robots.txt
   - Rate limit: max 10 req/min per domain

4. **File-based** (`source_type="file"`)
   - CSV, JSON, local files

### Configuração

```python
from apps.agents.base.config import AgentConfig, DataSourceConfig

SOURCES = [
    DataSourceConfig(
        name="example_rss",
        source_type="rss",
        url="https://example.com/feed",
        enabled=True,
    ),
    DataSourceConfig(
        name="example_api",
        source_type="api",
        url="https://api.example.com/data",
        api_key_env="EXAMPLE_API_KEY",
        rate_limit_per_minute=60,
        enabled=False,  # Enable when API key available
        params={"filter": "latam", "limit": 100},
    ),
]

AGENT_CONFIG = AgentConfig(
    agent_name="my_agent",
    version="0.1.0",
    description="Short description",
    data_sources=SOURCES,
    schedule_cron="0 7 * * 1",  # Every Monday 7am UTC
    output_content_type="DATA_REPORT",
    min_confidence_to_publish=0.4,
    max_items_per_run=500,
)
```

### Shared Source Modules (`apps/agents/sources/`)

Reusable data source modules shared across multiple agents. Each module follows the same pattern: dataclass(es) + fetch function(s) + graceful degradation when credentials are missing.

All modules return `[]` on error (no exceptions propagate to callers). Cross-source deduplication is supported via `content_hash` on every dataclass.

#### Google News RSS (`google_news.py`)

| | |
|---|---|
| **Endpoint** | `https://news.google.com/rss/search?q=...` |
| **Auth** | None |
| **Rate Limits** | No official limit (practical: ~100 req/hour) |
| **Agents** | SINTESE (`gnews_fintech_br`, `gnews_ai_latam`, `gnews_venture_br`), RADAR (`gnews_tech_trends_br`, `gnews_tech_trends_latam`), FUNDING (`gnews_funding_br`, `gnews_funding_latam`) |
| **Dataclass** | Reuses `RSSItem` from `rss.py` |
| **Tests** | 24 tests in `test_google_news.py` |

Key functions:
- `build_google_news_url(query, language, country, time_range)` — constructs RSS URL with regional ceid mapping
- `build_google_news_sources(queries, prefix)` — convenience for config files
- `fetch_google_news(source, client)` — builds URL from `source.params`, delegates to `fetch_rss_feed()`

#### Google Trends (`google_trends.py`)

| | |
|---|---|
| **Library** | `pytrends` (unofficial, no API key) |
| **Auth** | None |
| **Rate Limits** | Subject to Google throttling (exponential backoff recommended) |
| **Agents** | RADAR (`gtrends_br_trending`, `gtrends_related_ai`), MERCADO (`gtrends_latam_tech`) |
| **Dataclass** | `GoogleTrendItem` (keyword, trend_type, region, traffic_value) |
| **Tests** | 25 tests in `test_google_trends.py` |

Key functions:
- `fetch_trending_searches(source, region)` — today's trending searches via `pytrends.trending_searches()`
- `fetch_related_queries(source, keywords, region)` — rising/top queries for seed keywords (max 5 per API call)

**Fallback:** degrades gracefully if `pytrends` is not installed.

#### LinkedIn via RapidAPI (`linkedin.py`)

| | |
|---|---|
| **Endpoint** | `https://linkedin-data-api.p.rapidapi.com/search-posts` and `/search-companies` |
| **Auth** | `RAPIDAPI_KEY` env var (free tier: ~100-500 calls/month) |
| **Rate Limits** | Varies by RapidAPI provider |
| **Agents** | SINTESE (`linkedin_fintech_posts`, `linkedin_ai_posts` — disabled by default), MERCADO (`linkedin_latam_companies` — disabled by default) |
| **Dataclasses** | `LinkedInPost` (title, text, engagement metrics, external_url), `LinkedInCompany` (name, industry, headquarters, website) |
| **Tests** | 31 tests in `test_linkedin.py` |

Key functions:
- `fetch_linkedin_posts(source, client, query, limit)` — search posts with engagement data
- `fetch_linkedin_companies(source, client, query, limit)` — search company profiles

**Classification: EXPERIMENTAL.** Sources are `enabled=False` by default. Provider URL is stored in `DataSourceConfig.url` — switching providers requires only URL/params changes.

**Cross-source dedup:** `LinkedInPost.content_hash` uses `external_url` when present, so the same article shared on LinkedIn, HN, and Google News deduplicates.

#### Reddit API (`reddit.py`)

| | |
|---|---|
| **Endpoint** | `https://oauth.reddit.com/r/{subreddit}/{sort}` |
| **Auth** | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` (OAuth2 client_credentials) |
| **Rate Limits** | 100 req/min (free tier) |
| **Agents** | SINTESE (`reddit_brdev`, `reddit_startups`), RADAR (`reddit_programming`, `reddit_machinelearning`), CODIGO (`reddit_devops`, `reddit_webdev`) |
| **Dataclass** | `RedditPost` (title, url, subreddit, score, num_comments, selftext) |
| **Tests** | 25 tests in `test_reddit.py` |

Key functions:
- `authenticate_reddit(client)` — OAuth2 client_credentials token exchange
- `fetch_subreddit_posts(source, client, subreddit, sort, time_filter, limit)` — fetch subreddit listings

**Cross-source dedup:** link posts hash the external URL; self posts hash the permalink.

#### Bluesky AT Protocol (`bluesky.py`)

| | |
|---|---|
| **Endpoint** | `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts` |
| **Auth** | None (public API) |
| **Rate Limits** | No official limit for public search |
| **Agents** | SINTESE (`bluesky_fintech`, `bluesky_ai`), RADAR (`bluesky_tech_trends`) |
| **Dataclass** | `BlueskyPost` (text, url, author_handle, external_url, engagement metrics) |
| **Tests** | 29 tests in `test_bluesky.py` |

Key functions:
- `build_post_url(handle, rkey)` — construct bsky.app permalink
- `parse_bluesky_post(raw_post, source_name)` — parse AT Protocol post object
- `fetch_bluesky_search(source, client, query, limit)` — search posts

**Cross-source dedup:** hashes `external_url` from `app.bsky.embed.external` when present.

#### ProductHunt GraphQL (`producthunt.py`)

| | |
|---|---|
| **Endpoint** | `https://api.producthunt.com/v2/api/graphql` |
| **Auth** | `PRODUCTHUNT_TOKEN` env var (Bearer token from OAuth2) |
| **Rate Limits** | 450 req/15min (free tier) |
| **Agents** | RADAR (`producthunt_daily`), CODIGO (`producthunt_tools`) |
| **Dataclass** | `ProductHuntPost` (name, tagline, website, topics, makers, votes, comments) |
| **Tests** | 23 tests in `test_producthunt.py` |

Key functions:
- `fetch_producthunt_posts(source, client, limit, posted_after)` — GraphQL query with Relay-style pagination

**Cross-source dedup:** hashes `website` URL when present (same product on HN/GitHub deduplicates).

#### Crunchbase Basic API (`crunchbase.py`)

| | |
|---|---|
| **Endpoint** | `https://api.crunchbase.com/api/v4/searches/funding_rounds` and `/searches/organizations` |
| **Auth** | `CRUNCHBASE_API_KEY` env var (`X-cb-user-key` header) |
| **Rate Limits** | 200 req/day (free tier) |
| **Agents** | FUNDING (`crunchbase_funding_latam`), MERCADO (`crunchbase_companies_latam`) |
| **Dataclasses** | `CrunchbaseFundingRound` (company, round_type, amount, investors), `CrunchbaseCompany` (name, permalink, categories, funding_total) |
| **Tests** | 31 tests in `test_crunchbase.py` |

Key functions:
- `fetch_funding_rounds(source, client, locations, limit)` — search funding rounds by location
- `fetch_companies(source, client, locations, categories, limit)` — search company profiles

**Cross-source dedup:** `CrunchbaseFundingRound.content_hash` uses `company_name-round_type` (compatible with FUNDING agent's `FundingEvent` dedup).

#### Environment Variables Summary

| Variable | Source | Required |
|---|---|---|
| — | Google News RSS | No credentials needed |
| — | Google Trends (pytrends) | No credentials needed |
| `RAPIDAPI_KEY` | LinkedIn (RapidAPI) | Optional (sources disabled by default) |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | Reddit API | Optional |
| — | Bluesky (AT Protocol) | No credentials needed |
| `PRODUCTHUNT_TOKEN` | ProductHunt GraphQL | Optional |
| `CRUNCHBASE_API_KEY` | Crunchbase Basic API | Optional |

All agents produce valid output without any API keys. Sources degrade independently — a missing key skips only that source.

#### Test Coverage (188 tests across 7 modules)

```
apps/agents/sources/tests/
├── test_google_news.py      # 24 tests
├── test_google_trends.py    # 25 tests
├── test_linkedin.py         # 31 tests
├── test_reddit.py           # 25 tests
├── test_bluesky.py          # 29 tests
├── test_producthunt.py      # 23 tests
└── test_crunchbase.py       # 31 tests
```

Run all source tests: `pytest apps/agents/sources/tests/ -v`

---

## Output Format

### AgentOutput

Todos os agentes devem retornar `AgentOutput`:

```python
from apps.agents.base.output import AgentOutput

return AgentOutput(
    title="Report Title",
    body_md="# Markdown content\n\n...",
    agent_name=self.agent_name,
    run_id=self.run_id,
    confidence=aggregate_confidence,
    sources=source_urls[:20],
    content_type="DATA_REPORT",  # ou "ANALYSIS"
    summary="Brief summary of the report",
)
```

### Markdown com YAML Frontmatter

```markdown
---
title: "Report Title"
agent: funding
run_id: "funding-20260216-070015-a3f4b2"
generated_at: "2026-02-16T07:00:15Z"
content_type: DATA_REPORT
confidence_dq: 0.75
confidence_ac: 0.68
confidence_grade: B
source_count: 12
sources:
  - "https://source1.com/..."
  - "https://source2.com/..."
---

# Report Content

[Markdown body...]
```

---

## Runtime Layer (Phase 2)

A infraestrutura de runtime compartilhada que elimina duplicação entre agents.

### Shared CLI (`apps/agents/base/cli.py`)

Cada agent `main.py` delega para `run_agent_cli()`, reduzindo ~100 linhas de
boilerplate para ~10-25 linhas:

```python
from apps.agents.base.cli import run_agent_cli
from apps.agents.myagent.agent import MyAgent

def main():
    run_agent_cli(
        agent_class=MyAgent,
        description="MY_AGENT — Description",
        default_output_dir="apps/agents/myagent/output",
        slug_fn=lambda agent, args: f"myagent-week-{args.week}",
        filename_fn=lambda agent, args: f"myagent-week-{args.week}.md",
        post_run_fn=my_post_run,        # Optional: domain-specific post-processing
        extra_args_fn=my_extra_args,     # Optional: add agent-specific CLI args
    )
```

Argumentos padrão incluídos automaticamente: `--week/--edition`, `--output`, `--dry-run`, `--persist`, `--verbose`.

### Shared Persistence (`apps/agents/base/persistence.py`)

Três funções para persistir resultados de agents no banco:

| Função | Commit? | Uso |
|--------|---------|-----|
| `persist_agent_run(session, agent, result)` | NÃO | Cria AgentRun record |
| `persist_content_piece(session, result, slug)` | NÃO | Cria/atualiza ContentPiece por slug |
| `persist_agent_output(session, agent, result, slug)` | SIM | Convenience: ambos + commit/rollback |

As funções low-level (sem commit) são usadas pelo orchestrator para transações atômicas.

### Evidence Writer (`apps/agents/base/evidence_writer.py`)

Persiste dados brutos como evidence items para cross-referência entre agents:

```python
from apps.agents.base.evidence_writer import persist_raw_items

stats = persist_raw_items(session, agent._collected_data,
                          agent_name="funding", collector_run_id=agent.run_id)
# Returns: {"inserted": 5, "updated": 2, "skipped": 1}
```

Usa upsert por `content_hash` — confidence mais alta vence.

### Orchestrator (`apps/agents/base/orchestrator.py`)

Conecta todo o pipeline: agent → editorial → persist → evidence.

```python
from apps.agents.base.orchestrator import orchestrate_agent_run

result = orchestrate_agent_run(
    agent, session=session, slug="radar-week-8",
    enable_editorial=True,      # Run editorial pipeline
    enable_evidence=True,       # Persist raw items as evidence
    persist=True,               # Write AgentRun + ContentPiece
    domain_persist_fn=my_fn,    # Optional domain-specific writes
)
# result.editorial_result.publish_ready → True/False
# result.persisted → True/False
# result.evidence_stats → {"inserted": N, ...}
```

**Transação atômica:** todas as escritas (AgentRun, ContentPiece, evidence,
domain) acontecem em um único `session.commit()`. Se qualquer etapa falhar,
`session.rollback()` desfaz tudo.

**Editorial-in-the-loop:** o pipeline editorial classifica o output e define
`review_status="approved"` (publica automaticamente) ou `"pending_review"`
(requer revisão humana). Falhas no editorial defaultam para revisão humana.

---

## CLI Entry Point (main.py)

### Usando o Shared CLI

```python
# apps/agents/myagent/main.py (10-25 linhas)
from apps.agents.base.cli import run_agent_cli
from apps.agents.myagent.agent import MyAgent

def main():
    run_agent_cli(
        agent_class=MyAgent,
        description="MY_AGENT — Description",
        default_output_dir="apps/agents/myagent/output",
        slug_fn=lambda agent, args: f"myagent-week-{args.week}",
    )

if __name__ == "__main__":
    main()
```

### Argumentos Padrão (automáticos via shared CLI)

- `--week N` / `--edition N`: Período do report
- `--output PATH`: Caminho para salvar Markdown
- `--dry-run`: Roda sem salvar
- `--persist`: Salva AgentRun + ContentPiece no banco
- `--verbose`: Logging DEBUG

### Integração com run_agents.py

Adicionar ao `AGENTS` dict em `scripts/run_agents.py`:

```python
AGENTS = {
    # ...
    "my_agent": {
        "module": "apps.agents.my_agent.main",
        "description": "Short description",
        "class_module": "apps.agents.my_agent.agent",
        "class_name": "MyAgent",
        "period_arg": "week",
        "slug_pattern": "myagent-week-{period}",
    },
}
```

### Modos de Execução via run_agents.py

**Subprocess mode (default):** cada agent roda em processo separado.
```bash
python scripts/run_agents.py radar --week 8 --persist
python scripts/run_agents.py all --persist --dry-run
```

**Orchestrate mode:** agents rodam in-process com editorial review e evidence persistence.
```bash
python scripts/run_agents.py radar --week 8 --orchestrate
python scripts/run_agents.py all --week 8 --orchestrate --no-editorial
python scripts/run_agents.py funding --week 8 --orchestrate --no-evidence
```

| Flag | Descrição |
|------|-----------|
| `--orchestrate` | Ativa modo in-process com editorial pipeline |
| `--no-editorial` | Pula revisão editorial (só orchestrate) |
| `--no-evidence` | Pula persistência de evidence items (só orchestrate) |
| `--publish` | Envia newsletter unificada via Resend Broadcasts após todos os agents completarem |

### Newsletter Publisher (`scripts/publish_newsletter.py`)

Combina outputs dos 5 agents num único newsletter e envia via Resend Broadcasts.

**Estrutura do newsletter composto:**
1. **SINTESE** — lead editorial (corpo completo)
2. **RADAR** — "Tendências da Semana"
3. **CODIGO** — "Código & Infraestrutura"
4. **FUNDING** — "Investimentos"
5. **MERCADO** — "Ecossistema LATAM"

Agents sem output são silenciosamente omitidos.

**Uso standalone:**
```bash
# Compor + enviar via Resend Broadcasts
python scripts/publish_newsletter.py --edition 8 --week 8

# Compor + salvar HTML apenas (sem publicar)
python scripts/publish_newsletter.py --edition 8 --week 8 --html output.html --dry-run
```

**Uso integrado com run_agents.py:**
```bash
# Rodar todos os agents + publicar newsletter automaticamente
python scripts/run_agents.py all --week 8 --edition 8 --output --publish
```

O publisher reutiliza `markdown_to_html()`, `wrap_in_email_template()` e `send_broadcast()` de `apps/agents/sintese/newsletter.py`. Requer `RESEND_API_KEY` e `RESEND_AUDIENCE_ID` no `.env`.

**Testes:** 15 tests em `scripts/tests/test_publish_newsletter.py` (YAML parser, composição, HTML output, broadcast mock).

---

## Database Persistence

### Upsert Pattern

```python
from sqlalchemy.orm import Session

def upsert_record(session: Session, data: MyData, confidence: float) -> MyModel:
    """Insert or update record based on confidence."""
    # Check if exists by unique key
    existing = session.query(MyModel).filter_by(
        unique_field_1=data.field1,
        unique_field_2=data.field2,
    ).first()

    if existing:
        # Update only if new confidence > old
        if confidence > existing.confidence:
            existing.field_x = data.field_x
            existing.confidence = confidence
            session.commit()
            return existing
        else:
            # Skip update, existing is better
            return existing
    else:
        # Insert new record
        record = MyModel(
            id=uuid4(),
            field_x=data.field_x,
            confidence=confidence,
        )
        session.add(record)
        session.commit()
        return record
```

### Transaction Management

```python
try:
    # Multiple DB operations
    session.add(record1)
    session.add(record2)
    session.commit()
    logger.info("Persisted %d records", 2)
except Exception as e:
    session.rollback()
    logger.error("Failed to persist: %s", e)
    raise
finally:
    session.close()
```

---

## Testing Guidelines

### Estrutura de Testes

```python
# test_my_module.py
import pytest
from unittest.mock import Mock, patch

def test_happy_path():
    """Test with valid data."""
    result = my_function(valid_input)
    assert result == expected_output

def test_edge_case_empty():
    """Test with empty input."""
    result = my_function([])
    assert result == []

def test_edge_case_none():
    """Test with None values."""
    result = my_function(None)
    assert result is None

@patch('httpx.get')
def test_network_error(mock_get):
    """Test handling network error."""
    mock_get.side_effect = httpx.TimeoutException()
    result = my_function()
    assert result == []
```

### Fixtures

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    """Test database session."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def mock_feed_entry():
    """Mock feedparser entry."""
    class MockEntry:
        title = "Test Title"
        link = "https://test.com"
        summary = "Test summary"
    return MockEntry()
```

### Coverage

```bash
# Run tests with coverage
pytest apps/agents/my_agent/tests/ --cov=apps/agents/my_agent --cov-report=term-missing

# Minimum 80% coverage required
```

---

## Performance Guidelines

1. **Rate Limiting**: Respect `rate_limit_per_minute` from config
2. **Timeouts**: Always set timeouts (default 15s for HTTP)
3. **Async quando possível**: Use `httpx` async client para múltiplas requests
4. **Batch processing**: Process em chunks de 100-500 items
5. **Memory**: Evitar carregar todos os dados em memória (use generators)

---

## Security

1. **API Keys**: NUNCA hardcode, sempre via environment variables
2. **SQL Injection**: Sempre usar SQLAlchemy ORM (nunca raw SQL)
3. **XSS**: Sanitize user input antes de renderizar HTML
4. **Secrets**: Nunca commit `.env` ou credenciais no git
5. **Rate Limiting**: Implementar em endpoints públicos

---

## Deployment

### Environment Variables

```bash
# .env (NEVER commit this file)
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Data source API keys (all optional — agents degrade gracefully)
X_BEARER_TOKEN=            # X/Twitter App-Only Bearer Token
PRODUCTHUNT_TOKEN=         # ProductHunt OAuth2 Bearer Token
REDDIT_CLIENT_ID=          # Reddit OAuth2 App ID
REDDIT_CLIENT_SECRET=      # Reddit OAuth2 App Secret
CRUNCHBASE_API_KEY=        # Crunchbase Basic API key
RAPIDAPI_KEY=              # LinkedIn RapidAPI key (experimental)
GITHUB_TOKEN=              # GitHub Personal Access Token (optional, higher rate limits)
DEALROOM_API_KEY=          # Dealroom API key (disabled source)

# LLM (optional — agents fall back to template output)
ANTHROPIC_API_KEY=

# Newsletter publishing via Resend (optional — publisher skips if not set)
RESEND_API_KEY=
RESEND_AUDIENCE_ID=
```

### Cron Schedule

```bash
# crontab -e
# Subprocess mode (each agent in its own process)
0 7 * * 1 cd /app && python scripts/run_agents.py funding --persist
0 7 * * 3 cd /app && python scripts/run_agents.py mercado --persist

# Orchestrate mode (in-process with editorial review)
0 7 * * 1 cd /app && python scripts/run_agents.py all --week $(date +%V) --orchestrate

# Full pipeline: run all agents + send newsletter via Resend Broadcasts
0 7 * * 1 cd /app && python scripts/run_agents.py all --week $(date +%V) --edition $(date +%V) --output --publish
```

---

## Data Source Health

### Feed Audit Process

All RSS/Atom and API data sources should be periodically validated. Common failure modes:

| Failure | Action |
|---------|--------|
| **404 / DNS error** | Disable (`enabled=False`) with comment |
| **SSL error** | Disable — often a server misconfiguration |
| **Returns HTML, not RSS** | Disable — site removed its feed |
| **Empty feed (0 entries)** | Disable — feed exists but is abandoned |
| **403 Forbidden** | Disable — site blocks automated access |
| **Unbounded entries** | Set `max_items` to cap results |

### Current Status (Feb 2026)

**SINTESE** (34+ RSS, +5 API sources): 5 RSS feeds disabled (startse HTML, contxto SSL, netlify 404, fintechfutures 403, a16z 404). Vercel feed updated from `/blog/rss.xml` to `/atom` with `max_items=20`. Added: Google News (3 queries), LinkedIn posts (2 queries, disabled), Reddit (brdev, startups), Bluesky (fintech, ai).

**RADAR** (20+ sources): RSS feeds + GitHub + Google Trends. Added: Google News (2 queries), Google Trends pytrends (trending + related), Reddit (programming, MachineLearning), Bluesky (tech_trends), ProductHunt GraphQL (daily).

**CODIGO** (10+ sources): RSS feeds + GitHub trending. Added: Reddit (devops, webdev), ProductHunt (tools).

**FUNDING** (15+ total, 8+ enabled): 12 original VC feeds broken (404s, SSL errors, HTML responses). Added 5 cross-validated news sources from SINTESE. Added: Google News (2 funding queries), Crunchbase API (funding rounds LATAM).

**MERCADO** (6+ total, 5+ enabled): GitHub API sources switched from `/search/repositories` to `/search/users`. Dealroom API remains disabled. Added: Google Trends (latam_tech), LinkedIn companies (disabled), Crunchbase API (companies LATAM).

### `max_items` Field

`DataSourceConfig.max_items` caps the number of entries parsed from a feed. Useful for feeds that return their full archive (e.g., Vercel Atom returns 1300+ entries). Set to `None` (default) for no limit.

---

## Checklist para Novo Agente

Antes de considerar um agente "completo":

- [ ] Estrutura de diretórios correta (9 arquivos mínimos)
- [ ] Type hints em todas as funções públicas
- [ ] Docstrings em todas as classes e funções públicas
- [ ] Logging estruturado (sem `print()`)
- [ ] Confidence scoring implementado
- [ ] Provenance tracking para todos os dados
- [ ] Error handling explícito
- [ ] Testes com 80%+ coverage
- [ ] Testes de edge cases (empty, None, errors)
- [ ] CLI entry point funcional
- [ ] Integrado em `scripts/run_agents.py`
- [ ] Documentação atualizada em `docs/blueprint.md`
- [ ] README ou guia de uso no diretório do agente

---

## Referências

### Core
- [BaseAgent](../apps/agents/base/base_agent.py) — Classe base
- [ConfidenceScore](../apps/agents/base/confidence.py) — Sistema de confiança
- [ProvenanceTracker](../apps/agents/base/provenance.py) — Rastreamento de fontes
- [AgentOutput](../apps/agents/base/output.py) — Formato de saída

### Runtime Layer (Phase 2)
- [run_agent_cli](../apps/agents/base/cli.py) — Shared CLI entry point
- [persistence](../apps/agents/base/persistence.py) — Shared DB persistence
- [evidence_writer](../apps/agents/base/evidence_writer.py) — Evidence item writer
- [orchestrator](../apps/agents/base/orchestrator.py) — Editorial-in-the-loop orchestrator
- [run_agents.py](../scripts/run_agents.py) — Unified agent runner (subprocess + orchestrate)
- [publish_newsletter.py](../scripts/publish_newsletter.py) — Newsletter publisher (compose + Resend Broadcasts)

### Shared Data Sources (Phase 3)
- [google_news](../apps/agents/sources/google_news.py) — Google News RSS
- [google_trends](../apps/agents/sources/google_trends.py) — Google Trends (pytrends)
- [linkedin](../apps/agents/sources/linkedin.py) — LinkedIn via RapidAPI (experimental)
- [reddit](../apps/agents/sources/reddit.py) — Reddit API (OAuth2)
- [bluesky](../apps/agents/sources/bluesky.py) — Bluesky AT Protocol
- [producthunt](../apps/agents/sources/producthunt.py) — ProductHunt GraphQL API
- [crunchbase](../apps/agents/sources/crunchbase.py) — Crunchbase Basic API

**Exemplo de referência**: [apps/agents/sintese](../apps/agents/sintese/) — Agente SINTESE completo
