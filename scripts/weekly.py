#!/usr/bin/env python3
"""Weekly newsletter orchestrator.

Single CLI for the recurring ritual of assembling, reviewing, and publishing
a newsletter edition. Each subcommand is a step that can be re-run safely;
state lives in the DB (content_pieces.review_status, metadata).

Usage:
    python scripts/weekly.py status   --edition 57
    python scripts/weekly.py prepare  --edition 57
    python scripts/weekly.py generate --edition 57
    python scripts/weekly.py qa       --edition 57

    python scripts/weekly.py remove-item  --edition 57 --piece sinal-semanal-57 --item 5
    python scripts/weekly.py set-title    --edition 57 --title "..."
    python scripts/weekly.py set-subject  --edition 57 --subject "..."
    python scripts/weekly.py despublish   --edition 57 --piece index-week-19

    python scripts/weekly.py covers       --edition 57
    python scripts/weekly.py publish-local --edition 57
    python scripts/weekly.py preview       --edition 57 --to fabianoc@gmail.com
    python scripts/weekly.py sync-prod     --edition 57
    python scripts/weekly.py broadcast     --edition 57 \\
        --intelligence https://sinal.tech/intelligence/<slug> \\
        --article https://sinal.tech/artigos/<slug>
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("weekly")

# Pieces that compose a weekly edition (the ones the user reads on the site).
# INDEX is intentionally excluded — it is a data-discovery agent, not editorial.
EDITION_AGENTS = ["funding", "mercado", "codigo", "radar", "sintese"]

# Order matters: sintese aggregates highlights from the others, so it goes last.
GENERATE_ORDER = ["funding", "mercado", "codigo", "radar", "sintese"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugs_for_edition(edition: int, week: int) -> dict[str, str]:
    """Map agent name -> expected slug for a given (edition, week)."""
    return {
        "sintese": f"sinal-semanal-{edition}",
        "funding": f"funding-semanal-{week}",
        "mercado": f"mercado-week-{week}",
        "codigo": f"codigo-week-{week}",
        "radar": f"radar-week-{week}",
    }


def _get_session():
    """Return a SQLAlchemy session pointing at DATABASE_URL."""
    from packages.database.session import get_session
    return get_session()


def _get_pieces(session, edition: int, week: int) -> dict[str, "ContentPiece"]:  # type: ignore
    """Fetch all known pieces for this edition. Returns {agent: piece_or_None}."""
    from packages.database.models.content_piece import ContentPiece
    slugs = _slugs_for_edition(edition, week)
    out = {}
    for agent, slug in slugs.items():
        out[agent] = session.query(ContentPiece).filter_by(slug=slug).first()
    return out


def _resolve_week(edition: int, week: Optional[int]) -> int:
    """If week is given, use it. Otherwise infer from sintese piece."""
    if week is not None:
        return week
    # Heuristic: edition N often corresponds to week (N - 38) for 2026.
    # Better: fetch sintese piece if it exists and read week_number from metadata.
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        sintese = session.query(ContentPiece).filter_by(
            slug=f"sinal-semanal-{edition}"
        ).first()
        if sintese and sintese.metadata_ and "week_number" in sintese.metadata_:
            return int(sintese.metadata_["week_number"])
    finally:
        session.close()
    # Last resort: edition - 38 (works for 2026).
    return edition - 38


# ---------------------------------------------------------------------------
# Commands: read-only (status, qa)
# ---------------------------------------------------------------------------

def cmd_status(edition: int, week: Optional[int] = None) -> int:
    """Print a status table of all pieces for the edition."""
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        pieces = _get_pieces(session, edition, week)
        print(f"\nEdition #{edition} (week {week})")
        print("=" * 80)
        print(f"  {'agent':<10} {'status':<16} {'cover':<8} {'items':<7} title")
        print("-" * 80)
        for agent in EDITION_AGENTS:
            p = pieces.get(agent)
            if not p:
                print(f"  {agent:<10} {'(missing)':<16} {'-':<8} {'-':<7} -")
                continue
            meta = p.metadata_ or {}
            has_cover = "yes" if meta.get("hero_image") else "no"
            items_count = len(meta.get("items", [])) if meta.get("items") else "-"
            title = (p.title or "")[:55]
            print(f"  {agent:<10} {p.review_status:<16} {has_cover:<8} {str(items_count):<7} {title}")
        print()
        return 0
    finally:
        session.close()


QA_REVIEW_SYSTEM_PROMPT = """You are a senior editor reviewing the weekly newsletter \
for Sinal.lab — a LATAM tech intelligence publication for founders, CTOs, and senior \
engineers. The voice is sharp, opinionated, and operational: every paragraph should \
say something useful for a builder. The audience is fluent in Portuguese and \
technical English; both languages are fine.

You will receive the full body of one or more pieces from a single edition. Your \
job is to flag editorial problems that automated rules miss: tone repetition, \
self-promotion, weak hooks, items that feel like filler, sections where the lead \
paragraph is weaker than the bullets that follow, deals that are being treated \
as breaking news but are actually follow-ups from earlier coverage.

