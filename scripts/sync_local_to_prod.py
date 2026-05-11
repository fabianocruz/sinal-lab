"""Sync selected tables from local DB to prod (Railway).

Workflow:
1. Backup: dumps prod rows for content_pieces (affected slugs) to JSON.
2. Upsert: for each affected row in local, upsert in prod (by slug/company_slug).
3. Safety: --dry-run prints plan without writing. Each table handled separately.

Scope (hard-coded for clarity):
- content_pieces: 5 slugs (sinal-semanal-55, radar/codigo/funding/mercado week-17)
- companies: all new slugs (inserted in this session)
- funding_rounds: all rows (upsert by company_slug+round_type+announced_date)

Usage:
    python scripts/sync_local_to_prod.py --dry-run
    python scripts/sync_local_to_prod.py         # execute
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from packages.database.models.company import Company  # noqa: E402
from packages.database.models.content_piece import ContentPiece  # noqa: E402
from packages.database.models.funding_round import FundingRound  # noqa: E402

logger = logging.getLogger(__name__)

LOCAL_URL = os.getenv("DATABASE_URL")
PROD_URL = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")

SLUGS_TO_SYNC = [
    "sinal-semanal-57",
    "radar-week-19",
    "codigo-week-19",
    "funding-semanal-19",
    "mercado-week-19",
]

COMPANY_SLUGS_TO_SYNC: list[str] = []  # no new companies for ed 57


def _content_to_dict(p: ContentPiece) -> dict[str, Any]:
    return {
        "title": p.title,
        "slug": p.slug,
        "subtitle": p.subtitle,
        "body_md": p.body_md,
        "body_html": p.body_html,
        "summary": p.summary,
        "content_type": p.content_type,
        "agent_name": p.agent_name,
        "agent_run_id": p.agent_run_id,
        "sources": p.sources,
        "confidence_dq": p.confidence_dq,
        "confidence_ac": p.confidence_ac,
        "review_status": p.review_status,
        "reviewer": p.reviewer,
        "reviewed_at": p.reviewed_at,
        "published_at": p.published_at,
        "meta_description": p.meta_description,
        "canonical_url": p.canonical_url,
        "metadata_": p.metadata_,
        "author_name": p.author_name,
    }


def _company_to_dict(c: Company) -> dict[str, Any]:
    fields = [
        "name", "slug", "description", "short_description", "sector", "sub_sector",
        "tags", "city", "state", "country", "founded_date", "team_size", "tech_stack",
        "business_model", "website", "github_url", "linkedin_url", "twitter_url",
        "status",
    ]
    out = {f: getattr(c, f, None) for f in fields}
    # metadata column name varies; use getattr defensively
    if hasattr(c, "metadata_"):
        out["metadata_"] = c.metadata_
    return out


def _round_to_dict(r: FundingRound) -> dict[str, Any]:
    fields = [
        "company_slug", "company_name", "round_type", "amount_usd", "amount_local",
        "currency", "valuation_usd", "announced_date", "closed_date",
        "lead_investors", "participants", "source_url", "source_name",
        "confidence", "notes",
    ]
    out = {f: getattr(r, f, None) for f in fields}
    if hasattr(r, "metadata_"):
        out["metadata_"] = r.metadata_
    return out


def backup_prod_content(prod_session: Session, backup_dir: Path) -> None:
    """Dump prod content_pieces for affected slugs into a JSON backup."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    rows = prod_session.query(ContentPiece).filter(
        ContentPiece.slug.in_(SLUGS_TO_SYNC)
    ).all()
    payload = []
    for p in rows:
        d = _content_to_dict(p)
        for k, v in list(d.items()):
            if isinstance(v, (datetime,)):
                d[k] = v.isoformat()
            elif isinstance(v, uuid.UUID):
                d[k] = str(v)
        payload.append(d)
    path = backup_dir / f"prod_content_pieces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    logger.info("Backed up %d prod content_pieces to %s", len(payload), path)


