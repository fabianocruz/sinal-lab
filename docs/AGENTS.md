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

- **`apps/agents/base/llm.py`** — `LLMClient` (Anthropic Claude API) + `strip_code_fences()` utility
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
DEALROOM_API_KEY=your_api_key_here
CRUNCHBASE_API_KEY=your_api_key_here
```

### Cron Schedule

```bash
# crontab -e
# Subprocess mode (each agent in its own process)
0 7 * * 1 cd /app && python scripts/run_agents.py funding --persist
0 7 * * 3 cd /app && python scripts/run_agents.py mercado --persist

# Orchestrate mode (in-process with editorial review)
0 7 * * 1 cd /app && python scripts/run_agents.py all --week $(date +%V) --orchestrate
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

**SINTESE** (34 total, 29 enabled): 5 feeds disabled (startse HTML, contxto SSL, netlify 404, fintechfutures 403, a16z 404). Vercel feed updated from `/blog/rss.xml` to `/atom` with `max_items=20`.

**FUNDING** (15 total, 8 enabled): 12 original VC feeds broken (404s, SSL errors, HTML responses). Added 5 cross-validated news sources from SINTESE (crunchbase_news, techcrunch_latam, latamlist, abstartups, blocknews). 3 original feeds healthy (kaszek, neofeed, startupi).

**MERCADO** (6 total, 5 enabled): GitHub API sources switched from `/search/repositories` to `/search/users` (the `location:` qualifier only works on user/org profiles, not repositories). Dealroom API remains disabled pending API key.

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

**Exemplo de referência**: [apps/agents/sintese](../apps/agents/sintese/) — Agente SINTESE completo
