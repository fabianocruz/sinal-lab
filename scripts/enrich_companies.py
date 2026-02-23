#!/usr/bin/env python3
"""Enrich companies in the database with sector, tags, and quality classification.

Reads all companies from the DB, classifies each as startup vs non-startup
(university, government, course, personal dev), assigns a sector from the
platform's SECTOR_OPTIONS, generates tags, and updates the DB.

Usage:
    python scripts/enrich_companies.py --dry-run       # preview classifications
    python scripts/enrich_companies.py                  # apply to database
    python scripts/enrich_companies.py --deactivate     # also set non-startups to inactive
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)

# ---------------------------------------------------------------------------
# Sector classification (mirrors SECTOR_OPTIONS from apps/web/lib/company.ts)
# ---------------------------------------------------------------------------

SECTOR_OPTIONS = [
    "Fintech",
    "E-commerce",
    "SaaS",
    "Healthtech",
    "Edtech",
    "Logistics",
    "Agritech",
    "AI/ML",
    "Proptech",
    "HR Tech",
]

# Keywords mapped to sectors.  Checked against name + description + website.
SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Fintech": [
        "fintech", "banking", "bank", "payment", "payments", "crypto",
        "exchange", "lending", "credit", "financial", "capital market",
        "invest", "trading", "insurance", "insurtech", "neobank",
        "wallet", "remittance", "defi", "blockchain",
    ],
    "E-commerce": [
        "e-commerce", "ecommerce", "marketplace", "commerce platform",
        "retail", "shop", "store", "loja virtual", "tienda", "shopify",
        "woocommerce", "magento", "delivery", "food delivery", "super app",
    ],
    "SaaS": [
        "saas", "software as a service", "cloud platform", "api platform",
        "developer tool", "devtools", "dev tool", "infrastructure",
        "platform as a service", "erp", "crm", "cms", "b2b software",
        "enterprise software", "automation", "workflow",
    ],
    "Healthtech": [
        "healthtech", "health tech", "health", "healthcare", "medical",
        "telemedicine", "wellness", "fitness", "pharma", "biotech",
        "clinical", "hospital", "dental", "mental health", "dengue",
        "epidemiolog",
    ],
    "Edtech": [
        "edtech", "education", "learning", "coding school", "bootcamp",
        "teaching", "training", "course", "cursos", "educacion",
        "educacional", "aluno", "student", "lms", "moodle",
    ],
    "Logistics": [
        "logistics", "logistic", "supply chain", "shipping", "freight",
        "delivery service", "warehouse", "fleet", "last mile", "trucking",
        "mobility", "transport",
    ],
    "Agritech": [
        "agritech", "agriculture", "farming", "agro", "precision agriculture",
        "crop", "livestock", "farm", "agribusiness",
    ],
    "AI/ML": [
        "artificial intelligence", "machine learning", "ai-powered",
        "deep learning", "nlp", "computer vision", "data science",
        "neural network", "llm", "gpt", "ai platform", "ml platform",
        "robotics", "robot", "automation", "intelligent",
    ],
    "Proptech": [
        "proptech", "real estate", "property", "housing", "rent",
        "mortgage", "construction tech", "constru",
    ],
    "HR Tech": [
        "hr tech", "human resources", "recruiting", "recruitment",
        "talent", "hiring", "payroll", "benefits", "employee",
        "corporate wellness", "people management",
    ],
}

# ---------------------------------------------------------------------------
# Non-startup detection patterns
# ---------------------------------------------------------------------------

NON_STARTUP_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern, reason)
    # Universities and academic
    (r"\b(universid|universi|facult|escola|escuela|utn\b|uerj|usp\b|puc[-\s]|ufr|fiuba|unahur)", "university"),
    (r"\b(cátedra|catedra|materia|asignatura|disciplina|curso de |programación con|diseño de sistema)", "academic_course"),
    (r"\b(laboratori[oa]|lab\b|núcleo de pesquisa|research group)", "research_lab"),
    (r"\b(maestría|mestrado|doutorado|graduação|graduate)", "academic_program"),
    (r"\bgithub classroom\b", "academic_course"),
    # Government
    (r"\b(gobierno|governo|secretar[ií]a|consejería|prefeitura|municipal|distrital|presidencia)", "government"),
    (r"\bgob\.(ar|mx|co|cl|br)\b", "government"),
    (r"\bgov\.co\b", "government"),
    # Personal / freelancer
    (r"\b(fullstack .* dev|frontend .* dev|backend .* dev|prof\.|professor)\b", "personal"),
    (r"\bwesley andrade\b", "personal"),
    # Academic projects (not companies)
    (r"\b(ejercicios y apuntes|soluções das atividades|trabalho integrador)", "academic_project"),
    # Division / department (part of larger org, not a startup)
    (r"\b(division|división|departamento)\b", "org_division"),
]

# Names that are clearly not startups (exact slug match)
NON_STARTUP_SLUGS = {
    "gcba",                  # Gobierno de Buenos Aires
    "altaconsejeriatic",     # Alta Consejería Distrital de TIC
    "pem-humboldt",          # Dirección de Conocimiento
    "govimentumcms",         # Govimentum CMS (gov project)
    "mat-esp-2015",          # Math course 2015
    "mat-esp-2016",          # Math course 2016
    "dds-frd-utn",           # Diseño de Sistemas - UTN
    "dds-utn",               # Diseño de Sistemas - UTN
    "pdep-sm",               # UTN paradigms course
    "sisoputnfrba",          # UTN.SO
    "obj2-unahur",           # Programación con Objetos
    "fgv-emap",              # FGV math school
    "ieti-eci",              # Innovation course ECI
    "cese-dci",              # Circuit design course
    "tpii",                  # Taller de Proyecto 2
    "profesor-augusto-baffa", # Professor page
    "wesandradealves-jobs",  # Freelancer
    "nsi-iff",               # Research center
    "opus-research",         # Research group
    "laser-ud",              # Research lab
    "mat-esp-2015",          # Academic
    "mat-esp-2016",          # Academic
    "inmegen",               # Government research institute
    "csb-ig",                # Computational biology lab
    "swisstierrascolombia",  # Swiss cooperation / government
    "labplc",                # Government innovation lab
    "iswpoli",               # Software engineering course
    "maestriahd",            # Masters program
    "desarrollo-cespi",      # University development center
    "sima2soft",             # Software division
    "simassoftmean",         # Software division
    "programoxcomida",       # Community project
    "thedatapub",            # Community / meetup
    "glud",                  # University group
    "codwelt",               # Developer community
    "comunidad-devf",        # Developer community
    "conekta-examples",      # Example repos (not the company)
}


def classify_startup(name: str, description: str, slug: str, website: str) -> tuple[bool, str]:
    """Return (is_startup, reason) for a company."""
    if slug in NON_STARTUP_SLUGS:
        return False, "slug_blocklist"

    combined = f"{name} {description} {website}".lower()

    for pattern, reason in NON_STARTUP_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return False, reason

    return True, "startup"


def classify_sector(name: str, description: str, website: str) -> str | None:
    """Assign a sector from SECTOR_OPTIONS based on keyword matching.

    Returns the sector with the highest keyword hit count, or None.
    """
    combined = f"{name} {description} {website}".lower()
    scores: dict[str, int] = {}

    for sector, keywords in SECTOR_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in combined)
        if count > 0:
            scores[sector] = count

    if not scores:
        return None

    return max(scores, key=scores.get)  # type: ignore[arg-type]


def generate_tags(name: str, description: str, sector: str | None) -> list[str]:
    """Generate tags from description keywords and sector."""
    tags: list[str] = []
    combined = f"{name} {description}".lower()

    tag_keywords = {
        "open-source": ["open source", "open-source", "código abierto", "codigo abierto"],
        "B2B": ["b2b", "enterprise", "corporate", "empresas"],
        "B2C": ["b2c", "consumer", "retail", "usuario"],
        "marketplace": ["marketplace"],
        "mobile": ["mobile", "app", "ios", "android", "react native"],
        "API": ["api", "sdk", "developer", "developer tool"],
        "data": ["data", "analytics", "big data", "data science"],
        "security": ["security", "segurança", "seguridad", "cybersecurity", "infosec"],
        "cloud": ["cloud", "aws", "azure", "gcp", "kubernetes", "docker"],
        "payments": ["payment", "payments", "checkout", "billing"],
        "crypto": ["crypto", "blockchain", "web3", "defi", "nft"],
        "LATAM": ["latam", "latin america", "américa latina"],
        "Brazil": ["brazil", "brasil", "brazilian", "brasileir"],
        "Mexico": ["mexico", "méxico", "mexican"],
        "Argentina": ["argentina", "argentin"],
        "Colombia": ["colombia", "colombian"],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in combined for kw in keywords):
            tags.append(tag)

    if sector and sector not in tags:
        tags.insert(0, sector)

    return tags[:8]  # Cap at 8 tags


def fetch_companies(session: Session) -> list[dict]:
    """Fetch all companies from the database."""
    result = session.execute(
        text("SELECT slug, name, description, website, sector, tags, status FROM companies ORDER BY name")
    )
    return [dict(row._mapping) for row in result]


def update_company(
    session: Session,
    slug: str,
    *,
    sector: str | None,
    tags: list[str] | None,
    status: str | None = None,
) -> None:
    """Update sector, tags, and optionally status for a company."""
    parts = []
    params: dict = {"slug": slug}

    if sector is not None:
        parts.append("sector = :sector")
        params["sector"] = sector

    if tags is not None:
        parts.append("tags = :tags")
        params["tags"] = json.dumps(tags)

    if status is not None:
        parts.append("status = :status")
        params["status"] = status

    if not parts:
        return

    sql = f"UPDATE companies SET {', '.join(parts)} WHERE slug = :slug"
    session.execute(text(sql), params)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Namespace with --dry-run and --deactivate flags.
    """
    parser = argparse.ArgumentParser(description="Enrich companies with sector and tags")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview classifications without writing to the database",
    )
    parser.add_argument(
        "--deactivate",
        action="store_true",
        help="Set non-startup entries to status='inactive'",
    )
    return parser.parse_args()


