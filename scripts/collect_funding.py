#!/usr/bin/env python3
"""Continuous funding event collector for Sinal.lab.

Runs in a loop, collecting funding data from multiple sources and
persisting new events to the funding_rounds table. Designed to run
as a background process (Railway service or local daemon).

Sources:
  - Coresignal API (funding rounds via company database)
  - NeoFeed /negocios/ (scraping deal articles)
  - Bloomberg Linea (scraping deal articles)
  - RSS feeds (LatamList, TechCrunch LATAM, Crunchbase News)

Usage:
    # Run once
    python scripts/collect_funding.py --once

    # Run continuously (default: every 4 hours)
    python scripts/collect_funding.py

    # Custom interval
    python scripts/collect_funding.py --interval 7200

    # Dry run (no DB writes)
    python scripts/collect_funding.py --once --dry-run
"""

import argparse
import hashlib
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

import httpx
from sqlalchemy import text

from packages.database.session import get_session
from packages.database.models.funding_round import FundingRound

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 4 * 3600  # 4 hours


# ---------------------------------------------------------------------------
# Coresignal funding collector
# ---------------------------------------------------------------------------

CORESIGNAL_COUNTRIES = ["Brazil", "Mexico", "Argentina", "Colombia", "Chile"]
CORESIGNAL_INDUSTRIES = [
    "Financial Services",
    "Computer Software",
    "Internet",
    "Information Technology & Services",
]


def _parse_coresignal_amount(raw: str) -> Optional[float]:
    """Parse 'US$ 22.5M' or 'US$ 1.2B' to float."""
    if not raw:
        return None
    raw = raw.strip().replace(",", "").replace("\n", "")
    m = re.search(r"[\d.]+", raw)
    if not m:
        return None
    val = float(m.group())
    if "B" in raw.upper():
        val *= 1_000_000_000
    elif "M" in raw.upper():
        val *= 1_000_000
    elif "K" in raw.upper():
        val *= 1_000
    return val


def _normalize_round_type(raw: str) -> str:
    """Normalize Coresignal round types to our schema."""
    raw = raw.lower().strip()
    mapping = {
        "pre-seed": "pre_seed",
        "seed": "seed",
        "series a": "series_a",
        "series b": "series_b",
        "series c": "series_c",
        "series d": "series_d",
        "series e": "series_e",
        "series unknown": "unknown",
        "ipo": "ipo",
        "debt financing": "debt",
        "grant": "grant",
        "convertible note": "convertible",
        "corporate round": "corporate",
        "secondary market": "secondary",
    }
    for key, val in mapping.items():
        if key in raw:
            return val
    return "unknown"


def collect_from_coresignal(
    days_back: int = 30,
    max_companies: int = 10,
) -> List[Dict]:
    """Fetch recent funding rounds from Coresignal API."""
    api_key = os.getenv("CORESIGNAL_API_KEY")
    if not api_key:
        logger.warning("CORESIGNAL_API_KEY not set, skipping")
        return []

    cutoff = date.today() - timedelta(days=days_back)
    events: List[Dict] = []
    seen_keys: set = set()
    credits_used = 0  # Track API credit consumption

    with httpx.Client(timeout=30) as client:
        for country in CORESIGNAL_COUNTRIES:
            for industry in CORESIGNAL_INDUSTRIES:
                try:
                    r = client.post(
                        "https://api.coresignal.com/cdapi/v2/company_base/search/filter",
                        headers={"apikey": api_key, "Content-Type": "application/json"},
                        json={
                            "country": f"({country})",
                            "industry": f"({industry})",
                            "employees_count_gte": 5,
                            "employees_count_lte": 5000,
                        },
                    )
                    r.raise_for_status()
                    ids = r.json()
                except Exception as e:
                    logger.error("Coresignal search failed for %s/%s: %s", country, industry, e)
                    continue

                collected = 0
                for cid in ids[:max_companies]:
                    try:
                        r2 = client.get(
                            f"https://api.coresignal.com/cdapi/v2/company_base/collect/{cid}",
                            headers={"apikey": api_key},
                        )
                        credits_used += 1  # Each collect call costs 1 credit
                        if r2.status_code != 200:
                            continue
                        data = r2.json()
                    except Exception:
                        continue

                    if data.get("deleted") == 1:
                        continue

                    rounds = data.get("company_funding_rounds_collection", [])
                    if not rounds:
                        continue

                    company_name = (data.get("name") or "").strip()
                    if not company_name:
                        continue

                    slug = (data.get("company_shorthand_name") or company_name).lower().replace(" ", "-")

                    for rnd in rounds:
                        round_date_str = rnd.get("last_round_date", "")
                        if not round_date_str:
                            continue
                        try:
                            round_date = datetime.strptime(round_date_str[:10], "%Y-%m-%d").date()
                        except ValueError:
                            continue

                        if round_date < cutoff:
                            continue

                        round_type = _normalize_round_type(rnd.get("last_round_type", "unknown"))
                        amount = _parse_coresignal_amount(rnd.get("last_round_money_raised", ""))

                        # Dedup key
                        dedup = f"{slug}:{round_type}:{round_date}"
                        if dedup in seen_keys:
                            continue
                        seen_keys.add(dedup)

                        # Extract investors
                        investors = []
                        for inv in data.get("company_featured_investors_collection", []):
                            inv_data = inv.get("company_investors_list", {})
                            name = inv_data.get("name", "")
                            if name and name not in investors:
                                investors.append(name)

                        events.append({
                            "company_slug": slug,
                            "company_name": company_name,
                            "round_type": round_type,
                            "amount_usd": amount,
                            "announced_date": round_date,
                            "lead_investors": investors[:5],
                            "participants": [],
                            "source_url": f"https://api.coresignal.com/cdapi/v2/company_base/collect/{cid}",
                            "source_name": "coresignal",
                            "confidence": 0.7,
                            "country": country,
                        })
                        collected += 1

                    time.sleep(0.3)  # rate limit

                logger.info(
                    "Coresignal %s/%s: %d funding events from %d companies",
                    country, industry, collected, len(ids),
                )

    logger.info(
        "Coresignal total: %d funding events (used ~%d collect credits, %d search credits)",
        len(events), credits_used, len(CORESIGNAL_COUNTRIES) * len(CORESIGNAL_INDUSTRIES),
    )
    return events


