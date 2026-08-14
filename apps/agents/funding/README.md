# FUNDING Agent — Capital Flow Tracker

Weekly tracker of funding rounds involving LATAM startups. Data agent: it indexes
every round it can find, with no editorial filter (the editorial pipeline applies
that later).

## Extraction Strategy

Historically FUNDING recognised a round only when the RSS **title** matched a rigid
`Company raises $XM Series Y` regex. Almost no real headline is written that way, so
23 configured sources produced ~0-1 usable events per week and 205/207 real rows in
`funding_rounds` came from the manual Crunchbase dump instead of the live collector.

Each collected item now goes through three steps (`funding/collector.py`):

| Step | Function | Cost | Notes |
|------|----------|------|-------|
| 1. Title regex | `extract_funding_from_title` | free | High precision, low recall. Unchanged. |
| 2. Keyword pre-filter | `looks_like_funding_news` | free | Multilingual (pt/en/es). Gates step 3 so unrelated tech news never costs money. |
| 3. LLM extraction | `LLMFundingExtractor.extract` | ~1 call/item | Only for items that passed step 2, capped at `DEFAULT_LLM_EXTRACTION_BUDGET` (40) calls per run. |

The LLM returns strict JSON (`is_funding_event`, `company_name`, `amount`, `currency`,
`round_type`, `investors`). Events are dropped when the model rejects the item, when
the payload is unparseable, or when the fields are too incomplete to be useful
(minimum: company + amount, or company + a known round type). Every failure mode
degrades to `None` — one bad item never aborts a run.

Measured on the `latamlist` feed (2026-08-13): 10 entries → 6 passed the pre-filter →
5 LLM calls → **6 events** (1 regex + 5 LLM), versus 1 event before.

## Source Types

| Type | Handler | Sources |
|------|---------|---------|
| `rss` | `fetch_feed` | VC blogs, LATAM tech press, Google News queries |
| `html` | `fetch_html_source` → `sources.web_scraper.scrape_article_listing` | VC blogs that dropped their feeds (Canary, Maya Capital, Valor Capital, monashees) |
| `api` | `fetch_grok_source`, Crunchbase, SEC Form D | Live search + deals APIs + regulatory cross-check |
| database | `_load_from_funding_rounds_table` | Rows pre-collected by the 24/7 `collect_funding.py` daemon |

### HTML fallback

`scrape_article_listing` fetches a blog index, keeps same-domain links whose last path
segment looks like a post slug (`why-we-invested-in-nexu`), derives a title from the
slug when the anchor text is a generic "Read more", and pairs `<time>` elements with
links by proximity. Extracted posts then run through the same regex → pre-filter → LLM
extraction as RSS items.

### Grok Live Search

`sources/grok_search.py` calls xAI's `POST /v1/responses` with the server-side
`web_search` tool (model `grok-4.3`) and asks for LATAM rounds from the last 7 days in
strict JSON. Source URLs come from the model, falling back to the response's
`url_citation` annotations. Gated on `XAI_API_KEY`; missing key, network errors, HTTP
errors and unparseable answers all return an empty list.

Live run (2026-08-13): 3 events (Plinq seed $254K, FAZ Cred $14.8M, Yuno Series B $45M)
with 64 citations in a single ~90s call.

## Provenance

Two levels are tracked:

- `ProvenanceTracker` records the transport used (`rss`, `scraper`, `api`, `database`),
  constrained by the platform-wide vocabulary in `base/provenance.py`.
- `FundingEvent.extraction_method` records how the *fields* were obtained:
  `rss_regex`, `llm_fallback`, `api`, `database`, `grok_live_search`.

## Amount Conventions

`amount_usd` holds two legacy formats in the same field:

- Title-regex extraction stores **millions** (`15.0` = $15M).
- LLM, API, Grok and database rows store **absolute** values (`15_000_000` = $15M).

`synthesizer.normalize_amount_usd` treats anything below 1000 as millions, so both
round-trip correctly. **Always normalize before comparing or summing amounts** — the
report used to classify a $1.2M LLM round as a "Series A+ ($5M+)" round precisely
because a raw comparison was used.

## Tests

```bash
pytest apps/agents/funding/tests/ -v
pytest apps/agents/sources/tests/test_grok_search.py \
       apps/agents/sources/tests/test_funding_normalize.py \
       apps/agents/sources/tests/test_web_scraper.py -v
```