Output a brief report. Use this format:

## Verdict
One sentence: ready to ship / minor fixes / needs editorial pass.

## Issues by piece
For each issue:
- **[piece slug]** — what's wrong, in 1-2 sentences. Suggest the fix when obvious.

## Title and subject suggestions (sintese only)
If the current title or email subject is weak, suggest 2-3 alternatives that lead \
with substance, not a single company name. Keep subject under 90 chars.

Be specific and economical. Do NOT congratulate, do NOT summarize the content. \
Skip categories with no real issues."""


def cmd_qa_review(edition: int, week: Optional[int] = None) -> int:
    """Run an LLM-powered editorial review of all pieces.

    Complements `qa` (which is rule-based). This catches subjective issues:
    weak leads, self-promotion, repetitive tone, items that feel like filler.

    Costs ~$0.10 and ~30s per call (one Claude Opus call with all bodies).
    """
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        from apps.agents.base.llm import LLMClient
        client = LLMClient()
        if not client.is_available:
            print("  ANTHROPIC_API_KEY missing or anthropic SDK not installed.")
            return 1

        pieces = _get_pieces(session, edition, week)
        present = [(a, p) for a, p in pieces.items() if p is not None]
        if not present:
            print(f"  No pieces found for edition #{edition}.")
            return 1

        # Build the prompt: title + first 6000 chars of each body. Keep total
        # under ~30k chars so the call is fast.
        body_chunks = []
        for agent, p in present:
            meta = p.metadata_ or {}
            subj = meta.get("email_subject", "")
            body = (p.body_md or "")[:6000]
            body_chunks.append(
                f"### {p.slug} (agent={agent}, status={p.review_status})\n"
                f"Title: {p.title}\n"
                + (f"Email subject: {subj}\n" if subj else "")
                + f"\n{body}\n"
            )

        # Also pass the prior edition's sintese title and item URLs so the LLM
        # can detect cross-edition repetition.
        from packages.database.models.content_piece import ContentPiece
        prev = session.query(ContentPiece).filter_by(slug=f"sinal-semanal-{edition - 1}").first()
        prev_context = ""
        if prev and prev.metadata_:
            prev_items = prev.metadata_.get("items") or []
            prev_titles = [it.get("title") or "" for it in prev_items if it.get("title")]
            prev_urls = [it.get("url") or "" for it in prev_items if it.get("url")]
            prev_context = (
                f"\n## Prior edition context (#{edition - 1}, week {week - 1})\n"
                f"Title: {prev.title}\n"
                f"Items covered:\n" + "\n".join(f"- {t}" for t in prev_titles[:20]) + "\n"
                f"\nFlag any item in the current edition whose URL or topic significantly "
                f"overlaps with the prior edition (these may be follow-ups dressed as news).\n"
            )

        user_prompt = (
            f"Edition #{edition} (week {week}). Review the pieces below.\n\n"
            + prev_context
            + "\n\n## Current edition pieces\n\n"
            + "\n---\n\n".join(body_chunks)
        )

        print(f"  Asking Claude (this takes ~30s, costs ~$0.10)...\n")
        result = client.generate(
            user_prompt=user_prompt,
            system_prompt=QA_REVIEW_SYSTEM_PROMPT,
            max_tokens=2500,
            temperature=0.3,
        )
        if not result:
            print("  LLM call failed (check logs above).")
            return 1
        print(result)
        print()
        return 0
    finally:
        session.close()


def cmd_qa(edition: int, week: Optional[int] = None) -> int:
    """Run editorial QA rules across all pieces. Returns 0 if no errors, 1 otherwise."""
    week = _resolve_week(edition, week)
    session = _get_session()
    errors: list[tuple[str, str, str]] = []   # (severity, piece, msg)

    try:
        pieces = _get_pieces(session, edition, week)
        sintese = pieces.get("sintese")

        # Subject checks (sintese only)
        if sintese:
            meta = sintese.metadata_ or {}
            subj = meta.get("email_subject", "")
            if not subj:
                errors.append(("ERROR", "sintese", "email_subject is missing"))
            else:
                if len(subj) > 90:
                    errors.append(("WARN", "sintese", f"subject too long: {len(subj)} chars (>{90})"))
                if f"#{edition}" not in subj:
                    errors.append(("WARN", "sintese", f"subject missing edition number '#{edition}': '{subj[:60]}'"))
                if subj.lower().count(f"sinal semanal #{edition}") > 1:
                    errors.append(("ERROR", "sintese", f"subject has duplicate prefix: '{subj}'"))

        # Per-piece checks
        for agent, p in pieces.items():
            if not p:
                continue
            meta = p.metadata_ or {}
            body = p.body_md or ""

            # Cover image
            if p.review_status == "published" and not meta.get("hero_image"):
                errors.append(("ERROR", p.slug, "published without hero_image"))

            # Placeholder cover (Bloomberg/InfoQ/TheBlock images injected by agents)
            hero_url = (meta.get("hero_image") or {}).get("url", "")
            placeholder_hosts = ["bloomberglinea.com", "infoq.com", "tbstat.com", "cointelegraph.com"]
            if any(h in hero_url for h in placeholder_hosts):
                errors.append(("WARN", p.slug, f"hero_image looks like agent placeholder: {hero_url[:80]}"))

            # "Para [audience]" formula
            formula_count = sum(
                len(re.findall(rf"\b{phrase}\b", body, re.IGNORECASE))
                for phrase in ["Para founders", "Para fundadores", "Para CTOs", "Para CIOs",
                               "Para o ecossistema", "Para times de engenharia"]
            )
            if formula_count > 3:
                errors.append(("WARN", p.slug, f"'Para [audience]' formula appears {formula_count} times"))

            # Editorial grade
            er = (meta.get("editorial_review") or {})
            grade = er.get("grade", "")
            if p.review_status == "published" and grade and grade not in ("A", "B"):
                errors.append(("WARN", p.slug, f"published with editorial grade {grade}"))

            # Items count (sintese only)
            if agent == "sintese":
                items = meta.get("items") or []
                if len(items) < 12:
                    errors.append(("WARN", p.slug, f"only {len(items)} items in sintese metadata (<12)"))
                elif len(items) > 20:
                    errors.append(("WARN", p.slug, f"{len(items)} items in sintese metadata (>20)"))

                # Duplicate URLs within sintese items
                urls = [it.get("url") for it in items if it.get("url")]
                dupes = {u for u in urls if urls.count(u) > 1}
                if dupes:
                    errors.append(("ERROR", p.slug, f"duplicate URLs in items: {list(dupes)[:3]}"))

        # Cross-edition: items in this sintese that already appeared in edition N-1
        if sintese and (sintese.metadata_ or {}).get("items"):
            from packages.database.models.content_piece import ContentPiece
            prev = session.query(ContentPiece).filter_by(
                slug=f"sinal-semanal-{edition - 1}"
            ).first()
            if prev and prev.metadata_:
                prev_urls = {it.get("url") for it in (prev.metadata_.get("items") or [])
                             if it.get("url")}
                cur_urls = {it.get("url") for it in (sintese.metadata_.get("items") or [])
                            if it.get("url")}
                overlap = prev_urls & cur_urls
                if overlap:
                    errors.append(("WARN", "sintese",
                                   f"{len(overlap)} item URLs also appeared in edition #{edition - 1}: "
                                   f"{list(overlap)[:2]}"))

        # Report
        if not errors:
            print(f"\n  QA passed for edition #{edition} ({week=}). No issues found.\n")
            return 0
        print(f"\n  QA results for edition #{edition} ({week=}):\n")
        for sev, slug, msg in errors:
            sym = "✗" if sev == "ERROR" else "!"
            print(f"  [{sym} {sev:<5}] {slug:<22} {msg}")
        print()
        any_error = any(s == "ERROR" for s, _, _ in errors)
        return 1 if any_error else 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Commands: orchestration (prepare, generate, publish-local, despublish)
# ---------------------------------------------------------------------------

def cmd_prepare(edition: int, week: Optional[int] = None, force: bool = False) -> int:
    """Delete existing pieces/runs for this edition so it can be regenerated.

    By default refuses to delete pieces with review_status='published'.
    Pass --force to override.
    """
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        pieces = _get_pieces(session, edition, week)
        existing = [(a, p) for a, p in pieces.items() if p is not None]
        if not existing:
            print(f"  No existing pieces for edition #{edition} (week {week}). Nothing to clean.")
            return 0

        published = [p for _, p in existing if p.review_status == "published"]
        if published and not force:
            print(f"  Refusing to delete: {len(published)} piece(s) are 'published'.")
            print("  Re-run with --force to delete anyway.")
            for p in published:
                print(f"    - {p.slug}")
            return 1

        from packages.database.models.agent_run import AgentRun
        for agent, p in existing:
            run_id = p.agent_run_id
            print(f"  Deleting {p.slug} (status={p.review_status}, agent={agent})")
            session.delete(p)
            if run_id:
                ar = session.query(AgentRun).filter_by(run_id=run_id).first()
                if ar:
                    session.delete(ar)
        session.commit()
        print(f"  Cleaned {len(existing)} piece(s) for edition #{edition}.")
        return 0
    finally:
        session.close()


def cmd_generate(edition: int, week: Optional[int] = None, only: Optional[list[str]] = None,
                 skip_editorial: bool = False) -> int:
    """Run the agents that compose the edition, in dependency order.

    Wraps `scripts/run_agents.py <agent> --orchestrate`. Each agent is a
    subprocess so a failure of one doesn't kill the rest.
    """
    week = _resolve_week(edition, week)
    targets = only or GENERATE_ORDER
    invalid = [t for t in targets if t not in GENERATE_ORDER]
    if invalid:
        print(f"  Unknown agent(s): {invalid}")
        return 1

    failures: list[str] = []
    for agent in targets:
        period_arg = "--edition" if agent == "sintese" else "--week"
        period_val = str(edition) if agent == "sintese" else str(week)
        cmd = [
            sys.executable, "scripts/run_agents.py", agent,
            period_arg, period_val,
            "--orchestrate",
        ]
        if skip_editorial:
            cmd.append("--no-editorial")
        print(f"\n  → {agent.upper()} ({' '.join(cmd[2:])})")
        rc = subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode
        if rc != 0:
            print(f"  ✗ {agent} failed (exit {rc}). Stopping.")
            failures.append(agent)
            return 2

    print(f"\n  ✓ Generated {len(targets)} agent(s) for edition #{edition}.")
    return 0


def cmd_publish_local(edition: int, week: Optional[int] = None) -> int:
    """Move pieces from review_status='approved' to 'published'."""
    from datetime import datetime, timezone
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        pieces = _get_pieces(session, edition, week)
        updated = 0
        for agent, p in pieces.items():
            if p is None:
                print(f"  (skip) {agent}: no piece")
                continue
            if p.review_status == "published":
                print(f"  (skip) {p.slug}: already published")
                continue
            if p.review_status != "approved":
                print(f"  (skip) {p.slug}: status='{p.review_status}' (need 'approved')")
                continue
            p.review_status = "published"
            p.published_at = datetime.now(timezone.utc)
            updated += 1
            print(f"  ✓ published {p.slug}")
        if updated:
            session.commit()
        print(f"\n  Updated {updated} piece(s).")
        return 0
    finally:
        session.close()


def cmd_despublish(edition: int, piece: str, week: Optional[int] = None) -> int:
    """Reverse publish-local for a specific piece (status='approved', clears published_at)."""
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        p = session.query(ContentPiece).filter_by(slug=piece).first()
        if not p:
            print(f"  Piece not found: {piece}")
            return 1
        if p.review_status != "published":
            print(f"  {piece} is not published (status={p.review_status})")
            return 1
        p.review_status = "approved"
        p.published_at = None
        session.commit()
        print(f"  ✓ Despublished {piece}")
        return 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Commands: edit (remove-item, set-title, set-subject)
# ---------------------------------------------------------------------------

def cmd_remove_item(edition: int, piece: str, item: int, week: Optional[int] = None) -> int:
    """Remove item N from the body of a piece. Renumbers remaining items.

    Items are matched by leading "**N. [TITLE](URL)**" pattern in body_md.
    Also drops the matching entry from metadata.items if present.
    """
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        from sqlalchemy.orm.attributes import flag_modified
        p = session.query(ContentPiece).filter_by(slug=piece).first()
        if not p:
            print(f"  Piece not found: {piece}")
            return 1
        body = p.body_md or ""

        pattern = re.compile(
            rf"\*\*{item}\. \[([^\]]+)\]\(([^)]+)\)\*\*.*?(?=\n\*\*\d+\. \[|\n## |\Z)",
            re.DOTALL,
        )
        m = pattern.search(body)
        if not m:
            print(f"  Item #{item} not found in {piece} body")
            return 1

        removed_url = m.group(2)
        removed_title = m.group(1)
        new_body = body[:m.start()] + body[m.end():]

        # Renumber items > item: decrement by 1
        def renum(match):
            n = int(match.group(1))
            if n > item:
                return f"**{n - 1}. ["
            return match.group(0)
        new_body = re.sub(r"\*\*(\d+)\. \[", renum, new_body)
        new_body = re.sub(r"\n{3,}", "\n\n", new_body)

        # Drop from metadata.items if present
        meta = dict(p.metadata_ or {})
        items = meta.get("items") or []
        before = len(items)
        items = [it for it in items if (it.get("url") or "") != removed_url]
        if len(items) != before:
            meta["items"] = items
            meta["item_count"] = len(items)

        p.body_md = new_body
        p.body_html = None  # force re-render on next read
        p.metadata_ = meta
        flag_modified(p, "metadata_")
        session.commit()
        print(f"  ✓ Removed item #{item} from {piece}: {removed_title[:60]}")
        return 0
    finally:
        session.close()


def cmd_set_title(edition: int, title: str, week: Optional[int] = None) -> int:
    """Set the sintese piece title (also visible at /newsletter/sinal-semanal-N)."""
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        p = session.query(ContentPiece).filter_by(slug=f"sinal-semanal-{edition}").first()
        if not p:
            print(f"  Sintese not found for edition #{edition}")
            return 1
        old = p.title
        p.title = title
        session.commit()
        print(f"  ✓ Title updated for sinal-semanal-{edition}")
        print(f"    old: {old[:70]}")
        print(f"    new: {title[:70]}")
        return 0
    finally:
        session.close()


def cmd_set_subject(edition: int, subject: str, week: Optional[int] = None) -> int:
    """Set the email subject (stored in sintese metadata.email_subject)."""
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        from sqlalchemy.orm.attributes import flag_modified
        p = session.query(ContentPiece).filter_by(slug=f"sinal-semanal-{edition}").first()
        if not p:
            print(f"  Sintese not found for edition #{edition}")
            return 1
        meta = dict(p.metadata_ or {})
        meta["email_subject"] = subject
        p.metadata_ = meta
        flag_modified(p, "metadata_")
        session.commit()
        print(f"  ✓ email_subject updated for sinal-semanal-{edition}: '{subject}'")
        return 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Commands: wrappers around existing scripts
# ---------------------------------------------------------------------------

def cmd_covers(edition: int, week: Optional[int] = None) -> int:
    """Generate cover images for any piece in this edition that lacks one."""
    cmd = [sys.executable, "scripts/generate_covers.py"]
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode


def cmd_preview(edition: int, to: str, week: Optional[int] = None) -> int:
    """Send a single preview email via the briefing path of publish_newsletter."""
    week = _resolve_week(edition, week)
    cmd = [
        sys.executable, "scripts/publish_newsletter.py", "briefing",
        "--edition", str(edition),
        "--week", str(week),
        "--recipient", to,
    ]
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode


def cmd_sync_prod(edition: int, week: Optional[int] = None, dry_run: bool = False) -> int:
    """Sync the edition's content_pieces from local to prod via sync_local_to_prod.py."""
    week = _resolve_week(edition, week)

    # Patch SLUGS_TO_SYNC for this edition by setting an env hint the sync
    # script can pick up. The sync script currently has hardcoded slugs, so
    # we monkey-patch via a small wrapper.
    slugs = list(_slugs_for_edition(edition, week).values())
    print(f"  Slugs to sync: {slugs}")
    print("  NOTE: scripts/sync_local_to_prod.py currently has hardcoded SLUGS_TO_SYNC.")
    print("  Open that file and update the list for this edition before running, then:")
    print(f"    PROD_DATABASE_URL=$PROD_DATABASE_URL python3 scripts/sync_local_to_prod.py "
          f"{'--dry-run' if dry_run else ''} --only content")
    return 0


