# Feed Curator Agent

LLM-powered editorial curation for the Sinal.tech real-time feed.

## Architecture

```
social_signals (DB)
       |
       v
  curator.py          Load signals, pre-filter spam, LLM curation
       |
       v
  enricher.py         Detect YouTube/Instagram/TikTok embeds, fetch og:image
       |
       v
  db_writer.py        Persist curated items (upsert by content_hash)
       |
       v
curated_feed_items (DB) --> /api/signals/feed --> /feed (frontend)
```

## Files

| File | Purpose |
|------|---------|
| `config.py` | FeedCuratorConfig (persona, skip_keywords, prompts) |
| `curator.py` | LLM curation: load signals, filter spam, parse response |
| `enricher.py` | Embed detection + og:image extraction |
| `db_writer.py` | Upsert to curated_feed_items table |
| `agent.py` | FeedCuratorAgent(BaseAgent) lifecycle |
| `main.py` | CLI entry point with --persist, --limit, --no-thumbnails |

## Persona

**Ana Torres** -- editorial curator for Sinal.tech. Selects and contextualizes
signals for founders, CTOs and VCs building technology in Latin America.
Writes in Portuguese (Brazil).

## How it works

1. `load_recent_signals()` fetches the latest 100 signals from `social_signals`
2. `pre_filter_spam()` removes signals matching `skip_keywords` (sports bets, casinos)
3. `curate_via_llm()` sends signals to Claude, requesting top N with editorial headlines
4. `_parse_llm_response()` handles JSON array, JSONL, or regex-extracted responses
5. `enrich_items()` detects video embeds in source_url and source_text, fetches og:image
6. `persist_curated_feed()` upserts results into `curated_feed_items`

## Running

```bash
# Dry run (preview only)
python -m apps.agents.feed_curator.main --limit 50 --output-limit 15

# Persist to database
python -m apps.agents.feed_curator.main --persist

# Skip thumbnail fetching (faster)
python -m apps.agents.feed_curator.main --persist --no-thumbnails
```

## Tests

```bash
pytest apps/agents/feed_curator/tests/ -v
# 175 tests, 90% coverage
```
