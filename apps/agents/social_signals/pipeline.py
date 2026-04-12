"""Processing pipeline for the Social Signals Intelligence agent.

Orchestrates the full signal processing workflow:
    1. Batch-classify all posts (keyword-first, LLM for top N only)
    2. Filter posts with no theme assigned
    3. Compute cross-platform propagation scores
    4. Cluster related signals
    5. Score each cluster's 8 dimensions (with historical context)
    6. Determine narrative stage per cluster
    7. Extract top voices and top posts per cluster
    8. Return (clusters, all_processed_signals)

The pipeline is stateless: all previous-period data is passed in via
the previous_clusters parameter for velocity and sentiment shift computations.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from apps.agents.base.llm import LLMClient
from apps.agents.social_signals.classifier import classify_post, classify_posts_batch
from apps.agents.social_signals.clusterer import (
    cluster_signals,
    cluster_signals_with_embeddings,
    compute_cluster_centroid,
    describe_cluster,
)
from apps.agents.social_signals.embeddings import generate_embeddings
from apps.agents.social_signals.first_mover import detect_first_movers
from apps.agents.social_signals.models import (
    PipelineResult,
    ProcessedSignal,
    SignalClusterResult,
    SocialPost,
)
from apps.agents.social_signals.narrative_shift import detect_narrative_shifts
from apps.agents.social_signals.propagation import enrich_signals_with_propagation
from apps.agents.social_signals.scorer import (
    assign_narrative_stages_by_percentile,
    compute_cluster_dimensions,
    determine_narrative_stage,
    extract_top_posts,
    extract_top_voices,
    strip_html,
)

logger = logging.getLogger(__name__)

# Module-level storage for embeddings generated during the last pipeline run.
# The db_writer reads this to persist embeddings alongside signal records.
_last_signal_embeddings: Dict[str, List[float]] = {}

# Module-level storage for narrative shifts detected during the last pipeline run.
# The agent reads this to include in output metadata and trigger alerts.
_last_narrative_shifts: List[Dict[str, Any]] = []

# Module-level storage for first mover data detected during the last pipeline run.
_last_first_movers: Dict[str, Any] = {}


def get_last_signal_embeddings() -> Dict[str, List[float]]:
    """Return embeddings from the last pipeline run.

    Used by db_writer to persist embedding_json on SocialSignal records.
    """
    return dict(_last_signal_embeddings)


def get_last_narrative_shifts() -> List[Dict[str, Any]]:
    """Return narrative shifts from the last pipeline run.

    Used by the agent to include shift data in output metadata and
    to trigger alerts for significant narrative changes.
    """
    return list(_last_narrative_shifts)


def get_last_first_movers() -> Dict[str, Any]:
    """Return first mover data from the last pipeline run.

    Used by the agent to include first mover analysis in output
    metadata for the 'Who Started It' section.
    """
    return dict(_last_first_movers)


def _build_previous_period_data(
    previous_clusters: Optional[List[SignalClusterResult]],
) -> Tuple[Dict[str, int], Dict[str, float], Set[str]]:
    """Extract aggregated metrics from previous-period clusters.

    Builds three lookup structures used for velocity, sentiment shift,
    and new entrant computations in the current period.

    Args:
        previous_clusters: Clusters from the previous run (week N-1).

    Returns:
        Tuple of:
            - theme_counts: Dict[theme -> signal count] from previous period
            - theme_sentiments: Dict[theme -> avg sentiment] from previous period
            - known_authors: Set of author handles seen in previous period
    """
    theme_counts: Dict[str, int] = defaultdict(int)
    theme_sentiments: Dict[str, float] = defaultdict(float)
    theme_signal_counts_for_avg: Dict[str, int] = defaultdict(int)
    known_authors: Set[str] = set()

    if not previous_clusters:
        return theme_counts, theme_sentiments, known_authors

    for cluster in previous_clusters:
        theme = cluster.theme or "other"
        theme_counts[theme] += cluster.signal_count

        for signal in cluster.signals:
            theme_sentiments[theme] += signal.sentiment
            theme_signal_counts_for_avg[theme] += 1

            if signal.post.author_handle:
                known_authors.add(signal.post.author_handle)

    # Convert sentiment sums to averages
    for theme in theme_sentiments:
        count = theme_signal_counts_for_avg.get(theme, 1)
        theme_sentiments[theme] = theme_sentiments[theme] / max(count, 1)

    return theme_counts, theme_sentiments, known_authors


def run_pipeline(
    posts: List[SocialPost],
    llm_client: Optional[LLMClient] = None,
    previous_clusters: Optional[List[SignalClusterResult]] = None,
    historical_context: Optional[Dict[str, Any]] = None,
    distance_threshold: float = 0.5,
    min_cluster_size: int = 5,
    top_n_for_llm: int = 20,
    force_tfidf_embeddings: bool = False,
    skip_embeddings: bool = False,
) -> PipelineResult:
    """Execute the full social signals processing pipeline.

    Steps:
        1. Batch-classify all posts (keyword-first, LLM for top N only)
        2. Filter out posts with no theme assigned
        2.5. Generate embeddings for themed signals
        3. Compute cross-platform propagation scores
        4. Cluster related signals (embedding-based or TF-IDF fallback)
        5. Score each cluster's 8 dimensions (with historical context)
        6. Determine narrative lifecycle stage per cluster
        7. Extract top voices and top posts per cluster
        8. Extract related companies from entity mentions

    Args:
        posts: Raw SocialPost items from the collector.
        llm_client: Optional LLM client for high-quality classification
            and cluster labeling. Falls back to keyword-based methods.
        previous_clusters: Clusters from the previous period (week N-1)
            for computing velocity, sentiment shift, and new entrants.
            Used when historical_context is not provided.
        historical_context: Pre-built historical context from
            historical.build_historical_context(). If provided, takes
            precedence over previous_clusters for velocity/sentiment data.
        distance_threshold: Clustering distance threshold (passed to clusterer).
        min_cluster_size: Minimum signals per cluster (passed to clusterer).
        top_n_for_llm: Number of top posts to enrich with LLM (default 20).
        force_tfidf_embeddings: If True, use TF-IDF for embeddings instead
            of OpenAI. Useful for testing or cost control.
        skip_embeddings: If True, skip embedding generation entirely and
            use classic TF-IDF clustering. Useful for quick runs.

    Returns:
        PipelineResult containing clusters, signals, embeddings,
        narrative shifts, and first mover data.
    """
    if not posts:
        logger.warning("Pipeline received 0 posts, returning empty results")
        return PipelineResult()

    # Step 1: Batch-classify all posts (keyword-first, LLM for top N)
    logger.info("Step 1/8: Batch-classifying %d posts (LLM top %d)...", len(posts), top_n_for_llm)
    all_signals = classify_posts_batch(
        posts, llm_client=llm_client, top_n_for_llm=top_n_for_llm,
    )

    # Step 2: Filter posts with theme assigned
    themed_signals = [s for s in all_signals if s.theme]
    logger.info(
        "Step 2/8: Filtered to %d themed signals (dropped %d without theme)",
        len(themed_signals),
        len(all_signals) - len(themed_signals),
    )

    if not themed_signals:
        logger.warning("No signals matched any theme, returning empty clusters")
        return PipelineResult(all_signals=all_signals)

    # Step 2.5: Generate embeddings for themed signals
    signal_embeddings: Dict[str, List[float]] = {}
    if not skip_embeddings:
        logger.info("Step 2.5/9: Generating embeddings for %d signals...", len(themed_signals))
        try:
            signal_embeddings = generate_embeddings(
                themed_signals, force_tfidf=force_tfidf_embeddings,
            )
            logger.info(
                "Generated %d embeddings (%.0f%% coverage)",
                len(signal_embeddings),
                (len(signal_embeddings) / len(themed_signals) * 100) if themed_signals else 0,
            )
        except Exception:
            logger.exception("Embedding generation failed, continuing without embeddings")
            signal_embeddings = {}
    else:
        logger.info("Step 2.5/9: Skipping embedding generation (skip_embeddings=True)")

    # Step 3: Compute cross-platform propagation scores
    logger.info("Step 3/9: Computing cross-platform propagation scores...")
    propagation_scores = enrich_signals_with_propagation(themed_signals)

    # Step 4: Cluster related signals (embedding-based when available)
    if signal_embeddings and not skip_embeddings:
        logger.info("Step 4/9: Embedding-clustering %d signals...", len(themed_signals))
        # Use lower distance threshold for embeddings (more semantically precise)
        emb_threshold = min(distance_threshold, 0.5)
        clusters = cluster_signals_with_embeddings(
            themed_signals,
            signal_embeddings,
            llm_client=llm_client,
            distance_threshold=emb_threshold,
            min_cluster_size=min_cluster_size,
        )
    else:
        logger.info("Step 4/9: TF-IDF clustering %d signals...", len(themed_signals))
        clusters = cluster_signals(
            themed_signals,
            llm_client=llm_client,
            distance_threshold=distance_threshold,
            min_cluster_size=min_cluster_size,
        )

    # Build previous-period lookups from historical_context or previous_clusters
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
        hist_weeks_active = {}
        has_historical_data = bool(prev_counts)

    # Steps 5-9: Score, stage, enrich, and compute centroids
    logger.info("Step 5-9/9: Scoring and enriching %d clusters...", len(clusters))
    for cluster in clusters:
        theme = cluster.theme or "other"

        # Step 5: Compute 8-dimension scores
        cluster.dimensions = compute_cluster_dimensions(
            signals=cluster.signals,
            previous_count=prev_counts.get(theme, 0),
            previous_sentiment=prev_sentiments.get(theme, 0.0),
            known_authors=known_authors,
        )

        # Augment cross_platform_propagation with propagation tracking data
        if cluster.dimensions and propagation_scores:
            cluster_propagation_scores = [
                propagation_scores.get(s.content_hash, 0.0)
                for s in cluster.signals
                if s.content_hash in propagation_scores
            ]
            if cluster_propagation_scores:
                avg_propagation = sum(cluster_propagation_scores) / len(cluster_propagation_scores)
                # Take the max of computed cross-platform and propagation tracking
                cluster.dimensions.cross_platform_propagation = max(
                    cluster.dimensions.cross_platform_propagation,
                    avg_propagation,
                )

        # Step 6: Determine narrative stage
        weeks_active = hist_weeks_active.get(theme, 1)
        if not hist_weeks_active and theme in prev_counts:
            weeks_active = 2
        cluster.narrative_stage = determine_narrative_stage(
            cluster.dimensions,
            weeks_active=weeks_active,
            has_historical_data=has_historical_data,
        )

        # Step 7: Extract top voices and posts
        cluster.top_voices = extract_top_voices(cluster.signals, limit=10)
        cluster.top_posts = extract_top_posts(cluster.signals, limit=10)

        # Step 8: Extract related companies from entity mentions
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

        # Generate cluster description via LLM, fallback to theme summary
        cluster.description = describe_cluster(
            cluster.signals, cluster.name, llm_client,
        )

        # Step 9: Compute centroid embedding for the cluster
        if signal_embeddings:
            centroid = compute_cluster_centroid(cluster.signals, signal_embeddings)
            if centroid:
                # Attach centroid to cluster for db_writer to persist
                cluster._centroid_embedding = centroid  # type: ignore[attr-defined]

    # When no historical data, redistribute stages by percentile so that
    # not all clusters end up as "accelerating" from the fixed thresholds.
    if not has_historical_data:
        assign_narrative_stages_by_percentile(clusters, has_historical_data=False)

    # Detect narrative shifts (compare current vs previous clusters)
    prev_for_shifts = previous_clusters or []
    if not prev_for_shifts and historical_context:
        # historical_context doesn't carry full cluster objects, so shifts
        # are only computed when previous_clusters is provided directly
        pass
    shifts = detect_narrative_shifts(clusters, prev_for_shifts)
    if shifts:
        logger.info("Narrative shifts detected: %d", len(shifts))

    # Detect first movers per cluster
    first_movers = detect_first_movers(themed_signals, clusters)
    if first_movers:
        logger.info("First mover detection: %d clusters with timing data", len(first_movers))

    # Sort clusters by composite score descending
    clusters.sort(key=lambda c: c.composite_score, reverse=True)

    logger.info(
        "Pipeline complete: %d clusters from %d signals. "
        "Top cluster: %s (score=%.3f, stage=%s)",
        len(clusters),
        len(themed_signals),
        clusters[0].name if clusters else "none",
        clusters[0].composite_score if clusters else 0.0,
        clusters[0].narrative_stage if clusters else "n/a",
    )

    # Update module-level state for backward compatibility (db_writer, agent)
    _last_signal_embeddings.clear()
    _last_signal_embeddings.update(signal_embeddings)
    _last_narrative_shifts.clear()
    _last_narrative_shifts.extend(shifts)
    _last_first_movers.clear()
    _last_first_movers.update(first_movers)

    return PipelineResult(
        clusters=clusters,
        all_signals=all_signals,
        signal_embeddings=signal_embeddings,
        narrative_shifts=shifts,
        first_movers=first_movers,
    )
