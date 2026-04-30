#!/usr/bin/env python3
"""Retroactive fix for signal_clusters data quality.

Applies the same fixes from fix/signals-quality branch to existing data
in the database without re-running the full agent pipeline.

Fixes applied:
    1. Narrative stages — redistribute by percentile (per week) instead
       of all "accelerating"
    2. HTML stripping — remove HTML tags from cluster descriptions
    3. Duplicate merge — merge clusters with identical base slugs in the
       same week
    4. Weekly pulse — rebuild accelerating/emerging lists from fixed data

Usage:
    # Dry run (preview changes)
    python scripts/fix_signal_clusters.py --dry-run

    # Apply to production
    DATABASE_URL=<url> python scripts/fix_signal_clusters.py
"""

import re
import sys
from collections import defaultdict
from contextlib import closing
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.database.models.signal_cluster import SignalCluster
from packages.database.models.weekly_pulse import WeeklyPulse
from packages.database.session import get_session


def strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def fix_narrative_stages(session, dry_run: bool = False) -> int:
    """Redistribute narrative stages by percentile per week.

    Groups clusters by (year, week_number), then assigns stages
    based on composite_score rank within each week:
        - Top 15%: accelerating
        - Next 35%: emerging
        - Next 35%: peaking
        - Bottom 15%: declining
    """
    clusters = (
        session.query(SignalCluster)
        .filter(SignalCluster.composite_score.isnot(None))
        .order_by(SignalCluster.year, SignalCluster.week_number)
        .all()
    )

    if not clusters:
        print("  No clusters found")
        return 0

    # Group by week
    by_week: dict = defaultdict(list)
    for c in clusters:
        key = (c.year, c.week_number)
        by_week[key].append(c)

    updated = 0
    for (year, week), week_clusters in by_week.items():
        # Sort by composite score descending
        week_clusters.sort(key=lambda c: c.composite_score or 0, reverse=True)
        n = len(week_clusters)

        old_stages = [c.narrative_stage for c in week_clusters]

        for i, cluster in enumerate(week_clusters):
            pct = i / n
            if pct < 0.15:
                new_stage = "accelerating"
            elif pct < 0.50:
                new_stage = "emerging"
            elif pct < 0.85:
                new_stage = "peaking"
            else:
                new_stage = "declining"

            if cluster.narrative_stage != new_stage:
                cluster.narrative_stage = new_stage
                updated += 1

        new_stages = [c.narrative_stage for c in week_clusters]
        if old_stages != new_stages:
            from collections import Counter
            dist = Counter(new_stages)
            print(f"  Week {year}-W{week:02d} ({n} clusters): {dict(dist)}")

    if not dry_run:
        session.flush()

    return updated


def fix_html_descriptions(session, dry_run: bool = False) -> int:
    """Strip HTML tags from cluster descriptions."""
    clusters = (
        session.query(SignalCluster)
        .filter(SignalCluster.description.isnot(None))
        .all()
    )

    updated = 0
    for cluster in clusters:
        if not cluster.description:
            continue
        clean = strip_html(cluster.description)
        if clean != cluster.description:
            if dry_run:
                print(f"  [{cluster.slug}] {cluster.description[:60]}...")
                print(f"    -> {clean[:60]}...")
            cluster.description = clean
            updated += 1

    if not dry_run:
        session.flush()

    return updated


def merge_duplicate_clusters(session, dry_run: bool = False) -> int:
    """Merge clusters with identical base slugs in the same week.

    The slug format is "{name}-{year}-w{week}". Two clusters with the
    same slug are duplicates that should have been merged by the pipeline.
    """
    clusters = session.query(SignalCluster).all()

    # Group by slug
    by_slug: dict = defaultdict(list)
    for c in clusters:
        by_slug[c.slug].append(c)

    merged = 0
    for slug, group in by_slug.items():
        if len(group) <= 1:
            continue

        # Keep the one with highest composite score, delete the rest
        group.sort(key=lambda c: c.composite_score or 0, reverse=True)
        primary = group[0]

        for duplicate in group[1:]:
            print(f"  Merge: {duplicate.slug} (score={duplicate.composite_score:.3f}) "
                  f"-> {primary.slug} (score={primary.composite_score:.3f})")
            # Combine signal counts
            primary.signal_count = (primary.signal_count or 0) + (duplicate.signal_count or 0)

            if not dry_run:
                session.delete(duplicate)
            merged += 1

    if not dry_run:
        session.flush()

    return merged


def rebuild_weekly_pulse(session, dry_run: bool = False) -> int:
    """Rebuild accelerating/emerging lists from updated cluster data."""
    from apps.agents.social_signals.config import (
        CLUSTER_NAME_BLOCKLIST_RE,
        MIN_CLUSTER_COMPOSITE_SCORE,
    )

    pulses = session.query(WeeklyPulse).all()
    updated = 0

    for pulse in pulses:
        clusters = (
            session.query(SignalCluster)
            .filter(
                SignalCluster.week_number == pulse.week_number,
                SignalCluster.year == pulse.year,
            )
            .all()
        )

        # Quality filter
        quality = [
            c for c in clusters
            if (c.composite_score or 0) >= MIN_CLUSTER_COMPOSITE_SCORE
            and not CLUSTER_NAME_BLOCKLIST_RE.search(c.name or "")
        ]

        accelerating = [
            {"name": c.name, "score": round(c.composite_score or 0, 3), "signals": c.signal_count}
            for c in quality if c.narrative_stage == "accelerating"
        ][:5]

        emerging = [
            {"name": c.name, "score": round(c.composite_score or 0, 3)}
            for c in quality if c.narrative_stage == "emerging"
        ][:5]

        if pulse.accelerating_themes != accelerating or pulse.emerging_signals != emerging:
            old_acc = len(pulse.accelerating_themes or [])
            old_emg = len(pulse.emerging_signals or [])
            pulse.accelerating_themes = accelerating
            pulse.emerging_signals = emerging
            updated += 1
            print(f"  Pulse {pulse.slug}: accelerating {old_acc}->{len(accelerating)}, "
                  f"emerging {old_emg}->{len(emerging)}")

    if not dry_run:
        session.flush()

    return updated


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN (no changes will be saved) ===\n")

    with closing(get_session()) as session:
        try:
            # 1. Fix narrative stages
            print("1. Fixing narrative stages (percentile-based)...")
            stage_count = fix_narrative_stages(session, dry_run)
            print(f"   -> {stage_count} clusters updated\n")

            # 2. Strip HTML from descriptions
            print("2. Stripping HTML from descriptions...")
            html_count = fix_html_descriptions(session, dry_run)
            print(f"   -> {html_count} descriptions cleaned\n")

            # 3. Merge duplicate clusters
            print("3. Merging duplicate clusters...")
            merge_count = merge_duplicate_clusters(session, dry_run)
            print(f"   -> {merge_count} duplicates merged\n")

            # 4. Rebuild weekly pulse
            print("4. Rebuilding weekly pulse data...")
            pulse_count = rebuild_weekly_pulse(session, dry_run)
            print(f"   -> {pulse_count} pulses updated\n")

            # Summary
            total = stage_count + html_count + merge_count + pulse_count
            print(f"Total changes: {total}")

            if dry_run:
                print("\nRe-run without --dry-run to apply changes.")
                session.rollback()
            else:
                session.commit()
                print("\nAll changes committed successfully.")

        except Exception as e:
            session.rollback()
            print(f"\nError: {e}")
            raise


if __name__ == "__main__":
    main()
