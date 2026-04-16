"""Processing pipeline for the PULSO agent.

Orchestrates the clustering and scoring workflow. Unlike social_signals,
PULSO receives pre-collected, pre-classified signals from VOZES. The
pipeline starts at clustering, not collection.

Pipeline flow:
    cluster_signals() -> score_clusters() -> determine_stages() ->
    extract_top_content() -> build_pulse()
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from apps.agents.base.llm import LLMClient
from apps.agents.pulso.clusterer import (
    cluster_signals,
    cluster_signals_with_embeddings,
    compute_cluster_centroid,
    describe_cluster,
)
from apps.agents.pulso.config import (
    CLUSTERING_DISTANCE_THRESHOLD,
    EMBEDDING_DISTANCE_THRESHOLD,
    MIN_CLUSTER_SIZE,
)
from apps.agents.pulso.models import (
    PipelineResult,
    ProcessedSignal,
    SignalClusterResult,
)
from apps.agents.pulso.scorer import (
    assign_narrative_stages_by_percentile,
    compute_cluster_dimensions,
    determine_narrative_stage,
    extract_top_posts,
    extract_top_voices,
)

logger = logging.getLogger(__name__)


def _build_previous_period_data(
    previous_clusters: Optional[List[SignalClusterResult]],
) -> Tuple[Dict[str, int], Dict[str, float], Set[str]]:
    """Extract aggregated metrics from previous-period clusters.

    Returns:
        Tuple of (theme_counts, theme_sentiments, known_authors).
    """
    theme_counts: Dict[str, int] = defaultdict(int)
    theme_sentiments: Dict[str, float] = defaultdict(float)
    theme_signal_counts: Dict[str, int] = defaultdict(int)
    known_authors: Set[str] = set()

    if not previous_clusters:
        return theme_counts, theme_sentiments, known_authors

    for cluster in previous_clusters:
        theme = cluster.theme or "other"
        theme_counts[theme] += cluster.signal_count

        for signal in cluster.signals:
            theme_sentiments[theme] += signal.sentiment
            theme_signal_counts[theme] += 1

            if signal.post.author_handle:
                known_authors.add(signal.post.author_handle)

    for theme in theme_sentiments:
        count = theme_signal_counts.get(theme, 1)
        theme_sentiments[theme] = theme_sentiments[theme] / max(count, 1)

    return theme_counts, theme_sentiments, known_authors


def run_pipeline(
    signals: List[ProcessedSignal],
    llm_client: Optional[LLMClient] = None,
    previous_clusters: Optional[List[SignalClusterResult]] = None,
    historical_context: Optional[Dict[str, Any]] = None,
    signal_embeddings: Optional[Dict[str, List[float]]] = None,
    distance_threshold: float = CLUSTERING_DISTANCE_THRESHOLD,
    min_cluster_size: int = MIN_CLUSTER_SIZE,
    skip_embeddings: bool = False,
) -> PipelineResult:
    """Execute the PULSO processing pipeline.

    Unlike social_signals, this receives pre-classified ProcessedSignals
    (from VOZES) and starts at clustering.

    Steps:
        1. Cluster related signals (embedding-based or TF-IDF)
        2. Score each cluster's 8 dimensions (with historical context)
        3. Determine narrative lifecycle stage per cluster
        4. Extract top voices and top posts per cluster
        5. Extract related companies from entity mentions
        6. Generate cluster descriptions

    Args:
        signals: Pre-classified ProcessedSignals from VOZES.
        llm_client: Optional LLM client for cluster labeling.
        previous_clusters: Clusters from previous period for velocity.
        historical_context: Pre-built historical context dict.
        signal_embeddings: Pre-computed embeddings (content_hash -> vector).
        distance_threshold: Clustering distance threshold.
        min_cluster_size: Minimum signals per cluster.
        skip_embeddings: If True, use TF-IDF only.

    Returns:
        PipelineResult with clusters, signals, and metadata.
    """
    if not signals:
        logger.warning("Pipeline received 0 signals, returning empty results")
        return PipelineResult()

    # Filter to signals with a theme assigned
    themed_signals = [s for s in signals if s.theme]
    logger.info(
        "Pipeline starting with %d signals (%d themed)",
        len(signals), len(themed_signals),
    )

    if not themed_signals:
        logger.warning("No themed signals, returning empty clusters")
        return PipelineResult(all_signals=signals)

    # Step 1: Cluster signals
    embeddings = signal_embeddings or {}
    if embeddings and not skip_embeddings:
        logger.info("Step 1/6: Embedding-clustering %d signals...", len(themed_signals))
        clusters = cluster_signals_with_embeddings(
            themed_signals,
            embeddings,
            llm_client=llm_client,
            distance_threshold=EMBEDDING_DISTANCE_THRESHOLD,
            min_cluster_size=min_cluster_size,
        )
    else:
        logger.info("Step 1/6: TF-IDF clustering %d signals...", len(themed_signals))
        clusters = cluster_signals(
            themed_signals,
            llm_client=llm_client,
            distance_threshold=distance_threshold,
            min_cluster_size=min_cluster_size,
        )

    # Build historical lookups
    has_historical_data = False
    if historical_context:
        prev_counts = historical_context.get("theme_counts", {})
        prev_sentiments = historical_context.get("theme_sentiments", {})
        known_authors = historical_context.get("known_authors", set())
        hist_weeks_active = historical_context.get("weeks_active", {})
        has_historical_data = bool(prev_counts)
    else:
        prev_counts, prev_sentiments, known_authors = _build_previous_period_data(
            previous_clusters,
        )
        hist_weeks_active: Dict[str, int] = {}
        has_historical_data = bool(prev_counts)

    # Steps 2-6: Score, stage, enrich clusters
    logger.info("Steps 2-6/6: Scoring and enriching %d clusters...", len(clusters))
    for cluster in clusters:
        theme = cluster.theme or "other"

        # Step 2: Compute 8-dimension scores
        cluster.dimensions = compute_cluster_dimensions(
            signals=cluster.signals,
            previous_count=prev_counts.get(theme, 0),
            previous_sentiment=prev_sentiments.get(theme, 0.0),
            known_authors=known_authors,
        )

        # Step 3: Determine narrative stage
        weeks_active = hist_weeks_active.get(theme, 1)
        if not hist_weeks_active and theme in prev_counts:
            weeks_active = 2
        cluster.narrative_stage = determine_narrative_stage(
            cluster.dimensions,
            weeks_active=weeks_active,
            has_historical_data=has_historical_data,
        )

        # Step 4: Extract top voices and posts
        cluster.top_voices = extract_top_voices(cluster.signals, limit=10)
        cluster.top_posts = extract_top_posts(cluster.signals, limit=10)

        # Step 5: Extract related companies from entity mentions
        company_mentions: Dict[str, int] = defaultdict(int)
        for signal in cluster.signals:
            for entity in signal.entities:
                if entity.entity_type == "company":
                    company_mentions[entity.name] += 1

        cluster.related_companies = [
            {"name": name, "mention_count": count}
            for name, count in sorted(
                company_mentions.items(), key=lambda x: x[1], reverse=True,
            )[:10]
        ]

        # Step 6: Generate cluster description
        cluster.description = describe_cluster(
            cluster.signals, cluster.name, llm_client,
        )

        # Compute platform distribution
        cluster.compute_platform_distribution()

        # Compute centroid embedding
        if embeddings:
            centroid = compute_cluster_centroid(cluster.signals, embeddings)
            if centroid:
                cluster._centroid_embedding = centroid  # type: ignore[attr-defined]

    # Percentile-based stages when no historical data
    if not has_historical_data:
        assign_narrative_stages_by_percentile(clusters, has_historical_data=False)

    # Sort by composite score descending
    clusters.sort(key=lambda c: c.composite_score, reverse=True)

    logger.info(
        "Pipeline complete: %d clusters from %d signals. Top: %s (score=%.3f, stage=%s)",
        len(clusters),
        len(themed_signals),
        clusters[0].name if clusters else "none",
        clusters[0].composite_score if clusters else 0.0,
        clusters[0].narrative_stage if clusters else "n/a",
    )

    return PipelineResult(
        clusters=clusters,
        all_signals=signals,
        signal_embeddings=embeddings,
    )
