#!/usr/bin/env python3
"""One-time migration: enrich plain-text seed articles with Markdown formatting.

Reads all briefing-* articles from the database, applies Markdown formatting
(headings, bold data points, blockquotes), and updates body_md in place.

Usage:
    # Preview changes
    python scripts/enrich_seed_markdown.py --dry-run

    # Apply to database
    python scripts/enrich_seed_markdown.py

    # Via Railway (production)
    railway run python3 scripts/enrich_seed_markdown.py --dry-run
    railway run python3 scripts/enrich_seed_markdown.py
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)


def bold_data_points(paragraph: str) -> str:
    """Add **bold** to numeric data points and key metrics.

    Uses a two-pass approach: first collect all match spans, then apply bold
    markers from right to left to avoid offset shifts and overlapping markers.
    """
    spans: list[tuple[int, int]] = []

    # US$ amounts: US$1.2B, US$342M, US$85M, US$3-8M, US$200-500K
    for m in re.finditer(
        r'US\$[\d.,]+(?:\s?[-–]\s?(?:US\$)?[\d.,]+)?(?:\s?(?:bilhão|bilhões|milhão|milhões|mil|B|M|K|bi|mi))?\b',
        paragraph,
    ):
        spans.append((m.start(), m.end()))

    # Percentages: 340%, 60%, +40%
    for m in re.finditer(r'\b[+\-]?\d+(?:[.,]\d+)?%', paragraph):
        spans.append((m.start(), m.end()))

    # Significant numbers with context: "14 startups", "47 empresas"
    context_words = (
        r'startups?|empresas?|deals?|rodadas?|fundos?|unicórnios?|vagas?|'
        r'clusters?|aquisições?|stars?|alunos?|founders?|países?|'
        r'investidores?|profissionais?|data engineers?|fintechs?|consultas?'
    )
    for m in re.finditer(rf'\b(\d{{2,}}(?:\.\d+)?)\s+({context_words})', paragraph):
        spans.append((m.start(), m.end()))

    if not spans:
        return paragraph

    # Merge overlapping spans and sort right-to-left
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    # Apply bold from right to left to preserve offsets
    for start, end in reversed(merged):
        paragraph = paragraph[:start] + "**" + paragraph[start:end] + "**" + paragraph[end:]

    return paragraph


def format_section_headers(paragraph: str) -> str:
    """Convert paragraph-starting patterns into ## headings."""
    # "Sinal 1:", "Sinal 2:" etc → ## heading
    if re.match(r'^Sinal \d+:', paragraph):
        parts = paragraph.split(':', 1)
        if len(parts) == 2:
            return f"## {parts[0].strip()}\n\n{parts[1].strip()}"

    # "Descoberta 1:", "Descoberta 2:" etc → ## heading
    if re.match(r'^Descoberta \d+:', paragraph):
        parts = paragraph.split(':', 1)
        if len(parts) == 2:
            return f"## {parts[0].strip()}\n\n{parts[1].strip()}"

    return paragraph


def enrich_body_md(body_md: str, title: str, agent_name: str) -> str:
    """Convert plain text body to rich Markdown."""
    paragraphs = [p.strip() for p in body_md.split("\n\n") if p.strip()]

    if not paragraphs:
        return body_md

    enriched = []

    # Add title as H1
    enriched.append(f"# {title}")
    enriched.append("---")

    for i, para in enumerate(paragraphs):
        # Apply section headers
        para = format_section_headers(para)

        # Apply bold data points
        para = bold_data_points(para)

        # First paragraph: make it a lead/intro with slightly different treatment
        if i == 0:
            enriched.append(f"*{para}*")
        # Last paragraph: make it a blockquote (key insight/conclusion)
        elif i == len(paragraphs) - 1 and not para.startswith("##"):
            enriched.append(f"> {para}")
        else:
            enriched.append(para)

    return "\n\n".join(enriched)


def main():
    parser = argparse.ArgumentParser(description="Enrich seed articles with Markdown")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Fetch all briefing-* articles
        rows = session.execute(
            text("""
                SELECT id, slug, title, agent_name, body_md
                FROM content_pieces
                WHERE slug LIKE 'briefing-%'
                ORDER BY slug
            """)
        ).fetchall()

        print(f"Found {len(rows)} briefing articles to enrich\n")

        updated = 0
        for row in rows:
            article_id, slug, title, agent_name, body_md = row

            if not body_md:
                print(f"  SKIP (no body): {slug}")
                continue

            # Check if already has Markdown formatting (idempotent)
            if body_md.strip().startswith("#"):
                print(f"  SKIP (already enriched): {slug}")
                continue

            enriched = enrich_body_md(body_md, title, agent_name)

            if args.dry_run:
                print(f"  PREVIEW: {slug}")
                print(f"    Title: {title}")
                # Show first 200 chars of enriched content
                preview = enriched[:300].replace('\n', '\n    ')
                print(f"    Body preview:\n    {preview}...")
                print()
            else:
                session.execute(
                    text("UPDATE content_pieces SET body_md = :body WHERE id = :id"),
                    {"body": enriched, "id": article_id},
                )
                print(f"  UPDATED: {slug}")
                updated += 1

        if not args.dry_run:
            session.commit()
            print(f"\nDone: {updated} articles enriched with Markdown formatting")
        else:
            print(f"\nDry run complete: {len(rows)} articles would be enriched")

    finally:
        session.close()


if __name__ == "__main__":
    main()