def cmd_broadcast(edition: int, intelligence: Optional[str], article: Optional[str],
                  week: Optional[int] = None) -> int:
    """Trigger the production broadcast via publish_newsletter."""
    week = _resolve_week(edition, week)
    cmd = [
        sys.executable, "scripts/publish_newsletter.py", "broadcast",
        "--edition", str(edition),
        "--week", str(week),
    ]
    if intelligence:
        cmd += ["--intelligence", intelligence]
    if article:
        # publish_newsletter ARTICLE_HIGHLIGHTS is a per-edition registry edit,
        # not a flag. Print a reminder.
        print(f"  NOTE: --article wants {article}")
        print(f"  Make sure ARTICLE_HIGHLIGHTS[{edition}] is set in scripts/publish_newsletter.py.")
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode


# ---------------------------------------------------------------------------
# Commands: LLM-backed suggestions (suggest-title, suggest-subject,
# rewrite-hook, suggest-removals). All output-only — they never modify
# the DB. Apply with set-title / set-subject / remove-item if you like
# what you see.
# ---------------------------------------------------------------------------

_SUGGEST_SYSTEM = """You are a senior editor for Sinal.lab, a LATAM tech \
intelligence newsletter for founders, CTOs, and senior engineers. The voice \
is sharp, opinionated, operational. The audience reads Portuguese fluently \
and is comfortable with technical English; mix is fine. Avoid em dashes \
(—); use commas, colons, or periods to separate ideas."""


