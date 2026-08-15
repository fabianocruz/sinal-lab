"""Database persistence for the Social Signals Intelligence agent.

Handles upsert of SocialSignal, SignalCluster, and WeeklyPulse records.
Follows the same pattern as apps/agents/index/db_writer.py: the main
entry point (persist_social_signals) is passed as domain_persist_fn
to the orchestrator.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from apps.agents.social_signals.models import (
    ProcessedSignal,
    SignalClusterResult,
)

logger = logging.getLogger(__name__)

# Cache for pgvector availability (avoids repeated queries)
_pgvector_checked: Optional[bool] = None


def _is_pgvector_available(session: Session) -> bool:
    """Check if pgvector extension and vector columns exist.

    Caches result for process lifetime.
    """
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
    """Update the pgvector column for a record using raw SQL.

    No-op if pgvector is not available. Errors are logged but do not
    propagate (graceful degradation).

    Args:
        session: SQLAlchemy session.
        record_id: UUID string of the record.
        embedding: Embedding vector (1536 floats).
        table_name: "social_signals" or "signal_clusters".
    """
    if not _is_pgvector_available(session):
        return

    column_name = "embedding_vector" if table_name == "social_signals" else "centroid_vector"
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


def _upsert_social_signal(
    session: Session,
    signal: ProcessedSignal,
    cluster_db_id: Optional[str] = None,
    agent_run_id: str = "",
    embedding: Optional[List[float]] = None,
) -> str:
    """Upsert a single SocialSignal record by content_hash.

    Args:
        session: SQLAlchemy session (not committed).
        signal: ProcessedSignal from pipeline.
        cluster_db_id: UUID string of the parent SignalCluster.
        agent_run_id: Current agent run ID.
        embedding: Optional embedding vector (1536 floats) to persist.

    Returns:
        "inserted" or "updated"
    """
    from packages.database.models.social_signal import SocialSignal

    existing = (
        session.query(SocialSignal)
        .filter_by(content_hash=signal.content_hash)
        .first()
    )

    entities_json = [
        {"name": e.name, "type": e.entity_type, "confidence": e.confidence}
        for e in signal.entities
    ]

    now = datetime.now(timezone.utc)

    if existing:
        # Update classification and scoring (may have improved)
        existing.theme = signal.theme or existing.theme
        existing.sub_theme = signal.sub_theme or existing.sub_theme
        existing.entities = entities_json or existing.entities
        existing.sentiment = signal.sentiment
        existing.authority_score = signal.authority_score
        existing.cluster_id = cluster_db_id or existing.cluster_id
        existing.agent_run_id = agent_run_id or existing.agent_run_id
        existing.updated_at = now

        if entities_json:
            flag_modified(existing, "entities")

        # Update embedding if provided (new or improved)
        if embedding:
            existing.embedding_json = embedding
            flag_modified(existing, "embedding_json")
            _update_pgvector_column(session, str(existing.id), embedding, "social_signals")

        return "updated"

    record = SocialSignal(
        id=uuid4(),
        platform=signal.post.platform,
        post_url=signal.post.url,
        author_handle=signal.post.author_handle,
        author_display_name=signal.post.author_display_name,
        text=signal.post.text[:2000] if signal.post.text else None,
        content_hash=signal.content_hash,
        published_at=signal.post.published_at,
        collected_at=now,
        metrics=signal.post.metrics,
        theme=signal.theme,
        sub_theme=signal.sub_theme,
        entities=entities_json,
        sentiment=signal.sentiment,
        authority_score=signal.authority_score,
        embedding_json=embedding,
        cluster_id=cluster_db_id,
        agent_run_id=agent_run_id,
    )
    session.add(record)

    # Set pgvector column if available (needs the record to exist first)
    if embedding:
        session.flush()
        _update_pgvector_column(session, str(record.id), embedding, "social_signals")

    return "inserted"


def _upsert_signal_cluster(
    session: Session,
    cluster: SignalClusterResult,
    week_number: int,
    year: int,
    agent_run_id: str = "",
) -> str:
    """Upsert a SignalCluster record by slug.

    Uses a composite slug of "{original_slug}-{year}-w{week}" to ensure
    uniqueness per time period.

    Args:
        session: SQLAlchemy session (not committed).
        cluster: SignalClusterResult from pipeline.
        week_number: ISO week number.
        year: Year.
        agent_run_id: Current agent run ID.

    Returns:
        UUID string of the upserted cluster (for linking signals).
    """
    from apps.agents.base.cluster_identity import find_cluster_by_membership
    from packages.database.models.signal_cluster import SignalCluster

    slug = f"{cluster.slug}-{year}-w{week_number:02d}"
    now = datetime.now(timezone.utc)

    # Identity comes from the signals the cluster holds, not from the label
    # the LLM produced this run. Without this, a re-worded name means a new
    # slug and therefore an INSERT, which is how one bucket became ~27 rows
    # a week. Fall back to the slug lookup so a cluster whose membership is
    # not yet recorded still updates in place.
    content_hashes = {
        h for h in (getattr(s, "content_hash", None) for s in cluster.signals) if h
    }
    existing = find_cluster_by_membership(session, content_hashes, year, week_number)
    matched_by_membership = existing is not None
    if existing is None:
        existing = session.query(SignalCluster).filter_by(slug=slug).first()

    dimensions_dict = cluster.dimensions.to_dict() if cluster.dimensions else {}
    composite = cluster.composite_score

    top_voices = cluster.top_voices[:10] if cluster.top_voices else []
    top_posts = cluster.top_posts[:10] if cluster.top_posts else []
    related_companies = cluster.related_companies[:10] if cluster.related_companies else []

    # Get centroid embedding if computed during pipeline
    centroid_embedding: Optional[List[float]] = getattr(cluster, "_centroid_embedding", None)

    if existing:
        # When the match came from membership, the name and slug already in
        # the database are the ones the site has been showing and linking to.
        # Keep them: a cluster that renames itself every 6h is the same
        # instability in a different place, and the /signals/cluster/<slug>
        # URL would break on every run.
        if not matched_by_membership:
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
        # Refresh the identity fingerprint so the next run compares against
        # this run's membership, letting a cluster drift as the week fills.
        existing.signal_hashes = sorted(content_hashes)

        flag_modified(existing, "signal_hashes")
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
        signal_hashes=sorted(content_hashes),
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

    # Force the INSERT to flush now so we can catch UniqueViolation here
    # (rare case: query.first() returned None but the row exists — happens
    # when SQLAlchemy session cache is stale or when another process
    # inserted between query and add). Fall back to UPDATE.
    from sqlalchemy.exc import IntegrityError
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = session.query(SignalCluster).filter_by(slug=slug).first()
        if existing is None:
            raise  # genuine conflict, not a stale-cache miss
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

    if centroid_embedding:
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

    Args:
        session: SQLAlchemy session (not committed).
        clusters: All scored clusters from pipeline.
        week_number: ISO week number.
        year: Year.
        agent_run_id: Current agent run ID.

    Returns:
        "inserted" or "updated"
    """
    from packages.database.models.weekly_pulse import WeeklyPulse

    slug = f"pulse-{year}-w{week_number:02d}"
    now = datetime.now(timezone.utc)

    existing = session.query(WeeklyPulse).filter_by(slug=slug).first()

    # Quality filter: exclude low-score and blocklist-matching clusters
    from apps.agents.social_signals.config import CLUSTER_NAME_BLOCKLIST, MIN_CLUSTER_COMPOSITE_SCORE

    def _is_quality_cluster(c: SignalClusterResult) -> bool:
        if c.composite_score < MIN_CLUSTER_COMPOSITE_SCORE:
            return False
        name_lower = (c.name or "").lower()
        return not any(p in name_lower for p in CLUSTER_NAME_BLOCKLIST)

    quality_clusters = [c for c in clusters if _is_quality_cluster(c)]

    # Build structured data from quality-filtered clusters
    accelerating = [
        {"name": c.name, "score": round(c.composite_score, 3), "signals": c.signal_count}
        for c in quality_clusters if c.narrative_stage == "accelerating"
    ][:5]

    emerging = [
        {"name": c.name, "score": round(c.composite_score, 3), "platforms": c.platforms}
        for c in quality_clusters if c.narrative_stage == "emerging"
    ][:5]

    # Aggregate top posts across quality clusters
    all_top_posts: List[Dict[str, Any]] = []
    for c in quality_clusters:
        all_top_posts.extend(c.top_posts[:3])
    all_top_posts = all_top_posts[:10]

    # Aggregate top voices (dedup by handle)
    seen_handles: set = set()
    all_voices: List[Dict[str, Any]] = []
    for c in quality_clusters:
        for v in c.top_voices:
            handle = v.get("handle", "")
            if handle and handle not in seen_handles:
                seen_handles.add(handle)
                all_voices.append(v)
    all_voices = all_voices[:10]

    # Companies to watch
    company_counts: Dict[str, int] = {}
    for c in quality_clusters:
        for comp in c.related_companies:
            name = comp.get("name", "")
            count = comp.get("mention_count", 1)
            company_counts[name] = company_counts.get(name, 0) + count

    startups_to_watch = [
        {"name": name, "mentions": count}
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


def persist_social_signals(
    agent: Any,
    agent_output: Any,
    session: Session,
) -> None:
    """Domain persistence callback for the orchestrator.

    Matches the signature expected by orchestrator's domain_persist_fn:
    (agent, agent_output, session) -> None.

    Persists:
        1. SignalCluster records (one per cluster)
        2. SocialSignal records (one per classified post)
        3. WeeklyPulse record (one per week)

    Args:
        agent: SocialSignalsAgent instance.
        agent_output: AgentOutput from agent.output().
        session: SQLAlchemy session (caller manages commit/rollback).
    """
    clusters: List[SignalClusterResult] = getattr(agent, "_clusters", [])
    all_signals: List[ProcessedSignal] = getattr(agent, "_all_signals", [])
    week_number: int = getattr(agent, "week_number", 1)
    run_id: str = getattr(agent, "run_id", "")

    # Get embeddings from the last pipeline run
    try:
        from apps.agents.social_signals.pipeline import get_last_signal_embeddings
        signal_embeddings = get_last_signal_embeddings()
    except ImportError:
        signal_embeddings = {}

    now = datetime.now(timezone.utc)
    year = now.year

    stats = {
        "clusters_upserted": 0,
        "signals_inserted": 0,
        "signals_updated": 0,
        "pulse": "none",
    }

    # Step 1: Upsert clusters and build slug -> db_id mapping
    cluster_db_ids: Dict[str, str] = {}
    for cluster in clusters:
        db_id = _upsert_signal_cluster(
            session, cluster, week_number, year, run_id,
        )
        cluster_db_ids[cluster.slug] = db_id
        stats["clusters_upserted"] += 1

    # Step 2: Upsert individual signals
    # Build signal -> cluster_slug mapping
    signal_hash_to_cluster: Dict[str, str] = {}
    for cluster in clusters:
        for signal in cluster.signals:
            signal_hash_to_cluster[signal.content_hash] = cluster.slug

    for signal in all_signals:
        cluster_slug = signal_hash_to_cluster.get(signal.content_hash)
        cluster_db_id = cluster_db_ids.get(cluster_slug) if cluster_slug else None

        embedding = signal_embeddings.get(signal.content_hash)
        result = _upsert_social_signal(
            session, signal, cluster_db_id=cluster_db_id,
            agent_run_id=run_id, embedding=embedding,
        )
        if result == "inserted":
            stats["signals_inserted"] += 1
        else:
            stats["signals_updated"] += 1

    # Step 3: Upsert weekly pulse
    if clusters:
        stats["pulse"] = _upsert_weekly_pulse(
            session, clusters, week_number, year, run_id,
        )

    session.flush()

    logger.info(
        "Social Signals persistence complete: %d clusters, "
        "%d signals inserted, %d updated, pulse=%s",
        stats["clusters_upserted"],
        stats["signals_inserted"],
        stats["signals_updated"],
        stats["pulse"],
    )