# ---------------------------------------------------------------------------
# NeoFeed scraper
# ---------------------------------------------------------------------------

NEOFEED_URL = "https://neofeed.com.br/negocios/"

# Broad funding-related keywords (case-insensitive match against title)
FUNDING_KEYWORDS = [
    "capta", "captou", "levanta", "levantou", "recebe", "recebeu",
    "rodada", "aporte", "investimento", "serie a", "serie b", "serie c",
    "series a", "series b", "series c", "seed", "pre-seed",
    "funding", "ipo", "m&a", "aquisicao", "aquisição", "compra",
    "fusao", "fusão", "deal", "megadeal",
    "us$", "r$", "milhoes", "milhões", "bilhoes", "bilhões",
    "valuation", "unicornio", "unicórnio",
]


def _title_has_funding(title: str) -> bool:
    """Check if a title is about funding/deals."""
    t = title.lower()
    return any(kw in t for kw in FUNDING_KEYWORDS)


def collect_from_neofeed() -> List[Dict]:
    """Scrape NeoFeed /negocios/ for funding articles."""
    events: List[Dict] = []

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            r = client.get(NEOFEED_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; SinalBot/1.0)"})
            r.raise_for_status()
            html = r.text
    except Exception as e:
        logger.error("NeoFeed scrape failed: %s", e)
        return []

    # Extract links + nearby titles (h2/h3 tags)
    links = re.findall(r'href="(https://neofeed\.com\.br/negocios/[^"]+)"', html)
    titles = re.findall(r'<h[23][^>]*>\s*([^<]{15,})\s*</h[23]>', html)

    # Match links to titles by position (best effort)
    seen_urls: set = set()
    for title in titles:
        title = title.strip()
        if not _title_has_funding(title):
            continue

        # Find a matching link
        title_slug = re.sub(r'[^a-z0-9]', '', title.lower())[:20]
        matched_url = None
        for link in links:
            if link not in seen_urls:
                matched_url = link
                seen_urls.add(link)
                break

        if not matched_url:
            matched_url = f"https://neofeed.com.br/negocios/{hashlib.md5(title.encode()).hexdigest()[:8]}"

        slug = hashlib.md5(matched_url.encode()).hexdigest()[:12]
        events.append({
            "company_slug": slug,
            "company_name": title[:100],
            "round_type": "unknown",
            "amount_usd": None,
            "announced_date": date.today(),
            "lead_investors": [],
            "participants": [],
            "source_url": matched_url,
            "source_name": "neofeed",
            "confidence": 0.4,
            "notes": title,
        })

    logger.info("NeoFeed: %d funding articles found", len(events))
    return events


# ---------------------------------------------------------------------------
# Bloomberg Linea scraper
# ---------------------------------------------------------------------------

BLOOMBERG_URL = "https://www.bloomberglinea.com.br/negocios/"