def _llm_or_die() -> "LLMClient":  # type: ignore
    from apps.agents.base.llm import LLMClient
    client = LLMClient()
    if not client.is_available:
        print("  ANTHROPIC_API_KEY missing or anthropic SDK not installed.")
        sys.exit(1)
    return client


def cmd_suggest_title(edition: int, count: int = 3, week: Optional[int] = None) -> int:
    """Ask Claude for N alternative titles for the sintese piece."""
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        sintese = session.query(ContentPiece).filter_by(slug=f"sinal-semanal-{edition}").first()
        if not sintese:
            print(f"  No sintese for edition #{edition}.")
            return 1

        meta = sintese.metadata_ or {}
        items = meta.get("items") or []
        item_titles = "\n".join(
            f"- {(it.get('title') or '')[:120]}"
            for it in items[:18] if it.get("title")
        )
        # Use the first ~3000 chars of body as editorial lead context.
        lead = (sintese.body_md or "")[:3000]

        client = _llm_or_die()
        user_prompt = (
            f"Edition #{edition}, week {week}.\n\n"
            f"Current title: {sintese.title}\n\n"
            f"Lead paragraph(s) of the edition:\n{lead}\n\n"
            f"Item headlines covered in this edition:\n{item_titles}\n\n"
            f"Propose {count} alternative titles for this edition. Each title should:\n"
            f"- lead with substance, not with a single company name (avoid 'Nubank does X' framings)\n"
            f"- connect 2-3 of the strongest tensions in the edition\n"
            f"- be under 130 characters\n"
            f"- not promote any specific company\n\n"
            f"Output format:\n"
            f"## Option 1\n<title>\n*Why:* one sentence on what this title leads with and what it omits.\n\n"
            f"## Option 2\n...\n\n"
            f"Be specific. No preamble."
        )
        print(f"  Asking Claude for {count} title options...\n")
        out = client.generate(user_prompt=user_prompt, system_prompt=_SUGGEST_SYSTEM,
                              max_tokens=1500, temperature=0.6)
        if not out:
            print("  LLM call failed.")
            return 1
        print(out)
        print(f"\n  To apply: weekly set-title --edition {edition} --title \"...\"")
        return 0
    finally:
        session.close()


