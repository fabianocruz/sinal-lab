"""Import & enrich companies from Crunchbase CSV export.

Usage:
    python scripts/import_crunchbase_csv.py --csv /path/to/file.csv --dry-run
    python scripts/import_crunchbase_csv.py --csv /path/to/file.csv

Actions:
  1. INSERT new companies not already in the DB (matched by slug).
  2. ENRICH existing companies — fill empty fields (description, sector, tags, city)
     and bump source_count. Never overwrites non-empty fields.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import os
import unicodedata
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.database.session import SessionLocal
from packages.database.models.company import Company

BATCH_SIZE = 100

# ---------------------------------------------------------------------------
# Sector mapping: Crunchbase Industry keywords → platform sector
# Order matters — first match wins.
# ---------------------------------------------------------------------------
SECTOR_MAP = [
    # Fintech (broadest — must come after more specific sub-categories)
    ({"FinTech", "Financial Services", "Payments", "Banking", "Credit",
      "Lending", "Credit Cards", "Mobile Payments", "Insurance", "InsurTech",
      "Wealth Management", "Asset Management", "Cryptocurrency", "Blockchain",
      "Debit Cards", "Foreign Exchange Trading", "Trading Platform"}, "Fintech"),
    # AI/ML
    ({"Artificial Intelligence (AI)", "Machine Learning", "Natural Language Processing",
      "Computer Vision", "Predictive Analytics", "Generative AI", "Agentic AI"}, "AI/ML"),
    # SaaS
    ({"SaaS", "PaaS", "Enterprise Software", "Developer Platform",
      "Developer Tools", "Cloud Computing"}, "SaaS"),
    # Healthtech
    ({"Health Care", "Medical", "Telehealth", "mHealth", "Health Insurance",
      "Health Diagnostics", "Pharmaceutical", "Biopharma", "Mental Health",
      "Electronic Health Record (EHR)", "Therapeutics", "Oncology"}, "Healthtech"),
    # Edtech
    ({"EdTech", "Education", "E-Learning", "Higher Education",
      "Training", "Language Learning"}, "Edtech"),
    # Logistics
    ({"Logistics", "Freight Service", "Supply Chain Management",
      "Last Mile Transportation", "Shipping", "Fleet Management",
      "Warehousing", "Transportation"}, "Logistics"),
    # Agritech
    ({"AgTech", "Agriculture", "Farming", "Aquaculture"}, "Agritech"),
    # E-commerce
    ({"E-Commerce", "E-Commerce Platforms", "Marketplace",
      "Retail Technology", "Retail"}, "E-commerce"),
    # Proptech
    ({"PropTech", "Real Estate", "Real Estate Investment",
      "Property Management", "Commercial Real Estate"}, "Proptech"),
    # HR Tech
    ({"Human Resources", "Recruiting", "Staffing Agency",
      "Employee Benefits", "Skill Assessment"}, "HR Tech"),
    # Cleantech / Energy
    ({"Clean Energy", "CleanTech", "GreenTech", "Renewable Energy", "Solar",
      "Energy", "Energy Storage", "Electric Vehicle", "Sustainability",
      "Biomass Energy", "Wind Energy"}, "Cleantech"),
    # Biotech
    ({"Biotechnology", "Bioinformatics", "Biopharma"}, "Biotech"),
    # Cybersecurity
    ({"Cyber Security", "Cloud Security", "Network Security",
      "Identity Management", "Security"}, "Cybersecurity"),
    # Consumer
    ({"Consumer Goods", "Consumer", "Food and Beverage", "Food Delivery",
      "Grocery", "Beauty", "Fashion", "Pet", "Restaurants"}, "Consumer"),
    # Industrials
    ({"Mining", "Mining Technology", "Manufacturing", "Industrial",
      "Construction", "Oil and Gas", "Aerospace"}, "Industrials"),
    # Telecom
    ({"Telecommunications", "Internet", "Mobile"}, "Telecom"),
    # Legal Tech
    ({"Legal Tech", "Legal"}, "Legal Tech"),
    # Government
    ({"GovTech", "Government"}, "Government"),
]


def slugify(text: str) -> str:
    """Generate a URL-safe slug from company name."""
    # Normalize unicode (e.g. ã → a)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def parse_location(raw: str) -> tuple[str, str, str]:
    """Parse 'City, State, Country' from Crunchbase location string.

    Returns (city, state, country).
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[-1]
    if len(parts) == 2:
        return parts[0], "", parts[1]
    if len(parts) == 1:
        return "", "", parts[0]
    return "", "", ""


COUNTRY_NORMALIZE = {
    "Brazil": "Brazil",
    "Mexico": "Mexico",
    "Colombia": "Colombia",
    "Argentina": "Argentina",
    "Chile": "Chile",
    "Peru": "Peru",
    "Venezuela": "Venezuela",
    "Uruguay": "Uruguay",
    "Paraguay": "Paraguay",
    "Ecuador": "Ecuador",
    "Bolivia": "Bolivia",
    "Costa Rica": "Costa Rica",
    "Panama": "Panama",
}


def parse_industries(raw: str) -> list[str]:
    """Split Crunchbase comma-separated industries into a clean list."""
    if not raw:
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def map_sector(industries: list[str]) -> str | None:
    """Map Crunchbase industries list to a single platform sector."""
    industry_set = set(industries)
    for keywords, sector in SECTOR_MAP:
        if industry_set & keywords:
            return sector
    return None


def parse_cb_rank(raw: str) -> int | None:
    """Parse CB Rank string (may have commas like '1,305') to int."""
    if not raw:
        return None
    try:
        return int(raw.replace(",", "").strip())
    except ValueError:
        return None


