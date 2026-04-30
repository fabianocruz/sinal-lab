# Archived scripts

One-shot scripts that already ran in production and are kept here for
historical reference. They are **not** part of any active workflow and
are not invoked by the codebase or the cron service.

If you need to reuse one of these (e.g. another data backfill of the
same shape), copy it back to `scripts/` and adjust before running.

| Script | Purpose | Last relevant date |
|---|---|---|
| `count_companies.py` | Quick check of production company data | 2026-02-24 |
| `export_companies.py` | Export active companies from local to JSON for prod import | 2026-02-24 |
| `fix_countries.py` | Normalize country names in production DB to canonical Portuguese | 2026-02-24 |
| `regenerate_sintese_callouts.py` | Regenerate editorial callouts for a published SINTESE edition | 2026-04-21 |
| `enrich_seed_markdown.py` | One-time migration: enrich plain-text seed articles with Markdown | 2026-02-21 |
| `cleanup_polymarket_spam.py` | One-time cleanup: delete irrelevant Polymarket signals | 2026-04-04 |
| `fix_signal_clusters.py` | Retroactive fix for signal_clusters data quality | 2026-04-12 |
| `ingest_companies_manual.py` | One-off ingest of manually curated LATAM tech companies | 2026-04-21 |
| `import_companies.py` | Import companies from JSON into prod (batch upsert by slug) | 2026-02-24 |
| `import_resend_contacts.py` | Import Resend audience contacts into the database | 2026-03-17 |
| `import_seed_accounts.py` | Import seed list of monitored accounts from curated Excel | 2026-04-04 |
| `import_crunchbase_accounts.py` | Import monitored accounts from Crunchbase CSV exports | 2026-04-04 |

Archived on 2026-04-30 as part of `scripts/` cleanup. No tests reference
these files, no application code imports them.