def cmd_suggest_subject(edition: int, count: int = 3, week: Optional[int] = None) -> int:
    """Ask Claude for N alternative email subjects."""
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        sintese = session.query(ContentPiece).filter_by(slug=f"sinal-semanal-{edition}").first()
        if not sintese:
            print(f"  No sintese for edition #{edition}.")
            return 1

        meta = sintese.metadata_ or {}
        current_subj = meta.get("email_subject", "")
        lead = (sintese.body_md or "")[:2000]

        client = _llm_or_die()
        user_prompt = (
            f"Edition #{edition}.\n\n"
            f"Current title: {sintese.title}\n"
            f"Current subject: {current_subj or '(none)'}\n\n"
            f"Lead of the edition:\n{lead}\n\n"
            f"Propose {count} alternative email subjects. Constraints:\n"
            f"- prefix 'Sinal Semanal #{edition}: ' is added automatically by the renderer\n"
            f"  so DO NOT include it in your suggestions\n"
            f"- the subject text after the prefix should be under 70 characters so the\n"
            f"  full subject (with prefix) stays under ~90 chars\n"
            f"- ideal mobile preview shows the first ~30-40 chars after the prefix —\n"
            f"  put the strongest hook there\n"
            f"- avoid promoting a single company; lead with a tension or a number\n\n"
            f"Output format:\n"
            f"## Option 1\n<subject text without prefix>\n*chars (without prefix):* N\n\n"
            f"## Option 2\n...\n\n"
            f"Be specific. No preamble."
        )
        print(f"  Asking Claude for {count} subject options...\n")
        out = client.generate(user_prompt=user_prompt, system_prompt=_SUGGEST_SYSTEM,
                              max_tokens=1000, temperature=0.6)
        if not out:
            print("  LLM call failed.")
            return 1
        print(out)
        print(f"\n  To apply: weekly set-subject --edition {edition} --subject \"...\"")
        return 0
    finally:
        session.close()