def run(csv_path: str, dry_run: bool = False):
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"CSV loaded: {len(rows)} companies from {csv_path}")

    db = SessionLocal()

    # Load existing slugs + company objects for enrichment
    existing_companies = {c.slug: c for c in db.query(Company).all()}
    existing_slugs = set(existing_companies.keys())
    # Also build simplified name → slug lookup for fuzzy dedup
    simple_to_slug: dict[str, str] = {}
    for slug, c in existing_companies.items():
        simple = re.sub(r"[^a-z0-9]", "", c.name.lower())
        simple_to_slug[simple] = slug

    print(f"Existing DB: {len(existing_slugs)} companies\n")

    to_insert: list[Company] = []
    enriched = 0
    skipped = 0
    slug_counter: dict[str, int] = {}  # handle duplicate slugs within CSV

    for row in rows:
        name = row.get("Organization Name", "").strip()
        if not name:
            continue

        slug = slugify(name)
        simple_name = re.sub(r"[^a-z0-9]", "", name.lower())

        # Parse fields from CSV
        industries = parse_industries(row.get("Industries", ""))
        sector = map_sector(industries)
        city, state, country = parse_location(row.get("Headquarters Location", ""))
        country = COUNTRY_NORMALIZE.get(country, country)
        description = row.get("Description", "").strip() or None
        cb_rank = parse_cb_rank(row.get("CB Rank (Company)", ""))
        cb_url = row.get("Organization Name URL", "").strip() or None

        # --- Check if company already exists (exact slug or fuzzy name) ---
        matched_slug = None
        if slug in existing_slugs:
            matched_slug = slug
        elif simple_name in simple_to_slug:
            matched_slug = simple_to_slug[simple_name]

        if matched_slug and matched_slug in existing_companies:
            # ENRICH existing company
            company = existing_companies[matched_slug]
            changed = False

            if description and not company.description:
                company.description = description
                changed = True
            if description and not company.short_description and len(description) <= 500:
                company.short_description = description
                changed = True
            if sector and not company.sector:
                company.sector = sector
                changed = True
            if industries and not company.tags:
                company.tags = industries
                changed = True
            if city and not company.city:
                company.city = city
                changed = True
            if state and not company.state:
                company.state = state
                changed = True

            # Always add crunchbase metadata if not present
            meta = company.metadata_ or {}
            if cb_url and "crunchbase_url" not in meta:
                meta["crunchbase_url"] = cb_url
                changed = True
            if cb_rank and "cb_rank" not in meta:
                meta["cb_rank"] = cb_rank
                changed = True
            if changed:
                company.metadata_ = meta
                # Bump source_count for cross-source verification
                company.source_count = (company.source_count or 1) + 1
                enriched += 1
            else:
                skipped += 1
            continue

        # --- New company: prepare for insert ---
        # Deduplicate slug within this CSV batch
        if slug in slug_counter:
            slug_counter[slug] += 1
            slug = f"{slug}-{slug_counter[slug]}"
        else:
            slug_counter[slug] = 0

        # Final check slug doesn't collide with DB
        if slug in existing_slugs:
            slug = f"{slug}-cb"

        to_insert.append(Company(
            name=name,
            slug=slug,
            description=description,
            short_description=description[:500] if description and len(description) <= 500 else None,
            sector=sector,
            tags=industries if industries else None,
            city=city or None,
            state=state or None,
            country=country or "Brazil",
            source_count=1,
            status="active",
            metadata_={
                "source": "crunchbase_csv",
                "imported_at": datetime.utcnow().isoformat(),
                **({"crunchbase_url": cb_url} if cb_url else {}),
                **({"cb_rank": cb_rank} if cb_rank else {}),
            },
        ))
        # Track slug to prevent dupes in next iterations
        existing_slugs.add(slug)

    print(f"New companies to insert: {len(to_insert)}")
    print(f"Existing companies enriched: {enriched}")
    print(f"Skipped (no new data): {skipped}")
    print()

    if dry_run:
        print("=== DRY RUN — no changes written ===\n")
        print("Sample NEW companies (first 15):")
        for c in to_insert[:15]:
            print(f"  [{c.sector or '?':12s}] {c.name} — {c.city}, {c.country}")
        print(f"\n  ... and {max(0, len(to_insert) - 15)} more")
        db.close()
        return

    # Commit enrichment changes
    if enriched > 0:
        try:
            db.commit()
            print(f"Enrichment committed: {enriched} companies updated")
        except Exception as e:
            db.rollback()
            print(f"[ERROR] Enrichment commit failed: {e}")

    # Batch insert new companies
    inserted = 0
    errors = 0
    total = len(to_insert)
    for i in range(0, total, BATCH_SIZE):
        batch = to_insert[i:i + BATCH_SIZE]
        try:
            db.add_all(batch)
            db.commit()
            inserted += len(batch)
            names = ", ".join(c.name for c in batch[:3])
            suffix = f" +{len(batch) - 3} more" if len(batch) > 3 else ""
            print(f"  [{inserted:>4}/{total}] {names}{suffix}")
        except Exception as e:
            db.rollback()
            errors += len(batch)
            print(f"  [ERROR] Batch {i // BATCH_SIZE + 1}: {e}")

    db.close()

    print(f"\n{'=' * 55}")
    print(f"Done: {inserted} inserted, {enriched} enriched, {skipped} skipped, {errors} errors")
    print(f"Total in DB should be: ~{len(existing_companies) + inserted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Crunchbase CSV into Sinal.ai DB")
    parser.add_argument("--csv", required=True, help="Path to Crunchbase CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    run(args.csv, dry_run=args.dry_run)