def collect_from_bloomberg() -> List[Dict]:
    """Scrape Bloomberg Linea for funding articles."""
    events: List[Dict] = []

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            r = client.get(BLOOMBERG_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; SinalBot/1.0)"})
            r.raise_for_status()
            html = r.text
    except Exception as e:
        logger.error("Bloomberg Linea scrape failed: %s", e)
        return []

    # Extract titles from JSON-LD headlines + h2/h3 + card text
    links = re.findall(r'href="(https://www\.bloomberglinea\.com\.br/[^"]+)"', html)
    titles = re.findall(r'"headline"\s*:\s*"([^"]{15,})"', html)
    titles += re.findall(r'<h[23][^>]*>\s*([^<]{15,})\s*</h[23]>', html)
    titles += re.findall(r'class="[^"]*card[^"]*"[^>]*>.*?<[^>]+>([^<]{15,})<', html, re.DOTALL)

    seen_urls: set = set()
    for title in titles:
        title = title.strip()
        if not _title_has_funding(title):
            continue

        matched_url = None
        for link in links:
            if link not in seen_urls and "/negocios/" in link:
                matched_url = link
                seen_urls.add(link)
                break

        if not matched_url:
            matched_url = f"https://www.bloomberglinea.com.br/negocios/{hashlib.md5(title.encode()).hexdigest()[:8]}"

        slug = hashlib.md5(matched_url.encode()).hexdigest()[:12]
        events.append({
            "company_slug": slug,
            "company_name": title[:100],
            "round_type": "unknown",
            "amount_usd": None,
            "announced_date": date.today(),
            "lead_investors": [],
            "participants": [],
            "source_url": matched_url,
            "source_name": "bloomberg_linea",
            "confidence": 0.4,
            "notes": title,
        })

    logger.info("Bloomberg Linea: %d funding articles found", len(events))
    return events


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_events(events: List[Dict], dry_run: bool = False) -> Tuple[int, int]:
    """Persist funding events to the database. Returns (inserted, skipped)."""
    if dry_run:
        for e in events:
            logger.info(
                "[DRY] %s %s %s %s (via %s)",
                e["company_name"], e["round_type"],
                f"${e['amount_usd']:,.0f}" if e.get("amount_usd") else "undisclosed",
                e.get("announced_date", ""),
                e["source_name"],
            )
        return 0, len(events)

    session = get_session()
    inserted = 0
    skipped = 0

    try:
        for e in events:
            # Check for existing (dedup by company + round_type + date)
            existing = session.execute(
                text(
                    "SELECT id FROM funding_rounds "
                    "WHERE company_slug = :slug AND round_type = :rtype "
                    "AND announced_date = :adate LIMIT 1"
                ),
                {
                    "slug": e["company_slug"],
                    "rtype": e["round_type"],
                    "adate": e.get("announced_date"),
                },
            ).fetchone()

            if existing:
                skipped += 1
                continue

            record = FundingRound(
                company_slug=e["company_slug"],
                company_name=e["company_name"],
                round_type=e["round_type"],
                amount_usd=e.get("amount_usd"),
                announced_date=e.get("announced_date"),
                lead_investors=e.get("lead_investors", []),
                participants=e.get("participants", []),
                source_url=e.get("source_url"),
                source_name=e.get("source_name"),
                confidence=e.get("confidence", 0.5),
                notes=e.get("notes"),
                metadata_={"country": e.get("country")},
            )
            session.add(record)
            inserted += 1

        session.commit()
    except Exception as ex:
        session.rollback()
        logger.error("Error persisting funding events: %s", ex)
        raise
    finally:
        session.close()

    return inserted, skipped


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_collection(dry_run: bool = False) -> None:
    """Run one collection cycle across all sources."""
    logger.info("Starting funding collection cycle")
    all_events: List[Dict] = []

    # Source 1: Coresignal (recent rounds)
    all_events.extend(collect_from_coresignal(days_back=14, max_companies=50))

    # Source 2: NeoFeed scraping
    all_events.extend(collect_from_neofeed())

    # Source 3: Bloomberg Linea scraping
    all_events.extend(collect_from_bloomberg())

    logger.info("Total events collected: %d", len(all_events))

    if all_events:
        inserted, skipped = persist_events(all_events, dry_run=dry_run)
        logger.info("Persisted: %d inserted, %d skipped (duplicates)", inserted, skipped)
    else:
        logger.info("No new events found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous funding event collector")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Seconds between cycles")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [funding-collector] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.once:
        run_collection(dry_run=args.dry_run)
        return

    logger.info("Starting continuous collection (interval: %ds)", args.interval)
    while True:
        try:
            run_collection(dry_run=args.dry_run)
        except Exception:
            logger.exception("Collection cycle failed")
        logger.info("Sleeping %ds until next cycle", args.interval)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