def cmd_rewrite_hook(piece: str, item: int, count: int = 3) -> int:
    """Ask Claude to rewrite the opening hook of a specific blockquote.

    Useful when the LLM-generated commentary opens with the same formula
    multiple times (e.g. 'Para founders LATAM, ...'). Keeps the substance,
    varies the lead.
    """
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        p = session.query(ContentPiece).filter_by(slug=piece).first()
        if not p:
            print(f"  Piece not found: {piece}")
            return 1
        body = p.body_md or ""

        # Find the blockquote tied to item N: pattern "**N. [...]**\n*Fonte: ...*\n> ..."
        pattern = re.compile(
            rf"\*\*{item}\. \[([^\]]+)\]\([^)]+\)\*\*\s*\n"
            rf"(?:\*[^\n]+\*\s*\n)?"
            rf"(> [^\n]+)",
            re.MULTILINE,
        )
        m = pattern.search(body)
        if not m:
            print(f"  Item #{item} (with blockquote) not found in {piece}")
            return 1
        item_title = m.group(1)
        current_quote = m.group(2)

        # Sample 2 neighboring blockquotes for tone context
        all_quotes = re.findall(r"^> [^\n]+", body, re.MULTILINE)
        try:
            cur_idx = all_quotes.index(current_quote)
            neighbors = []
            if cur_idx > 0:
                neighbors.append(all_quotes[cur_idx - 1])
            if cur_idx + 1 < len(all_quotes):
                neighbors.append(all_quotes[cur_idx + 1])
        except ValueError:
            neighbors = []

        client = _llm_or_die()
        user_prompt = (
            f"Piece: {piece}, item #{item}.\n"
            f"Item title: {item_title}\n\n"
            f"Current blockquote (to rewrite):\n{current_quote}\n\n"
            + (f"Neighbor blockquotes (for tone):\n" + "\n".join(neighbors) + "\n\n"
               if neighbors else "")
            + f"Rewrite this blockquote {count} different ways. Constraints:\n"
            f"- keep the SAME factual claims and analytical conclusion\n"
            f"- vary the OPENING hook — do not start with 'Para founders/CTOs/fundadores'\n"
            f"- alternative openers to try: a number, a comparison, a counterintuitive\n"
            f"  claim, an operational consequence, a question, a contrast with a known\n"
            f"  case\n"
            f"- preserve length (within ±20%)\n"
            f"- single line, no internal blank lines\n"
            f"- start with '> ' (Markdown blockquote)\n\n"
            f"Output format:\n"
            f"## Option 1\n<blockquote starting with '> '>\n*Hook:* one phrase naming the rhetorical move used\n\n"
            f"## Option 2\n...\n\n"
            f"No preamble."
        )
        print(f"  Asking Claude for {count} rewrite options...\n")
        out = client.generate(user_prompt=user_prompt, system_prompt=_SUGGEST_SYSTEM,
                              max_tokens=1500, temperature=0.7)
        if not out:
            print("  LLM call failed.")
            return 1
        print(out)
        print(f"\n  To apply, replace the blockquote in {piece}'s body_md manually")
        print(f"  (no automation yet — paste your chosen option in psql or via a quick UPDATE).")
        return 0
    finally:
        session.close()


