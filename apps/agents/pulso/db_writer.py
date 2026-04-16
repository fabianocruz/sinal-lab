"""Database persistence for the PULSO agent.

Handles upsert of SignalCluster and WeeklyPulse records. Unlike
social_signals, PULSO does NOT persist individual SocialSignal records
(that is VOZES' responsibility).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from apps.agents.pulso.config import CLUSTER_NAME_BLOCKLIST, MIN_CLUSTER_COMPOSITE_SCORE
from apps.agents.pulso.models import ProcessedSignal, SignalClusterResult

logger = logging.getLogger(__name__)

# Cache for pgvector availability
_pgvector_checked: Optional[bool] = None


def _is_pgvector_available(session: Session) -> bool:
    """Check if pgvector extension and vector columns exist."""
    global _pgvector_checked
    if _pgvector_checked is not None:
        return _pgvector_checked

    try:
        from apps.agents.social_signals.similarity import check_pgvector_available
        _pgvector_checked = check_pgvector_available(session)
    except Exception:
        _pgvector_checked = False

    return _pgvector_checked


def _update_pgvector_column(
    session: Session,
    record_id: str,
    embedding: List[float],
    table_name: str,
) -> None:
    """Update the pgvector column for a record. No-op if pgvector unavailable."""
    if not _is_pgvector_available(session):
        return

    column_name = "centroid_vector"
    embedding_str = "[" + ",".join(str(f) for f in embedding) + "]"

    try:
        session.execute(
            text(
                f"UPDATE {table_name} SET {column_name} = :vec "
                f"WHERE id = :rid::uuid"
            ),
            {"vec": embedding_str, "rid": record_id},
        )
    except Exception:
        logger.warning(
            "Failed to update pgvector column %s.%s for %s",
            table_name, column_name, record_id,
            exc_info=True,
        )


def _upsert_signal_cluster(
    session: Session,
    cluster: SignalClusterResult,
    week_number: int,
    year: int,
    agent_run_id: str = "",
) -> str:
    """Upsert a SignalCluster record by slug.

    Returns UUID string of the upserted cluster.
    """
    from packages.database.models.signal_cluster import SignalCluster

    slug = f"{cluster.slug}-{year}-w{week_number:02d}"
    now = datetime.now(timezone.utc)

    existing = session.query(SignalCluster).filter_by(slug=slug).first()

    dimensions_dict = cluster.dimensions.to_dict() if cluster.dimensions else {}
    composite = cluster.composite_score

    top_voices = cluster.top_voices[:10] if cluster.top_voices else []
    top_posts = cluster.top_posts[:10] if cluster.top_posts else []
    related_companies = cluster.related_companies[:10] if cluster.related_companies else []

    centroid_embedding: Optional[List[float]] = getattr(cluster, "_centroid_embedding", None)

    if existing:
        existing.name = cluster.name
        existing.theme = cluster.theme
        existing.sub_theme = cluster.sub_theme
        existing.description = cluster.description or existing.description
        existing.signal_count = cluster.signal_count
        existing.composite_score = composite
        existing.dimensions = dimensions_dict
        existing.narrative_stage = cluster.narrative_stage
        existing.top_voices = top_voices
        existing.top_posts = top_posts
        existing.related_companies = related_companies
        existing.last_active_at = now
        existing.agent_run_id = agent_run_id
        existing.updated_at = now

        flag_modified(existing, "dimensions")
        flag_modified(existing, "top_voices")
        flag_modified(existing, "top_posts")
        flag_modified(existing, "related_companies")

        if centroid_embedding:
            existing.centroid_embedding_json = centroid_embedding
            flag_modified(existing, "centroid_embedding_json")
            _update_pgvector_column(session, str(existing.id), centroid_embedding, "signal_clusters")

        return str(existing.id)

    cluster_id = uuid4()
    record = SignalCluster(
        id=cluster_id,
        name=cluster.name,
        slug=slug,
        theme=cluster.theme,
        sub_theme=cluster.sub_theme,
        description=cluster.description,
        signal_count=cluster.signal_count,
        composite_score=composite,
        dimensions=dimensions_dict,
        narrative_stage=cluster.narrative_stage,
        first_seen_at=now,
        last_active_at=now,
        top_voices=top_voices,
        top_posts=top_posts,
        related_companies=related_companies,
        centroid_embedding_json=centroid_embedding,
        week_number=week_number,
        year=year,
        agent_run_id=agent_run_id,
    )
    session.add(record)

    if centroid_embedding:
        session.flush()
        _update_pgvector_column(session, str(cluster_id), centroid_embedding, "signal_clusters")

    return str(cluster_id)


def _upsert_weekly_pulse(
    session: Session,
    clusters: List[SignalClusterResult],
    week_number: int,
    year: int,
    agent_run_id: str = "",
) -> str:
    """Upsert a WeeklyPulse record for the given week.

    Returns "inserted" or "updated".
    """
    from packages.database.models.weekly_pulse import WeeklyPulse

    slug = f"pulse-{year}-w{week_number:02d}"
    now = datetime.now(timezone.utc)

    existing = session.query(WeeklyPulse).filter_by(slug=slug).first()

    def _is_quality_cluster(c: SignalClusterResult) -> bool:
        if c.composite_score < MIN_CLUSTER_COMPOSITE_SCORE:
            return False
        name_lower = (c.name or "").lower()
        return not any(p in name_lower for p in CLUSTER_NAME_BLOCKLIST)

    quality_clusters = [c for c in clusters if _is_quality_cluster(c)]

    accelerating = [
        {"name": c.name, "score": round(c.composite_score, 3), "signals": c.signal_count}
        for c in quality_clusters if c.narrative_stage == "accelerating"
    ][:5]

    emerging = [
        {"name": c.name, "score": round(c.composite_score, 3), "platforms": c.platforms}
        for c in quality_clusters if c.narrative_stage == "emerging"
    ][:5]

    all_top_posts: List[Dict[str, Any]] = []
    for c in quality_clusters:
        all_top_posts.extend(c.top_posts[:3])
    all_top_posts = all_top_posts[:10]

    seen_handles: set = set()
    all_voices: List[Dict[str, Any]] = []
    for c in quality_clusters:
        for v in c.top_voices:
            handle = v.get("handle", "")
            if handle and handle not in seen_handles:
                seen_handles.add(handle)
                all_voices.append(v)
    all_voices = all_voices[:10]

    # Startups to watch: use full company name (cross-reference if available)
    company_counts: Dict[str, int] = {}
    for c in quality_clusters:
        for comp in c.related_companies:
            name = comp.get("name", "")
            count = comp.get("mention_count", 1)
            company_counts[name] = company_counts.get(name, 0) + count

    # Try to enrich with full company names from the companies table
    enriched_names = _enrich_company_names(session, list(company_counts.keys()))

    startups_to_watch = [
        {"name": enriched_names.get(name, name), "mentions": count}
        for name, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
    ][:10]

    if existing:
        existing.accelerating_themes = accelerating
        existing.emerging_signals = emerging
        existing.top_posts = all_top_posts
        existing.top_voices = all_voices
        existing.startups_to_watch = startups_to_watch
        existing.generated_at = now
        existing.agent_run_id = agent_run_id
        existing.status = "draft"
        existing.updated_at = now

        flag_modified(existing, "accelerating_themes")
        flag_modified(existing, "emerging_signals")
        flag_modified(existing, "top_posts")
        flag_modified(existing, "top_voices")
        flag_modified(existing, "startups_to_watch")

        return "updated"

    record = WeeklyPulse(
        id=uuid4(),
        week_number=week_number,
        year=year,
        slug=slug,
        accelerating_themes=accelerating,
        emerging_signals=emerging,
        top_posts=all_top_posts,
        top_voices=all_voices,
        startups_to_watch=startups_to_watch,
        generated_at=now,
        agent_run_id=agent_run_id,
        status="draft",
    )
    session.add(record)
    return "inserted"


def _enrich_company_names(
    session: Session,
    short_names: List[str],
) -> Dict[str, str]:
    """Cross-reference entity mention names against the companies table.

    Returns a mapping of short_name -> full_name for matches found.
    """
    if not short_names:
        return {}

    try:
        from packages.database.models.company import Company

        result: Dict[str, str] = {}
        for name in short_names:
            match = (
                session.query(Company.name)
                .filter(Company.name.ilike(f"%{name}%"))
                .first()
            )
            if match:
                result[name] = match[0]
        return result
    except Exception:
        logger.debug("Company enrichment unavailable, using raw names")
        return {}


def persist_pulso_data(
    agent: Any,
    agent_output: Any,
    session: Session,
) -> None:
    """Domain persistence callback for the orchestrator.

    Signature: (agent, agent_output, session) -> None.

    Persists:
        1. SignalCluster records (one per cluster)
        2. WeeklyPulse record (one per week)

    Note: Individual SocialSignal records are NOT persisted here.
    That is VOZES' responsibility.
    """
    clusters: List[SignalClusterResult] = getattr(agent, "_clusters", [])
    week_number: int = getattr(agent, "week_number", 1)
    run_id: str = getattr(agent, "run_id", "")

    now = datetime.now(timezone.utc)
    year = now.year

    stats = {
        "clusters_upserted": 0,
        "pulse": "none",
    }

    # Step 1: Upsert clusters
    for cluster in clusters:
        _upsert_signal_cluster(
            session, cluster, week_number, year, run_id,
        )
        stats["clusters_upserted"] += 1

    # Step 2: Upsert weekly pulse
    if clusters:
        stats["pulse"] = _upsert_weekly_pulse(
            session, clusters, week_number, year, run_id,
        )

    session.flush()

    logger.info(
        "PULSO persistence complete: %d clusters upserted, pulse=%s",
        stats["clusters_upserted"],
        stats["pulse"],
    )
