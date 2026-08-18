"""Normalize the social_signals gap-week pieces before publishing.

These were generated weekly during the 13-week publishing gap (ISO weeks
21-32) and never published. The editorial prose is solid; what needs
cleaning is mechanical output noise:

1. Raw metric dumps  ("Volume: 0.94 | Velocidade: 0.50 | ...") — internal
   scoring detail, and 'Velocidade' is a constant 0.50 everywhere, so it
   carries no information for a reader.
2. Missing accents in generated headers ("Aceleracao", "Estagio").
3. Blockquotes truncated mid-sentence by an upstream character cap.
4. "Empresas mencionadas" lists polluted by non-companies (LLM, Brasil,
   Mexico) and unresolved tickers (BN, TRN) — the entity extraction is
   demonstrably unreliable, so the line is dropped rather than published
   wrong.

Usage:
    python polish_social_signals.py --sample        # before/after, no writes
    python polish_social_signals.py --apply         # write to LOCAL db
"""

import argparse
import re
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

GAP_WEEKS = list(range(21, 33))  # weeks 21..32 inclusive

ACCENT_FIXES = {
    "Temas em Aceleracao": "Temas em Aceleração",
    "**Estagio:**": "**Estágio:**",
    "Estagio:": "Estágio:",
}

# The classifier emits its stage enum in English inside otherwise
# Portuguese copy.
STAGE_LABELS = {
    "accelerating": "acelerando",
    "emerging": "emergente",
    "sustained": "sustentado",
    "declining": "em queda",
}

# "Volume: 0.94 | Velocidade: 0.50 | Autoridade: 0.00 | Cross-platform: 0.75"
RAW_METRICS_RE = re.compile(
    r"^Volume:\s*[\d.]+\s*\|\s*Velocidade:\s*[\d.]+\s*\|\s*"
    r"Autoridade:\s*[\d.]+\s*\|\s*Cross-platform:\s*[\d.]+\s*$",
    re.MULTILINE,
)

COMPANIES_LINE_RE = re.compile(r"^\*\*Empresas mencionadas:\*\*.*$", re.MULTILINE)

SENTENCE_END = (".", "!", "?", '"', "”", ")")


def trim_truncated(text: str) -> str:
    """Cut a blockquote back to its last complete sentence.

    The upstream generator caps blockquote length mid-word, leaving
    fragments like '...estrategias de '. Better to end cleanly than to
    publish a dangling clause. Returns the text unchanged when it already
    ends on a sentence boundary.
    """
    stripped = text.rstrip()
    if not stripped or stripped.endswith(SENTENCE_END):
        return stripped
    cut = max(stripped.rfind(". "), stripped.rfind("! "), stripped.rfind("? "))
    if cut == -1:
        # No sentence boundary at all — keep as-is rather than delete content.
        return stripped
    return stripped[: cut + 1]


def polish_blockquotes(body: str) -> str:
    """Apply truncation repair to every '> ' blockquote line."""
    out = []
    for line in body.split("\n"):
        if line.startswith("> "):
            content = line[2:]
            out.append("> " + trim_truncated(content))
        else:
            out.append(line)
    return "\n".join(out)


def polish(body: str) -> str:
    """Full normalization pass over one piece's markdown body."""
    for wrong, right in ACCENT_FIXES.items():
        body = body.replace(wrong, right)
    for english, portuguese in STAGE_LABELS.items():
        body = body.replace(f"**Estágio:** {english}", f"**Estágio:** {portuguese}")
    body = RAW_METRICS_RE.sub("", body)
    body = COMPANIES_LINE_RE.sub("", body)
    body = polish_blockquotes(body)
    # Collapse the blank-line runs the removals leave behind.
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip() + "\n"


def _get_session():
    import sys

    sys.path.insert(0, str(PROJECT_ROOT))
    from packages.database.session import get_session

    return get_session()


def fetch_prod_rows(slugs: list[str]) -> list[dict]:
    """Read the gap-week pieces straight from prod (read-only)."""
    import os

    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    import psycopg2
    from psycopg2.extras import RealDictCursor

    url = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT title, slug, subtitle, body_md, summary, content_type,
               agent_name, agent_run_id, sources, confidence_dq, confidence_ac,
               review_status, meta_description, canonical_url, metadata,
               author_name, created_at
        FROM content_pieces
        WHERE slug = ANY(%s)
        ORDER BY created_at
        """,
        (slugs,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def show_sample(rows: list[dict], slug: Optional[str] = None) -> None:
    target = slug or "social-signals-week-26"
    row = next((r for r in rows if r["slug"] == target), rows[0] if rows else None)
    if row is None:
        print("nenhuma peca encontrada")
        return
    before = row["body_md"] or ""
    after = polish(before)
    print(f"=== {row['slug']} ({row['created_at'].date()}) ===")
    print(f"tamanho: {len(before)} -> {len(after)} chars\n")
    print("---------- ANTES (primeiras 1400) ----------")
    print(before[:1400])
    print("\n---------- DEPOIS (primeiras 1400) ----------")
    print(after[:1400])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="preview only, no writes")
    ap.add_argument("--slug", default=None, help="slug to preview")
    ap.add_argument("--apply", action="store_true", help="write into the LOCAL db")
    args = ap.parse_args()

    slugs = [f"social-signals-week-{w}" for w in GAP_WEEKS]
    rows = fetch_prod_rows(slugs)
    print(f"peças encontradas em prod: {len(rows)}\n")

    if args.apply:
        import sys

        sys.path.insert(0, str(PROJECT_ROOT))
        from packages.database.models.content_piece import ContentPiece

        session = _get_session()
        created = updated = 0
        for row in rows:
            body = polish(row["body_md"] or "")
            existing = (
                session.query(ContentPiece).filter_by(slug=row["slug"]).first()
            )
            if existing is None:
                existing = ContentPiece(slug=row["slug"])
                session.add(existing)
                created += 1
            else:
                updated += 1
            existing.title = row["title"]
            existing.subtitle = row["subtitle"]
            existing.body_md = body
            existing.summary = row["summary"]
            existing.content_type = row["content_type"]
            existing.agent_name = row["agent_name"]
            existing.agent_run_id = row["agent_run_id"]
            existing.sources = row["sources"]
            existing.confidence_dq = row["confidence_dq"]
            existing.confidence_ac = row["confidence_ac"]
            existing.meta_description = row["meta_description"]
            existing.canonical_url = row["canonical_url"]
            existing.metadata_ = row["metadata"]
            existing.author_name = row["author_name"]
            existing.created_at = row["created_at"]
            # Publish with the date the intelligence was actually produced.
            existing.review_status = "published"
            existing.published_at = row["created_at"]
        session.commit()
        session.close()
        print(f"local: {created} criadas, {updated} atualizadas (published)")
        return

    show_sample(rows, args.slug)


if __name__ == "__main__":
    main()