def cmd_suggest_removals(edition: int, week: Optional[int] = None) -> int:
    """Ask Claude which items to consider cutting from the edition."""
    week = _resolve_week(edition, week)
    session = _get_session()
    try:
        from packages.database.models.content_piece import ContentPiece
        sintese = session.query(ContentPiece).filter_by(slug=f"sinal-semanal-{edition}").first()
        if not sintese:
            print(f"  No sintese for edition #{edition}.")
            return 1
        meta = sintese.metadata_ or {}
        items = meta.get("items") or []
        if not items:
            print(f"  Sintese has no items in metadata.")
            return 1

        # Prior edition context: items + title for follow-up detection
        prev = session.query(ContentPiece).filter_by(slug=f"sinal-semanal-{edition - 1}").first()
        prev_block = ""
        if prev and prev.metadata_:
            prev_titles = [(it.get("title") or "")[:100]
                           for it in (prev.metadata_.get("items") or [])
                           if it.get("title")]
            prev_block = (
                f"\n## Prior edition #{edition - 1} items (for follow-up detection)\n"
                + "\n".join(f"- {t}" for t in prev_titles[:25]) + "\n"
            )

        item_lines = []
        for i, it in enumerate(items, start=1):
            title = (it.get("title") or "(no title)")[:140]
            source = it.get("source") or ""
            url = it.get("url") or ""
            item_lines.append(f"{i}. {title}  [source={source}, url={url}]")
        items_block = "\n".join(item_lines)

        client = _llm_or_die()
        user_prompt = (
            f"Edition #{edition}, week {week}. {len(items)} items currently in sintese.\n\n"
            f"## Current items\n{items_block}\n"
            + prev_block
            + f"\n\nIdentify items that are weak fits for THIS edition and worth removing. "
            f"Reasons might include: (a) duplicates a topic from the prior edition without "
            f"adding new substance, (b) tangential to LATAM tech / founders / CTOs / engineers, "
            f"(c) promotional or PR-like, (d) thin on facts.\n\n"
            f"Sintese typically holds 12-16 items. Don't suggest cuts just to hit a number — "
            f"only flag items that genuinely don't earn their slot.\n\n"
            f"Output format:\n"
            f"## Items to consider cutting\n"
            f"- **#K** [title] — one-sentence reason. Suggested action: cut / rewrite as follow-up / keep but renumber.\n\n"
            f"If everything earns its slot, say so plainly. No preamble."
        )
        print(f"  Asking Claude to review {len(items)} items...\n")
        out = client.generate(user_prompt=user_prompt, system_prompt=_SUGGEST_SYSTEM,
                              max_tokens=1500, temperature=0.4)
        if not out:
            print("  LLM call failed.")
            return 1
        print(out)
        print(f"\n  To apply: weekly remove-item --edition {edition} --piece sinal-semanal-{edition} --item K")
        return 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Argparse plumbing
# ---------------------------------------------------------------------------

