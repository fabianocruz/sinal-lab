"""Signal clustering for the Social Signals Intelligence agent.

Groups related ProcessedSignals into SignalClusterResult objects using
TF-IDF vectorization and agglomerative clustering. Falls back to
simple theme-based grouping when scikit-learn is unavailable.

Clustering pipeline:
    1. Vectorize signal texts with TF-IDF
    2. Compute cosine similarity matrix
    3. Apply agglomerative clustering with distance threshold
    4. Build SignalClusterResult for each cluster
    5. Optionally label clusters via LLM
"""

import logging
import re
import unicodedata
from collections import defaultdict
from typing import Dict, List, Optional

from apps.agents.base.llm import LLMClient
from apps.agents.social_signals.models import ProcessedSignal, SignalClusterResult

logger = logging.getLogger(__name__)

# Try importing sklearn; flag availability for graceful fallback
try:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logger.info("scikit-learn not available, using theme-based clustering fallback")


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------


def _prepare_text(signal: ProcessedSignal) -> str:
    """Extract and clean text from a ProcessedSignal for vectorization.

    Combines post text with theme and sub-theme labels to improve
    clustering accuracy for short texts.

    Args:
        signal: A classified ProcessedSignal.

    Returns:
        Cleaned text string ready for TF-IDF.
    """
    parts = [signal.post.text]
    if signal.theme:
        parts.append(signal.theme)
    if signal.sub_theme:
        parts.append(signal.sub_theme)

    text = " ".join(parts)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove @mentions and #hashtags (keep the word after)
    text = re.sub(r"[@#](\w+)", r"\1", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Sklearn-based clustering
# ---------------------------------------------------------------------------


def _cluster_with_tfidf(
    signals: List[ProcessedSignal],
    distance_threshold: float = 0.7,
) -> Dict[int, List[ProcessedSignal]]:
    """Cluster signals using TF-IDF + agglomerative clustering.

    Uses cosine distance (1 - cosine_similarity) as the affinity metric
    with average linkage. The distance_threshold controls cluster granularity:
    lower values produce more, tighter clusters.

    Args:
        signals: Classified signals to cluster.
        distance_threshold: Maximum distance for merging clusters (0-2 range
            for cosine distance). Default 0.7 balances granularity.

    Returns:
        Dict mapping cluster_id -> list of ProcessedSignals.
    """
    texts = [_prepare_text(s) for s in signals]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        min_df=1,
        max_df=0.95,
        ngram_range=(1, 2),
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Compute distance matrix (1 - similarity)
    sim_matrix = cosine_similarity(tfidf_matrix)
    distance_matrix = 1.0 - sim_matrix

    # Clamp negative distances (floating point artifacts)
    distance_matrix[distance_matrix < 0] = 0.0

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(distance_matrix)

    clusters: Dict[int, List[ProcessedSignal]] = defaultdict(list)
    for idx, label in enumerate(labels):
        clusters[int(label)].append(signals[idx])

    return clusters


# ---------------------------------------------------------------------------
# Theme-based fallback clustering
# ---------------------------------------------------------------------------


def _cluster_by_theme(
    signals: List[ProcessedSignal],
) -> Dict[str, List[ProcessedSignal]]:
    """Group signals by their classified theme + sub_theme.

    Simple fallback when sklearn is not available. Groups first by theme,
    then splits large theme groups by sub_theme for finer granularity.

    Args:
        signals: Classified signals to group.

    Returns:
        Dict mapping theme_key -> list of ProcessedSignals.
    """
    groups: Dict[str, List[ProcessedSignal]] = defaultdict(list)

    for signal in signals:
        key = signal.theme or "uncategorized"
        if signal.sub_theme:
            key = f"{key}/{signal.sub_theme}"
        groups[key].append(signal)

    return groups


# ---------------------------------------------------------------------------
# Cluster labeling
# ---------------------------------------------------------------------------


def label_cluster(
    signals: List[ProcessedSignal],
    llm_client: Optional[LLMClient] = None,
) -> str:
    """Generate a descriptive name for a cluster of signals.

    Uses LLM when available for high-quality labels. Falls back to
    extracting the most common theme + sub_theme combination.

    Args:
        signals: Signals in this cluster.
        llm_client: Optional LLM client for generating labels.

    Returns:
        Human-readable cluster name string.
    """
    if llm_client and llm_client.is_available and len(signals) >= 2:
        sample_texts = [s.post.text[:150] for s in signals[:5]]
        prompt = (
            "Given these related social media posts, generate a short "
            "(3-7 words) descriptive label for their shared topic.\n\n"
            "Posts:\n" + "\n---\n".join(sample_texts) + "\n\n"
            "Reply with ONLY the label, no quotes or explanation."
        )

        result = llm_client.generate(
            user_prompt=prompt,
            system_prompt="You are a topic labeler. Reply with a short descriptive label only.",
            max_tokens=30,
            temperature=0.3,
        )

        if result and result.strip():
            return result.strip()

    # Fallback: use most common theme/sub_theme
    theme_counts: Dict[str, int] = defaultdict(int)
    for s in signals:
        key = s.theme or "General"
        if s.sub_theme:
            key = f"{s.theme}: {s.sub_theme}"
        theme_counts[key] += 1

    if theme_counts:
        return max(theme_counts, key=theme_counts.get)  # type: ignore[arg-type]

    return "Uncategorized Signals"


def slugify_cluster_name(name: str) -> str:
    """Convert a cluster name to a URL-safe slug.

    Handles Unicode normalization, lowercasing, and replacing
    non-alphanumeric characters with hyphens.

    Args:
        name: Human-readable cluster name.

    Returns:
        URL-safe slug string (e.g., "ai-agents-for-compliance").
    """
    # Normalize unicode characters
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    slug = slug.lower()
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    # Collapse consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    return slug or "unnamed-cluster"


# ---------------------------------------------------------------------------
# Main clustering function
# ---------------------------------------------------------------------------


def cluster_signals(
    signals: List[ProcessedSignal],
    llm_client: Optional[LLMClient] = None,
    distance_threshold: float = 0.7,
    min_cluster_size: int = 2,
) -> List[SignalClusterResult]:
    """Cluster related signals and build SignalClusterResult objects.

    Uses TF-IDF + agglomerative clustering when sklearn is available,
    otherwise falls back to theme-based grouping.

    Clusters with fewer than min_cluster_size signals are merged into
    an "Other Signals" catch-all cluster.

    Args:
        signals: Classified ProcessedSignals to cluster.
        llm_client: Optional LLM client for cluster labeling.
        distance_threshold: Distance threshold for agglomerative clustering.
        min_cluster_size: Minimum signals per cluster. Smaller clusters
            are merged into a catch-all group.

    Returns:
        List of SignalClusterResult sorted by signal count descending.
    """
    if not signals:
        return []

    # Single signal: one cluster
    if len(signals) == 1:
        name = label_cluster(signals, llm_client)
        return [
            SignalClusterResult(
                name=name,
                slug=slugify_cluster_name(name),
                theme=signals[0].theme,
                sub_theme=signals[0].sub_theme,
                signals=signals,
            )
        ]

    # Cluster using sklearn or fallback
    if _SKLEARN_AVAILABLE and len(signals) >= 3:
        raw_clusters = _cluster_with_tfidf(signals, distance_threshold)
        grouped: Dict[str, List[ProcessedSignal]] = {
            str(k): v for k, v in raw_clusters.items()
        }
    else:
        grouped = _cluster_by_theme(signals)

    # Build SignalClusterResult objects
    results: List[SignalClusterResult] = []
    small_cluster_signals: List[ProcessedSignal] = []

    for _key, cluster_signals_list in grouped.items():
        if len(cluster_signals_list) < min_cluster_size:
            small_cluster_signals.extend(cluster_signals_list)
            continue

        name = label_cluster(cluster_signals_list, llm_client)

        # Determine dominant theme/sub_theme
        theme_counts: Dict[str, int] = defaultdict(int)
        sub_counts: Dict[str, int] = defaultdict(int)
        for s in cluster_signals_list:
            if s.theme:
                theme_counts[s.theme] += 1
            if s.sub_theme:
                sub_counts[s.sub_theme] += 1

        dominant_theme = max(theme_counts, key=theme_counts.get) if theme_counts else ""  # type: ignore[arg-type]
        dominant_sub = max(sub_counts, key=sub_counts.get) if sub_counts else ""  # type: ignore[arg-type]

        results.append(SignalClusterResult(
            name=name,
            slug=slugify_cluster_name(name),
            theme=dominant_theme,
            sub_theme=dominant_sub,
            signals=cluster_signals_list,
        ))

    # Merge small clusters into catch-all
    if small_cluster_signals:
        name = "Other Signals"
        results.append(SignalClusterResult(
            name=name,
            slug="other-signals",
            theme="",
            sub_theme="",
            signals=small_cluster_signals,
        ))

    # Sort by signal count descending
    results.sort(key=lambda c: c.signal_count, reverse=True)

    logger.info(
        "Clustered %d signals into %d clusters (min_size=%d)",
        len(signals),
        len(results),
        min_cluster_size,
    )

    return results
