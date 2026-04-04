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
from apps.agents.social_signals.clusterer import cluster_signals
from apps.agents.social_signals.models import (
    ProcessedSignal,
    SignalClusterResult,
    SocialPost,
)
from apps.agents.social_signals.propagation import enrich_signals_with_propagation
from apps.agents.social_signals.scorer import (
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
    distance_threshold: float = 0.7,
    min_cluster_size: int = 2,
    top_n_for_llm: int = 20,
) -> Tuple[List[SignalClusterResult], List[ProcessedSignal]]:
    """Execute the full social signals processing pipeline.

    Steps:
        1. Batch-classify all posts (keyword-first, LLM for top N only)
        2. Filter out posts with no theme assigned
        3. Compute cross-platform propagation scores
        4. Cluster related signals using TF-IDF or theme-based fallback
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

    Returns:
        Tuple of:
            - List of scored SignalClusterResult objects (sorted by composite score)
            - List of all ProcessedSignal objects (including filtered-out ones)
    """
    if not posts:
        logger.warning("Pipeline received 0 posts, returning empty results")
        return [], []

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
        return [], all_signals

    # Step 3: Compute cross-platform propagation scores
    logger.info("Step 3/8: Computing cross-platform propagation scores...")
    propagation_scores = enrich_signals_with_propagation(themed_signals)

    # Step 4: Cluster related signals
    logger.info("Step 4/8: Clustering %d signals...", len(themed_signals))
    clusters = cluster_signals(
        themed_signals,
        llm_client=llm_client,
        distance_threshold=distance_threshold,
        min_cluster_size=min_cluster_size,
    )

    # Build previous-period lookups from historical_context or previous_clusters
    if historical_context:
        prev_counts = historical_context.get("theme_counts", {})
        prev_sentiments = historical_context.get("theme_sentiments", {})
        known_authors = historical_context.get("known_authors", set())
        hist_weeks_active = historical_context.get("weeks_active", {})
    else:
        prev_counts, prev_sentiments, known_authors = _build_previous_period_data(
            previous_clusters,
        )
        hist_weeks_active = {}

    # Steps 5-8: Score, stage, and enrich each cluster
    logger.info("Step 5-8/8: Scoring and enriching %d clusters...", len(clusters))
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
            cluster.dimensions, weeks_active=weeks_active,
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

        # Set description from top post text
        if cluster.top_posts:
            cluster.description = cluster.top_posts[0].get("text", "")[:200]

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

    return clusters, all_signals
