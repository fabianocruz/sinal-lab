"""Export all active companies from local DB to JSON for production import."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.database.session import SessionLocal
from packages.database.models.company import Company


def export():
    db = SessionLocal()
    companies = db.query(Company).filter(Company.status == "active").all()

    rows = []
    for c in companies:
        rows.append({
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "short_description": c.short_description,
            "sector": c.sector,
            "sub_sector": c.sub_sector,
            "tags": c.tags,
            "city": c.city,
            "state": c.state,
            "country": c.country,
            "founded_date": str(c.founded_date) if c.founded_date else None,
            "team_size": c.team_size,
            "tech_stack": c.tech_stack,
            "business_model": c.business_model,
            "funding_stage": c.funding_stage,
            "total_funding_usd": c.total_funding_usd,
            "is_trending": c.is_trending,
            "website": c.website,
            "github_url": c.github_url,
            "linkedin_url": c.linkedin_url,
            "twitter_url": c.twitter_url,
            "cnpj": c.cnpj,
            "source_count": c.source_count,
            "status": c.status,
            "metadata": c.metadata_,
        })

    db.close()

    out = "scripts/companies_export.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)

    print(f"Exported {len(rows)} companies to {out}")


if __name__ == "__main__":
    export()