def _add_edition(p: argparse.ArgumentParser) -> None:
    p.add_argument("--edition", type=int, required=True, help="Newsletter edition number")
    p.add_argument("--week", type=int, default=None, help="ISO week number (auto-detected if omitted)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly newsletter orchestrator")
    parser.add_argument("--verbose", "-v", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="Print status table for the edition")
    _add_edition(p_status)

    p_qa = sub.add_parser("qa", help="Run editorial QA rules (rule-based by default; --review uses LLM)")
    _add_edition(p_qa)
    p_qa.add_argument("--review", action="store_true",
                      help="Use Claude for a deeper editorial review (slower, costs ~$0.10)")

    p_prepare = sub.add_parser("prepare", help="Delete existing pieces so the edition can be regenerated")
    _add_edition(p_prepare)
    p_prepare.add_argument("--force", action="store_true", help="Allow deletion of published pieces")

    p_generate = sub.add_parser("generate", help="Run the agents that compose the edition")
    _add_edition(p_generate)
    p_generate.add_argument("--only", nargs="+", choices=GENERATE_ORDER,
                            help="Only run a subset (default: all)")
    p_generate.add_argument("--no-editorial", action="store_true",
                            help="Skip editorial review (faster, less safe)")

    p_publish = sub.add_parser("publish-local", help="Move approved pieces to published")
    _add_edition(p_publish)

    p_desp = sub.add_parser("despublish", help="Despublish a single piece (status->approved)")
    _add_edition(p_desp)
    p_desp.add_argument("--piece", type=str, required=True, help="Slug of the piece")

    p_rm = sub.add_parser("remove-item", help="Remove item #N from a piece's body")
    _add_edition(p_rm)
    p_rm.add_argument("--piece", type=str, required=True, help="Slug of the piece")
    p_rm.add_argument("--item", type=int, required=True, help="Item number (as shown in body)")

    p_title = sub.add_parser("set-title", help="Set sintese title")
    _add_edition(p_title)
    p_title.add_argument("--title", type=str, required=True)

    p_subj = sub.add_parser("set-subject", help="Set email subject")
    _add_edition(p_subj)
    p_subj.add_argument("--subject", type=str, required=True)

    p_covers = sub.add_parser("covers", help="Generate cover images for pieces without one")
    _add_edition(p_covers)

    p_preview = sub.add_parser("preview", help="Send a single preview email (briefing mode)")
    _add_edition(p_preview)
    p_preview.add_argument("--to", type=str, required=True, help="Recipient email")

    p_sync = sub.add_parser("sync-prod", help="Sync this edition's pieces to prod (dry-run by default)")
    _add_edition(p_sync)
    p_sync.add_argument("--execute", action="store_true", help="Actually run (otherwise dry-run)")

    p_bcast = sub.add_parser("broadcast", help="Send broadcast via Resend")
    _add_edition(p_bcast)
    p_bcast.add_argument("--intelligence", type=str, default=None, help="Intelligence report URL")
    p_bcast.add_argument("--article", type=str, default=None, help="Article highlight URL (informational)")

    # LLM-backed suggestions (output-only, never modify the DB)
    p_st = sub.add_parser("suggest-title", help="Ask Claude for N alternative titles")
    _add_edition(p_st)
    p_st.add_argument("--count", type=int, default=3, help="Number of options to generate")

    p_ss = sub.add_parser("suggest-subject", help="Ask Claude for N alternative email subjects")
    _add_edition(p_ss)
    p_ss.add_argument("--count", type=int, default=3, help="Number of options to generate")

    p_rh = sub.add_parser("rewrite-hook",
                          help="Ask Claude to rewrite the opening of a blockquote")
    p_rh.add_argument("--piece", type=str, required=True, help="Slug of the piece")
    p_rh.add_argument("--item", type=int, required=True, help="Item number with the blockquote")
    p_rh.add_argument("--count", type=int, default=3, help="Number of rewrite options")

    p_sr = sub.add_parser("suggest-removals", help="Ask Claude which items to consider cutting")
    _add_edition(p_sr)

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [weekly] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    cmd = args.cmd
    if cmd == "status":
        return cmd_status(args.edition, args.week)
    if cmd == "qa":
        if args.review:
            return cmd_qa_review(args.edition, args.week)
        return cmd_qa(args.edition, args.week)
    if cmd == "prepare":
        return cmd_prepare(args.edition, args.week, force=args.force)
    if cmd == "generate":
        return cmd_generate(args.edition, args.week, only=args.only,
                            skip_editorial=args.no_editorial)
    if cmd == "publish-local":
        return cmd_publish_local(args.edition, args.week)
    if cmd == "despublish":
        return cmd_despublish(args.edition, args.piece, args.week)
    if cmd == "remove-item":
        return cmd_remove_item(args.edition, args.piece, args.item, args.week)
    if cmd == "set-title":
        return cmd_set_title(args.edition, args.title, args.week)
    if cmd == "set-subject":
        return cmd_set_subject(args.edition, args.subject, args.week)
    if cmd == "covers":
        return cmd_covers(args.edition, args.week)
    if cmd == "preview":
        return cmd_preview(args.edition, args.to, args.week)
    if cmd == "sync-prod":
        return cmd_sync_prod(args.edition, args.week, dry_run=not args.execute)
    if cmd == "broadcast":
        return cmd_broadcast(args.edition, args.intelligence, args.article, args.week)
    if cmd == "suggest-title":
        return cmd_suggest_title(args.edition, count=args.count, week=args.week)
    if cmd == "suggest-subject":
        return cmd_suggest_subject(args.edition, count=args.count, week=args.week)
    if cmd == "rewrite-hook":
        return cmd_rewrite_hook(args.piece, args.item, count=args.count)
    if cmd == "suggest-removals":
        return cmd_suggest_removals(args.edition, args.week)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