def main() -> None:
    """Enrich all companies in the database with sector and tags.

    Classifies each company as startup or non-startup, assigns a sector,
    generates tags, and updates the database. Uses --dry-run to preview
    or --deactivate to inactivate non-startups.
    """
    args = parse_args()

    print(f"Connecting to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    make_session = sessionmaker(bind=engine)

    with make_session() as session:
        companies = fetch_companies(session)
        print(f"Found {len(companies)} companies\n")

        startups: list[dict] = []
        non_startups: list[dict] = []
        enriched = 0
        already_had_sector = 0

        for co in companies:
            slug = co["slug"]
            name = co["name"] or ""
            desc = co["description"] or ""
            website = co["website"] or ""
            current_sector = co["sector"]
            current_tags = co["tags"]

            is_startup, reason = classify_startup(name, desc, slug, website)

            if not is_startup:
                non_startups.append({"name": name, "slug": slug, "reason": reason})
                if args.deactivate and not args.dry_run:
                    update_company(session, slug, sector=None, tags=None, status="inactive")
                continue

            startups.append({"name": name, "slug": slug})

            # Skip if already has sector (e.g., from curated CSV seed)
            if current_sector:
                already_had_sector += 1
                continue

            sector = classify_sector(name, desc, website)
            tags = generate_tags(name, desc, sector)

            if not args.dry_run:
                update_company(session, slug, sector=sector, tags=tags if tags else None)

            enriched += 1
            sector_str = sector or "—"
            tags_str = ", ".join(tags[:4]) if tags else "—"
            print(f"  ENRICH: {name:45s} → {sector_str:12s} [{tags_str}]")

        if not args.dry_run:
            session.commit()

        # Summary
        print(f"\n{'=' * 70}")
        print(f"SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total companies:     {len(companies)}")
        print(f"Classified startup:  {len(startups)}")
        print(f"Non-startup:         {len(non_startups)}")
        print(f"Already had sector:  {already_had_sector}")
        print(f"Newly enriched:      {enriched}")
        if args.deactivate:
            print(f"Deactivated:         {len(non_startups)}")

        if non_startups:
            print(f"\n--- Non-startups ({len(non_startups)}) ---")
            for ns in non_startups:
                print(f"  [{ns['reason']:20s}] {ns['name']}")

        if args.dry_run:
            print(f"\n⚠ DRY RUN — no changes written to database.")
        else:
            print(f"\nDone.")


if __name__ == "__main__":
    main()
