"""Import companies from JSON into production DB (batch upsert by slug)."""
import json
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.database.session import SessionLocal
from packages.database.models.company import Company

BATCH_SIZE = 100


def import_companies():
    src = "scripts/companies_export.json"
    with open(src, "r", encoding="utf-8") as f:
        rows = json.load(f)

    db = SessionLocal()

    # Load all existing slugs in one query
    existing_slugs = set(
        slug for (slug,) in db.query(Company.slug).all()
    )
    print(f"Existing: {len(existing_slugs)} companies in DB")

    to_insert = []
    skipped = 0

    for row in rows:
        if row["slug"] in existing_slugs:
            skipped += 1
            continue

        founded = None
        if row.get("founded_date"):
            try:
                founded = date.fromisoformat(row["founded_date"])
            except ValueError:
                pass

        to_insert.append(Company(
            name=row["name"],
            slug=row["slug"],
            description=row.get("description") or None,
            short_description=row.get("short_description"),
            sector=row.get("sector"),
            sub_sector=row.get("sub_sector"),
            tags=row.get("tags"),
            city=row.get("city"),
            state=row.get("state"),
            country=row.get("country", "Brasil"),
            founded_date=founded,
            team_size=row.get("team_size"),
            tech_stack=row.get("tech_stack"),
            business_model=row.get("business_model"),
            funding_stage=row.get("funding_stage"),
            total_funding_usd=row.get("total_funding_usd"),
            is_trending=row.get("is_trending", False),
            website=row.get("website") or None,
            github_url=row.get("github_url"),
            linkedin_url=row.get("linkedin_url"),
            twitter_url=row.get("twitter_url"),
            cnpj=row.get("cnpj"),
            source_count=row.get("source_count", 1),
            status=row.get("status", "active"),
            metadata_=row.get("metadata"),
        ))

    print(f"To insert: {len(to_insert)} new companies ({skipped} already exist)")
    print(f"Batches: {(len(to_insert) + BATCH_SIZE - 1) // BATCH_SIZE} x {BATCH_SIZE}\n")

    # Batch insert
    inserted = 0
    errors = 0
    for i in range(0, len(to_insert), BATCH_SIZE):
        batch = to_insert[i:i + BATCH_SIZE]
        try:
            db.add_all(batch)
            db.commit()
            inserted += len(batch)
            # Show sample names from batch
            names = ", ".join(c.name for c in batch[:3])
            suffix = f" +{len(batch)-3} more" if len(batch) > 3 else ""
            print(f"  [{inserted:>4}/{len(to_insert)}] {names}{suffix}")
        except Exception as e:
            db.rollback()
            errors += len(batch)
            print(f"  [ERROR] Batch {i//BATCH_SIZE + 1} failed: {e}")

    db.close()
    print(f"\n{'='*50}")
    print(f"Done: {inserted} inserted, {skipped} skipped, {errors} errors")
    print(f"Total in DB should be: ~{len(existing_slugs) + inserted}")


if __name__ == "__main__":
    import_companies()