def sync_content_pieces(
    local_session: Session,
    prod_session: Session,
    dry_run: bool,
) -> None:
    local_rows = local_session.query(ContentPiece).filter(
        ContentPiece.slug.in_(SLUGS_TO_SYNC)
    ).all()
    logger.info("Found %d local content_pieces to sync", len(local_rows))

    for lp in local_rows:
        data = _content_to_dict(lp)
        existing = prod_session.query(ContentPiece).filter_by(slug=lp.slug).first()
        if existing:
            action = "UPDATE"
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            action = "INSERT"
            new = ContentPiece(id=uuid.uuid4(), **data)
            prod_session.add(new)
        logger.info(
            "  %s %s | status=%s | %s",
            action, lp.slug, lp.review_status, (lp.title or "")[:70],
        )

    if dry_run:
        prod_session.rollback()
        logger.info("DRY RUN — rolled back content_pieces")
    else:
        prod_session.commit()
        logger.info("content_pieces COMMITTED")


def sync_companies(
    local_session: Session,
    prod_session: Session,
    dry_run: bool,
) -> None:
    local_rows = local_session.query(Company).filter(
        Company.slug.in_(COMPANY_SLUGS_TO_SYNC)
    ).all()
    logger.info("Found %d local companies to sync", len(local_rows))

    for lc in local_rows:
        data = _company_to_dict(lc)
        existing = prod_session.query(Company).filter_by(slug=lc.slug).first()
        if existing:
            action = "SKIP (exists)"
        else:
            action = "INSERT"
            new = Company(id=uuid.uuid4(), **data)
            prod_session.add(new)
        logger.info("  %s %s (%s)", action, lc.slug, lc.sector)

    if dry_run:
        prod_session.rollback()
        logger.info("DRY RUN — rolled back companies")
    else:
        prod_session.commit()
        logger.info("companies COMMITTED")


def sync_funding_rounds(
    local_session: Session,
    prod_session: Session,
    dry_run: bool,
) -> None:
    local_rows = local_session.query(FundingRound).filter(
        FundingRound.source_name == "crunchbase_manual_dump"
    ).all()
    logger.info("Found %d local crunchbase funding_rounds to sync", len(local_rows))

    inserted = 0
    skipped = 0
    for lr in local_rows:
        existing = prod_session.query(FundingRound).filter_by(
            company_slug=lr.company_slug,
            round_type=lr.round_type,
            announced_date=lr.announced_date,
        ).first()
        if existing:
            skipped += 1
            continue
        data = _round_to_dict(lr)
        new = FundingRound(id=uuid.uuid4(), **data)
        prod_session.add(new)
        inserted += 1

    logger.info("funding_rounds: %d to insert, %d to skip (already present)", inserted, skipped)

    if dry_run:
        prod_session.rollback()
        logger.info("DRY RUN — rolled back funding_rounds")
    else:
        prod_session.commit()
        logger.info("funding_rounds COMMITTED")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync local → prod")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--skip-backup", action="store_true", help="Skip backup step")
    parser.add_argument(
        "--only",
        choices=["content", "companies", "funding", "all"],
        default="all",
        help="Restrict scope",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not LOCAL_URL or not PROD_URL:
        logger.error("Need DATABASE_URL (local) and PROD_DATABASE_URL (prod) set.")
        sys.exit(1)

    local_engine = create_engine(LOCAL_URL)
    prod_engine = create_engine(PROD_URL)

    local_session = Session(local_engine)
    prod_session = Session(prod_engine)

    try:
        if not args.skip_backup:
            backup_dir = PROJECT_ROOT / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_prod_content(prod_session, backup_dir)

        if args.only in ("content", "all"):
            sync_content_pieces(local_session, prod_session, args.dry_run)
        if args.only in ("companies", "all"):
            sync_companies(local_session, prod_session, args.dry_run)
        if args.only in ("funding", "all"):
            sync_funding_rounds(local_session, prod_session, args.dry_run)

        logger.info("DONE (dry_run=%s)", args.dry_run)
    finally:
        local_session.close()
        prod_session.close()


if __name__ == "__main__":
    main()
