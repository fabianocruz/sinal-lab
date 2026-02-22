# INDEX Agent — LATAM Startup Index

Comprehensive registry of LATAM tech startups built from multiple bulk data sources.

## What it does

Discovers, deduplicates, and indexes startups from 5+ independent sources into a unified `Company` table. Cross-source entity matching ensures the same company isn't counted twice, even when names differ across sources (e.g., "NU PAGAMENTOS S.A." from Receita Federal vs "Nubank" from Crunchbase).

## Data Sources

| Source | Type | Confidence | What it provides |
|--------|------|------------|------------------|
| Receita Federal | CSV file | 0.9 | CNPJ, razao social, CNAE codes, city/state |
| ABStartups | API | 0.7 | Name, sector, website, business model |
| YC Portfolio | API | 0.85 | Name, batch, vertical, website |
| GitHub Orgs | API | 0.6 | Org name, repos, contributors, languages |
| Crunchbase Open | CSV file | 0.8 | Name, domain, categories, funding, founded date |

## Entity Matching

Priority cascade (first match wins):

1. **CNPJ exact** (confidence 1.0) — Brazilian tax ID, definitively correct
2. **Domain exact** (confidence 0.95) — After normalizing www prefix and protocol
3. **Crunchbase permalink** (confidence 0.9) — Unique identifier
4. **Fuzzy name + same city** (confidence ~0.72) — SequenceMatcher threshold 0.85

## Usage

```bash
# Preview collection + dedup stats (no persistence)
python -m apps.agents.index.main --dry-run

# API-only sources (no file downloads needed)
python -m apps.agents.index.main --api-only --dry-run

# Full run with Receita Federal CSV
python -m apps.agents.index.main --rf-file /path/to/estabelecimentos.csv --persist

# One-time bulk seed (alternative entry point)
python scripts/seed_index.py --api-only --dry-run
```

## Pipeline

```
Source Collectors → CandidateCompany → match_batch() → MergedCompany → score → persist
```

1. **Collect** — Fetch from all enabled sources in parallel
2. **Convert** — Normalize each source format into `CandidateCompany`
3. **Match** — Deduplicate using CNPJ/domain/name cascade + intra-batch index
4. **Merge** — Combine fields from multiple sources per company (prefer higher-confidence)
5. **Score** — Composite: source_count (40%) + field completeness (35%) + avg confidence (25%)
6. **Persist** — Upsert to `companies` + register `company_external_ids`

## Schedule

Runs every **Saturday** via `run_cron.py`.

## Tests

```bash
python3 -m pytest apps/agents/index/tests/ -v          # 82 tests
python3 -m pytest apps/agents/sources/tests/ -v         # 78 source tests
```
