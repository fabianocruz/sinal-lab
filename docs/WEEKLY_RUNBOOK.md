# Weekly Newsletter Runbook

The recurring ritual to assemble, review, and publish a `Sinal Semanal #N` edition.
All operations go through `scripts/weekly.py`. Each step is idempotent and can
be re-run.

State lives in `content_pieces` (review_status, metadata). There is no parallel
JSON or filesystem state.

## Usage

All commands take `--edition N` (the edition number) and an optional `--week W`
(ISO week number; auto-detected from sintese metadata if omitted).

```bash
# Quick reference
python scripts/weekly.py status --edition 57
python scripts/weekly.py qa --edition 57
python scripts/weekly.py qa --edition 57 --review   # LLM editorial review
```

## The ritual (in order)

### 1. Prepare a fresh slate (if regenerating an existing edition)
```bash
python scripts/weekly.py prepare --edition 57
```
Deletes pieces and agent runs for the edition. Refuses if any are already
`published` — pass `--force` to override. Skip this step the first time you
build an edition.

### 2. Generate the agent outputs
```bash
python scripts/weekly.py generate --edition 57
```
Runs (in order): `funding → mercado → codigo → radar → sintese`. Each agent
runs in `--orchestrate` mode, which means editorial review is part of the
pipeline. `sintese` aggregates highlights from the others, so it goes last.

If a single agent fails the editorial review or has a bug, generation stops
there. Fix and re-run with `--only <agent>`:
```bash
python scripts/weekly.py generate --edition 57 --only mercado sintese
```

### 3. Run rule-based QA
```bash
python scripts/weekly.py qa --edition 57
```
Catches detectable issues:
- Subject missing edition number, too long, or duplicated prefix
- Pieces marked published without a hero_image
- Hero image is a known agent-placeholder URL (Bloomberg, InfoQ, etc)
- "Para founders/CTOs/fundadores" formula appearing >3 times in one piece
- Pieces published with editorial grade C or below
- Sintese with too few (<12) or too many (>20) items
- Duplicate URLs within a single piece
- Items in this edition's sintese that already appeared in edition N-1

Returns 0 if no errors, 1 if any. Warnings always pass.

### 4. (Optional) LLM editorial review
```bash
python scripts/weekly.py qa --edition 57 --review
```
Calls Claude Opus with the full body of each piece + context from edition
N-1. Catches subjective issues that rules miss: weak section leads,
self-promotion, items that feel like filler, follow-ups dressed as news,
title or subject suggestions.

Costs ~$0.10 and ~30s per call. Run once before publishing.

### 4b. (Optional) Targeted LLM suggestions
When QA review flags something specific, ask Claude for proposals:

```bash
# Propose 3 alternative titles for the sintese
python scripts/weekly.py suggest-title --edition 57

# Propose 3 alternative email subjects (with character counts)
python scripts/weekly.py suggest-subject --edition 57

# Identify items that are weak fits and worth cutting (uses prior-edition context)
python scripts/weekly.py suggest-removals --edition 57

# Rewrite a single blockquote, varying the opening hook
python scripts/weekly.py rewrite-hook --piece radar-week-19 --item 5
```

Each is ~$0.05 and ~10s. They print options and never modify the DB —
apply with `set-title` / `set-subject` / `remove-item` if you like what
you see. `rewrite-hook` is read-only; copy the chosen option manually.

### 5. Edit individual pieces
Manual fixes that come out of QA review.

```bash
# Remove an editorial item (renumbers remaining items, drops from metadata)
python scripts/weekly.py remove-item --edition 57 --piece sinal-semanal-57 --item 5

# Update sintese title (visible at /newsletter/sinal-semanal-57)
python scripts/weekly.py set-title --edition 57 --title "..."

# Update email subject (used by Resend broadcast)
python scripts/weekly.py set-subject --edition 57 --subject "Sinal Semanal #57: ..."

# Despublish a piece (e.g. INDEX shouldn't be in the edition)
python scripts/weekly.py despublish --edition 57 --piece index-week-19
```

### 6. Generate cover images
```bash
python scripts/weekly.py covers --edition 57
```
Wraps `scripts/generate_covers.py`. Generates 3 variations per piece, saves
all to Vercel Blob, sets v1 as default in `metadata.hero_image`. To switch
to a different variation, edit the URL in metadata directly.

### 7. Publish locally
```bash
python scripts/weekly.py publish-local --edition 57
```
Moves any `approved` pieces to `published` and stamps `published_at`.
Required for the pieces to appear in the public listing at `/newsletter`
and for the email broadcast template to find them.

### 8. Send a preview email
```bash
python scripts/weekly.py preview --edition 57 --to fabianoc@gmail.com
```
Sends a single transactional email via Resend (not a broadcast). Uses the
same template as production. Iterate until layout, subject, and content all
look right.

### 9. Sync to prod
The local DB and prod DB are separate. Once you're happy locally, copy the
edition's pieces over.

```bash
python scripts/weekly.py sync-prod --edition 57            # dry-run preview
python scripts/weekly.py sync-prod --edition 57 --execute  # actually run
```
Currently this command prints instructions and you run `sync_local_to_prod.py`
manually after updating its `SLUGS_TO_SYNC` for the new edition. (Future
work: have the command patch the slug list automatically.)

### 10. Broadcast
```bash
# Register highlights first (one-time per edition):
#  - INTELLIGENCE_REPORTS in scripts/publish_newsletter.py (if a new report)
#  - ARTICLE_HIGHLIGHTS[57] in scripts/publish_newsletter.py (if a new article)

# Then:
python scripts/weekly.py broadcast --edition 57 \
  --intelligence https://sinal.tech/intelligence/<slug> \
  --article https://sinal.tech/artigos/<slug>
```
This wraps `publish_newsletter.py broadcast`, which prompts you to type
`ENVIAR` before actually sending. Action is irreversible (~333 subscribers).

## Common situations

### "I already generated and published, but I want to fix one item"
You don't need to regenerate. Use `remove-item`, `set-title`, `set-subject`
directly — the changes hit `body_md` and metadata, and the next preview
email will reflect them.

### "An item from the prior edition is showing up in this one (post-holiday)"
QA `--review` will flag this. The fix is editorial: rewrite the lead of the
affected piece to acknowledge it as a follow-up, not as breaking news. Use
`remove-item` only if the item really shouldn't be there.

### "Cover image looks like a placeholder (Bloomberg/InfoQ)"
QA flags this. Run `covers` again — `generate_covers.py` only regenerates
pieces without a `hero_image`. To force regeneration, clear the field first
with a manual SQL update, then re-run.

### "I need to retry a single agent without losing the others"
```bash
python scripts/weekly.py generate --edition 57 --only mercado
```
The single-agent run will overwrite that one piece in the DB.

### "I want to skip editorial review for a quick test"
```bash
python scripts/weekly.py generate --edition 57 --no-editorial
```
Don't ship this — bypasses `pesquisa`/`validacao`/`vies`/`seo`/`guidelines`/
`sintese_final` layers.

## What this CLI does not do

- Doesn't pick the editorial line. You decide the title, the subject,
  which items get cut, which Intelligence report and Article are featured.
- Doesn't run vozes/pulso/feed_curator. Those run on the production cron
  service (`sinal-collector`), independent of weekly editions.
- Doesn't deploy code. Use `git push` for that.
