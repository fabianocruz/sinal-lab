"""One-off ingest of manually curated LATAM tech companies.

Reads an inline list of CompanyProfile-compatible dicts and upserts
them via the existing Company model. Idempotent by slug.

Usage:
    python3 scripts/ingest_companies_manual.py --dry-run
    python3 scripts/ingest_companies_manual.py
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

from packages.database.models.company import Company  # noqa: E402
from packages.database.session import get_session  # noqa: E402

logger = logging.getLogger(__name__)

# Curated LATAM tech companies from Crunchbase dumps (2026-04-21).
# Filtered from ~150 entries: only tech/fintech/crypto/analytics,
# excluding traditional news/media outlets.
COMPANIES = [
    {
        "slug": "red-atlas",
        "name": "RED Atlas",
        "description": "Platform that provides real estate data and insights powered by AI, analytics, and machine learning for property market professionals.",
        "short_description": "AI-powered real estate analytics platform",
        "sector": "PropTech",
        "city": "San Juan",
        "country": "Puerto Rico",
        "tags": ["AI", "analytics", "real-estate", "machine-learning"],
    },
    {
        "slug": "knewin",
        "name": "Knewin",
        "description": "Largest PR Tech company in Latin America, helping over 2,000 clients manage their reputation through analytics, ML, and social listening.",
        "short_description": "PR Tech + social listening com ML",
        "sector": "MarTech",
        "city": "Florianópolis",
        "state": "Santa Catarina",
        "country": "Brazil",
        "tags": ["pr-tech", "analytics", "machine-learning", "social-listening"],
    },
    {
        "slug": "newsco-ai",
        "name": "Newsco.ai",
        "description": "Platform that aggregates news from various sources using AI.",
        "short_description": "AI-powered news aggregation",
        "sector": "AI",
        "city": "João Ramalho",
        "state": "São Paulo",
        "country": "Brazil",
        "tags": ["AI", "news-aggregation", "apps"],
    },
    {
        "slug": "futuur",
        "name": "Futuur",
        "description": "Community-based forecasting game and prediction market platform, leveraging collective intelligence to forecast events.",
        "short_description": "Prediction market + forecasting community",
        "sector": "FinTech",
        "city": "Rio de Janeiro",
        "state": "Rio de Janeiro",
        "country": "Brazil",
        "tags": ["prediction-markets", "gaming", "information-services"],
    },
    {
        "slug": "coincodex",
        "name": "CoinCodex",
        "description": "Cryptocurrency market data platform covering real-time coin prices, news, guides, and analysis.",
        "short_description": "Cripto market data + news",
        "sector": "FinTech",
        "city": "Santiago",
        "country": "Chile",
        "tags": ["crypto", "bitcoin", "blockchain", "finance"],
    },
    {
        "slug": "livecoins",
        "name": "Livecoins",
        "description": "Largest Brazilian news portal covering Bitcoin, blockchain, and cryptocurrency markets.",
        "short_description": "Maior portal brasileiro de cripto",
        "sector": "FinTech",
        "state": "Minas Gerais",
        "country": "Brazil",
        "tags": ["crypto", "bitcoin", "blockchain", "finance"],
    },
    {
        "slug": "autoclipper",
        "name": "Autoclipper",
        "description": "AI tool that turns a single video into multiple short-form content pieces for social media distribution.",
        "short_description": "AI video-to-shorts automation",
        "sector": "AI",
        "city": "São Luís",
        "state": "Maranhão",
        "country": "Brazil",
        "tags": ["AI", "video", "content-creation", "automation"],
    },
    {
        "slug": "contxto",
        "name": "Contxto",
        "description": "Media and data platform focused on Latin America's startup, tech, and venture capital scene.",
        "short_description": "Mídia + data sobre startups LATAM",
        "sector": "MediaTech",
        "city": "Guadalajara",
        "state": "Jalisco",
        "country": "Mexico",
        "tags": ["media", "startup-data", "latam"],
    },
]


def upsert_company(session, data: dict) -> str:
    """Insert or update a company by slug. Returns action taken."""
    existing = session.query(Company).filter_by(slug=data["slug"]).first()
    if existing:
        # Only update fields that are currently empty, preserving richer data.
        updated = False
        for field in ("description", "short_description", "sector", "city", "state", "country"):
            if not getattr(existing, field, None) and data.get(field):
                setattr(existing, field, data[field])
                updated = True
        if data.get("tags") and not existing.tags:
            existing.tags = data["tags"]
            updated = True
        return "updated" if updated else "skipped"

    company = Company(
        id=uuid.uuid4(),
        name=data["name"],
        slug=data["slug"],
        description=data.get("description"),
        short_description=data.get("short_description"),
        sector=data.get("sector"),
        city=data.get("city"),
        state=data.get("state"),
        country=data.get("country", "Brazil"),
        tags=data.get("tags"),
        status="active",
    )
    session.add(company)
    return "inserted"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest manually curated LATAM tech companies")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    session = get_session()
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    try:
        for data in COMPANIES:
            action = upsert_company(session, data)
            stats[action] += 1
            logger.info("  %-10s %s (%s)", action.upper(), data["slug"], data.get("sector"))

        if args.dry_run:
            session.rollback()
            logger.info("DRY RUN — rolled back. Would have: %s", stats)
        else:
            session.commit()
            logger.info("COMMITTED: %s", stats)
    finally:
        session.close()


if __name__ == "__main__":
    main()
