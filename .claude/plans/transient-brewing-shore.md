# Plan: MERCADO Editorial Redesign + Cover Generation

## Context

MERCADO produces 3,281 chars with 0 links from 1,292 collected profiles. SINTESE produces 18,955 chars with 28 links from ~560 items. The gap: MERCADO uses 2 LLM calls for aggregate stats; SINTESE uses 5-6 calls with per-section editorial rewrites. Additionally, FUNDING and MERCADO have no hero images because their data types lack image_url fields.

**Goal:** Transform MERCADO output from thin data summary into editorial-quality market report (~12-15k chars, 15+ links, sectored analysis). Then generate AI covers for all agents missing hero images.

---

## Part 1: MERCADO Editorial Redesign

### Strategy: Mirror SINTESE's section-based pattern

SINTESE pattern: select top 18 items → group by category → LLM writes intro + per-item summaries → each item linked with source attribution.

MERCADO adaptation: select top ~15 profiles (with city/sector diversity) → group by sector → LLM writes sector analysis + per-profile descriptions → each profile linked with website/GitHub.

### Changes

#### `apps/agents/mercado/synthesizer.py` — Rewrite

Replace single-pass template with section-based synthesis (mirror SINTESE's `synthesize_newsletter`):

```python
# New constants
TOP_PROFILES_COUNT = 15          # vs SINTESE's 18
MAX_PER_SECTOR = 5               # diversity cap
MAX_PER_CITY = 4                 # diversity cap

# New dataclass
@dataclass
class SectorSection:
    heading: str
    profiles: list[ScoredCompanyProfile]

# New functions:
def select_top_profiles(scored, count=15) -> list[ScoredCompanyProfile]
    # Like SINTESE's select_top_items but with sector/city diversity caps
    # Ensures no single city or sector dominates

def group_by_sector(profiles) -> list[SectorSection]
    # Like SINTESE's group_by_category
    # Groups into sector sections, sorted by size

def format_profile_markdown(scored, index, description_override=None) -> str
    # Like SINTESE's format_item_markdown
    # Links to website, shows city, tech stack, GitHub
    # Uses LLM description if available, else truncated original

def synthesize_ecosystem_snapshot(scored_profiles, week_number, writer=None) -> str
    # Restructured:
    # 1. select_top_profiles(scored_profiles)
    # 2. group_by_sector(top_profiles)
    # 3. For each section: writer.write_sector_analysis(section) → intro + per-profile descriptions
    # 4. Aggregate stats section at bottom (city map, total counts)
    # 5. Footer
```

**Key design decisions:**
- Top 15 profiles get full editorial treatment (vs current 3)
- Remaining 1,277 still appear in aggregate stats at bottom
- Each profile gets: linked name (website), LLM description, metadata bullets
- ~4-5 LLM calls total (intro + 1 per sector section) — affordable and impactful

#### `apps/agents/mercado/writer.py` — Add sector analysis method

```python
def write_sector_analysis(
    self,
    section: "SectorSection",
    aggregate_context: str,
) -> Optional["SectorContent"]
    # New method — 1 API call per sector
    # Returns SectorContent dataclass with:
    #   - intro: str (2-3 sentences about the sector in LATAM)
    #   - descriptions: list[str] (one per profile, 2-3 sentences each)
    # Similar to SINTESE's write_section_content()
```

New dataclass in writer.py:
```python
@dataclass
class SectorContent:
    intro: str
    descriptions: list[str]  # one per profile in the section
```

#### `apps/agents/mercado/agent.py` — Update output() method

- Expand `metadata["items"]` from top 10 to top 15 profiles
- Add hero_image extraction: loop top 15 profiles, check for `website` field, build hero dict from first profile with a website (as a reference link, not an image — since profiles don't have images)
- Actually: since profiles don't have image_url, rely on generate_covers.py for hero (Part 2)

### Expected Output Structure

```markdown
# Ecossistema LATAM — Semana 10/2026

*Relatório de 05/03/2026 — Curado por Valentina Rojas (MERCADO)*

---

[LLM intro: 3-5 sentences about this week's discoveries, citing numbers]

---

## Fintech (8 startups mapeadas)

[LLM sector intro: 2-3 sentences about fintech in LATAM this week]

**1. [Company Name](https://website.com)**
*São Paulo, Brasil — Fintech*
> [LLM description: 2-3 sentences about why this company matters]
- **Tech Stack**: Python, React, PostgreSQL
- **GitHub**: https://github.com/company

**2. [Company Name](https://website.com)**
...

## DevTools (5 startups mapeadas)
...

---

## Panorama do Ecossistema

[Aggregate stats: city distribution, sector counts, total profiles]
```

### Tests — `apps/agents/mercado/tests/test_synthesizer.py`

Update/expand existing tests:
- `test_select_top_profiles_diversity` — sector/city caps work
- `test_group_by_sector` — groups correctly, sorted by size
- `test_format_profile_markdown` — linked name, metadata, description override
- `test_synthesize_with_writer` — sections get LLM content
- `test_synthesize_without_writer` — template fallback still works
- `test_synthesize_empty` — empty input handled

### Tests — `apps/agents/mercado/tests/test_writer.py`

Add test for new method:
- `test_write_sector_analysis` — returns SectorContent with intro + descriptions
- `test_write_sector_analysis_unavailable` — returns None when LLM unavailable
- `test_write_sector_analysis_parse_error` — handles bad JSON gracefully

---

## Part 2: Generate Covers

The `scripts/generate_covers.py` pipeline already exists and works:
1. Finds published content without `hero_image` in metadata
2. Generates AI cover via Recraft V3 API
3. Applies brand overlay (agent color bar, DQ badge, gradient)
4. Uploads to Vercel Blob
5. Updates metadata in DB

**Action:** Simply run the script after publishing content:

```bash
python3 scripts/generate_covers.py --verbose
```

This will generate covers for all 5 new content pieces (SINTESE, RADAR, CODIGO, FUNDING, MERCADO).

**Required env vars:** `DATABASE_URL`, `RECRAFT_API_KEY`, `BLOB_READ_WRITE_TOKEN`

No code changes needed for Part 2.

---

## Implementation Order

1. **Branch:** `fix/mercado-editorial-output`
2. **Step 1:** Write tests for new functions (TDD per CLAUDE.md)
3. **Step 2:** Implement `SectorSection` dataclass + `SectorContent` dataclass
4. **Step 3:** Implement `select_top_profiles()`, `group_by_sector()`, `format_profile_markdown()`
5. **Step 4:** Implement `write_sector_analysis()` in writer.py
6. **Step 5:** Restructure `synthesize_ecosystem_snapshot()` to use sections
7. **Step 6:** Update `agent.py` output() to pass expanded metadata
8. **Step 7:** Run all tests, verify
9. **Step 8:** Run MERCADO agent locally to validate output quality
10. **Step 9:** Run `generate_covers.py` to add AI covers

## Files Modified

| File | Change |
|------|--------|
| `apps/agents/mercado/synthesizer.py` | Rewrite: section-based synthesis |
| `apps/agents/mercado/writer.py` | Add `SectorContent`, `write_sector_analysis()` |
| `apps/agents/mercado/agent.py` | Update metadata items count |
| `apps/agents/mercado/tests/test_synthesizer.py` | New/updated tests |
| `apps/agents/mercado/tests/test_writer.py` | New tests for sector analysis |

## Estimated Scope

| Component | Production LOC | Test LOC |
|-----------|---------------|----------|
| synthesizer.py (rewrite) | ~120 | ~100 |
| writer.py (new method) | ~60 | ~50 |
| agent.py (metadata update) | ~5 | — |
| **Total** | **~185** | **~150** |

## Verification

```bash
# Tests
pytest apps/agents/mercado/tests/ -v

# Full test suite
pytest apps/ packages/ -v

# Local run
python3 scripts/run_agents.py mercado --persist --verbose

# Verify output
python3 -c "
import psycopg2, os
from dotenv import load_dotenv; load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT slug, length(body_md), title FROM content_pieces WHERE slug='mercado-week-10'\")
r = cur.fetchone(); print(f'{r[0]}: {r[1]} chars | {r[2]}')
"

# Generate covers
python3 scripts/generate_covers.py --verbose
```
