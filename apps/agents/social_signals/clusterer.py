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

# Clusters larger than this are re-clustered with a tighter threshold.
# Prevents mega-clusters (700+ signals) that mix unrelated content.
MAX_CLUSTER_SIZE = 150

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



# Portuguese fallback labels for common theme/sub_theme combinations.
# Used when the LLM is unavailable to ensure cluster names are always
# displayed in Portuguese on the dashboard.
_PORTUGUESE_LABELS: Dict[str, str] = {
    "AI": "Inteligencia Artificial",
    "AI: AI agents": "Agentes de IA",
    "AI: LLM infrastructure": "Infraestrutura de LLMs",
    "AI: AI safety and governance": "Seguranca e Governanca de IA",
    "AI: Open source AI": "IA Open Source",
    "AI: AI in healthcare": "IA em Saude",
    "AI: AI developer tools": "Ferramentas de IA para Devs",
    "AI: Multimodal AI": "IA Multimodal",
    "AI: Edge AI and on-device": "IA on-device e Edge",
    "Fintech": "Fintech e Pagamentos",
    "Fintech: Payments infrastructure": "Infraestrutura de Pagamentos",
    "Fintech: Embedded finance": "Financas Embutidas",
    "Fintech: Lending and credit": "Credito e Emprestimos",
    "Fintech: Neobanks": "Neobancos",
    "Fintech: Crypto and DeFi": "Cripto e DeFi",
    "Fintech: Insurtech": "Insurtech",
    "Fintech: Wealthtech": "Wealthtech e Investimentos",
    "Fintech: Cross-border payments": "Pagamentos Internacionais",
    "Fintech: Open banking": "Open Banking",
    "Fintech: BaaS": "Banking as a Service",
    "AI in Banking": "IA em Banking e Servicos Financeiros",
    "AI in Banking: AI agents for compliance": "Agentes de IA para Compliance",
    "AI in Banking: KYC automation": "Automacao de KYC",
    "AI in Banking: Underwriting copilots": "Copilots de Underwriting",
    "AI in Banking: Fraud detection AI": "IA para Deteccao de Fraude",
    "AI in Banking: AML monitoring": "Monitoramento AML",
    "AI in Banking: Core banking modernization": "Modernizacao de Core Banking",
    "AI in Banking: Model risk governance": "Governanca de Risco de Modelo",
    "AI in Banking: GenAI compliance": "GenAI e Compliance",
    "AI in Banking: Voice AI in collections": "IA de Voz em Cobranca",
}


def label_cluster(
    signals: List[ProcessedSignal],
    llm_client: Optional[LLMClient] = None,
) -> str:
    """Generate a descriptive name for a cluster of signals.

    Uses LLM when available for high-quality labels (forced Portuguese).
    Falls back to Portuguese label map, then to the most common
    theme + sub_theme combination.

    Args:
        signals: Signals in this cluster.
        llm_client: Optional LLM client for generating labels.

    Returns:
        Human-readable cluster name string in Portuguese.
    """
    if llm_client and llm_client.is_available and len(signals) >= 2:
        # Sample more signals for better coverage, prioritize diverse authors
        seen_authors: set = set()
        sample: List[ProcessedSignal] = []
        for s in signals:
            author = s.post.author_handle or ""
            if author not in seen_authors or len(sample) < 10:
                sample.append(s)
                seen_authors.add(author)
            if len(sample) >= 10:
                break

        sample_texts = [s.post.text[:150] for s in sample]

        # Include theme distribution for context
        theme_dist: Dict[str, int] = defaultdict(int)
        for s in signals:
            if s.theme:
                theme_dist[s.theme] += 1
        theme_summary = ", ".join(f"{t} ({c})" for t, c in sorted(theme_dist.items(), key=lambda x: -x[1])[:3])

        prompt = (
            f"These {len(signals)} social media posts are clustered together. "
            f"Theme distribution: {theme_summary}.\n\n"
            "Sample posts:\n" + "\n---\n".join(sample_texts) + "\n\n"
            "Generate a SPECIFIC label (3-7 words) for the shared topic.\n"
            "BAD labels: 'Publicações diversas', 'Tendências em tecnologia', 'Conteúdos variados'\n"
            "GOOD labels: 'Agentes de IA para Compliance', 'Pagamentos Pix e Open Banking', 'Startups HealthTech LATAM'\n\n"
            "IMPORTANT: Reply in Brazilian Portuguese only.\n"
            "Reply with ONLY the label, no quotes or explanation."
        )

        result = llm_client.generate(
            user_prompt=prompt,
            system_prompt=(
                "You are a topic labeler for a Brazilian tech intelligence platform "
                "covering AI, Fintech, Banking, Startups, and VC in Latin America. "
                "Generate specific, descriptive labels. Never use generic words like "
                "'diversos', 'variados', 'tendências gerais'. "
                "Reply in Brazilian Portuguese only. Reply with a short label only."
            ),
            max_tokens=30,
            temperature=0.2,
        )

        if result and result.strip():
            return result.strip()

    # Fallback: use most common theme/sub_theme with Portuguese labels
    theme_counts: Dict[str, int] = defaultdict(int)
    for s in signals:
        key = s.theme or "General"
        if s.sub_theme:
            key = f"{s.theme}: {s.sub_theme}"
        theme_counts[key] += 1

    if theme_counts:
        best_key = max(theme_counts, key=theme_counts.get)  # type: ignore[arg-type]
        return _PORTUGUESE_LABELS.get(best_key, best_key)

    return "Sinais Diversos"


def describe_cluster(
    signals: List[ProcessedSignal],
    cluster_name: str,
    llm_client: Optional[LLMClient] = None,
) -> str:
    """Generate a 1-2 sentence description for a cluster.

    Uses LLM when available. Falls back to a summary built from the
    most common entities and theme.

    Args:
        signals: Signals in this cluster.
        cluster_name: The cluster's display name (for context).
        llm_client: Optional LLM client for generation.

    Returns:
        Portuguese description string (max ~200 chars).
    """
    if llm_client and llm_client.is_available and len(signals) >= 3:
        # Sample diverse signals for context
        sample_texts = [s.post.text[:120] for s in signals[:8]]

        prompt = (
            f"Cluster: '{cluster_name}' ({len(signals)} posts)\n\n"
            "Sample posts:\n" + "\n---\n".join(sample_texts) + "\n\n"
            "Write a 1-2 sentence summary (max 180 chars) describing "
            "what this cluster is about and why it matters.\n"
            "IMPORTANT: Write in Brazilian Portuguese. Be specific, not generic.\n"
            "Reply with ONLY the description, no quotes."
        )

        result = llm_client.generate(
            user_prompt=prompt,
            system_prompt=(
                "You summarize social signal clusters for a Brazilian tech "
                "intelligence platform. Be concise and specific. "
                "Reply in Brazilian Portuguese only."
            ),
            max_tokens=80,
            temperature=0.3,
        )

        if result and result.strip():
            return result.strip()[:200]

    # Fallback: theme + signal count + top entity
    theme = signals[0].theme if signals else ""
    entity_names: list = []
    for s in signals[:20]:
        for e in s.entities:
            if e.entity_type == "company":
                entity_names.append(e.name)
    top_entity = max(set(entity_names), key=entity_names.count) if entity_names else ""

    if top_entity:
        return f"Discussoes sobre {theme} com destaque para {top_entity} ({len(signals)} sinais)"
    return f"Cluster de {len(signals)} sinais sobre {theme or 'tecnologia'}"


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


def _split_large_clusters(
    grouped: Dict[str, List[ProcessedSignal]],
    max_size: int = MAX_CLUSTER_SIZE,
    tighter_threshold: float = 0.4,
) -> Dict[str, List[ProcessedSignal]]:
    """Re-cluster oversized groups with a tighter distance threshold.

    When a cluster exceeds max_size, it likely mixed unrelated signals.
    We re-run TF-IDF clustering on just that group with a lower threshold
    to split it into more specific sub-clusters.

    Args:
        grouped: Dict of cluster_key -> signals.
        max_size: Maximum acceptable cluster size.
        tighter_threshold: Distance threshold for re-clustering.

    Returns:
        Updated grouped dict with large clusters split.
    """
    if not _SKLEARN_AVAILABLE:
        return grouped

    result: Dict[str, List[ProcessedSignal]] = {}
    split_count = 0

    for key, signals in grouped.items():
        if len(signals) <= max_size:
            result[key] = signals
            continue

        # Re-cluster with tighter threshold
        sub_clusters = _cluster_with_tfidf(signals, tighter_threshold)
        for sub_key, sub_signals in sub_clusters.items():
            result[f"{key}_sub{sub_key}"] = sub_signals
        split_count += 1
        logger.info(
            "Split oversized cluster %s (%d signals) into %d sub-clusters",
            key, len(signals), len(sub_clusters),
        )

    if split_count:
        logger.info("Split %d oversized clusters (max_size=%d)", split_count, max_size)

    return result


def _merge_similar_clusters(
    clusters: List[SignalClusterResult],
) -> List[SignalClusterResult]:
    """Merge clusters with identical or near-identical slugs.

    After labeling, different raw groups may receive the same LLM-generated
    name (e.g., two groups both labeled "Venture Capital e Investimentos").
    These produce duplicate slugs and visually identical cards on the dashboard.

    Merging strategy: clusters with the same slug are combined. The merged
    cluster keeps the name from the largest contributor and combines all
    signals.

    Args:
        clusters: List of labeled SignalClusterResult objects.

    Returns:
        Deduplicated list of SignalClusterResult.
    """
    if len(clusters) <= 1:
        return clusters

    slug_groups: Dict[str, List[SignalClusterResult]] = defaultdict(list)
    for cluster in clusters:
        slug_groups[cluster.slug].append(cluster)

    merged: List[SignalClusterResult] = []
    merge_count = 0

    for slug, group in slug_groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        # Merge: keep name from largest cluster, combine all signals
        group.sort(key=lambda c: c.signal_count, reverse=True)
        primary = group[0]
        all_signals: List[ProcessedSignal] = []
        for c in group:
            all_signals.extend(c.signals)

        merged.append(SignalClusterResult(
            name=primary.name,
            slug=slug,
            theme=primary.theme,
            sub_theme=primary.sub_theme,
            signals=all_signals,
        ))
        merge_count += len(group) - 1

    if merge_count:
        logger.info(
            "Merged %d duplicate clusters (%d -> %d)",
            merge_count,
            len(clusters),
            len(merged),
        )

    return merged


def _build_cluster_results(
    grouped: Dict[str, List[ProcessedSignal]],
    llm_client: Optional[LLMClient] = None,
    min_cluster_size: int = 5,
) -> List[SignalClusterResult]:
    """Build SignalClusterResult objects from grouped signals.

    Shared logic used by both TF-IDF and embedding clustering paths.
    Groups smaller than min_cluster_size are merged into a catch-all
    "Outros Sinais" cluster.

    Args:
        grouped: Dict mapping group_key -> list of ProcessedSignals.
        llm_client: Optional LLM client for cluster labeling.
        min_cluster_size: Minimum signals per cluster.

    Returns:
        List of SignalClusterResult sorted by signal count descending.
    """
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
        results.append(SignalClusterResult(
            name="Outros Sinais",
            slug="outros-sinais",
            theme="",
            sub_theme="",
            signals=small_cluster_signals,
        ))

    # Merge clusters with duplicate slugs (same LLM-generated name)
    results = _merge_similar_clusters(results)

    # Sort by signal count descending
    results.sort(key=lambda c: c.signal_count, reverse=True)

    return results


def cluster_signals(
    signals: List[ProcessedSignal],
    llm_client: Optional[LLMClient] = None,
    distance_threshold: float = 0.7,
    min_cluster_size: int = 5,
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

    # Split oversized clusters into tighter sub-clusters
    grouped = _split_large_clusters(grouped)

    results = _build_cluster_results(grouped, llm_client, min_cluster_size)

    logger.info(
        "Clustered %d signals into %d clusters (min_size=%d)",
        len(signals),
        len(results),
        min_cluster_size,
    )

    return results


# ---------------------------------------------------------------------------
# Embedding-based clustering
# ---------------------------------------------------------------------------


def _compute_cosine_distance_matrix(embeddings: List[List[float]]) -> List[List[float]]:
    """Compute pairwise cosine distance matrix from embedding vectors.

    Args:
        embeddings: List of embedding vectors (each same length).

    Returns:
        NxN distance matrix where distance = 1 - cosine_similarity.
    """
    import math

    n = len(embeddings)
    # Pre-compute norms
    norms = []
    for vec in embeddings:
        norm = math.sqrt(sum(x * x for x in vec))
        norms.append(norm if norm > 0 else 1e-10)

    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dot = sum(a * b for a, b in zip(embeddings[i], embeddings[j]))
            sim = dot / (norms[i] * norms[j])
            dist = max(0.0, 1.0 - sim)
            matrix[i][j] = dist
            matrix[j][i] = dist

    return matrix


def _cluster_with_embeddings(
    signals: List[ProcessedSignal],
    embeddings: Dict[str, List[float]],
    distance_threshold: float = 0.5,
) -> Dict[int, List[ProcessedSignal]]:
    """Cluster signals using precomputed embeddings + agglomerative clustering.

    Uses cosine distance computed from embedding vectors instead of TF-IDF.
    This produces higher-quality clusters because the embeddings capture
    semantic meaning beyond bag-of-words.

    Args:
        signals: Classified signals to cluster.
        embeddings: Dict mapping content_hash -> embedding vector.
        distance_threshold: Maximum distance for merging clusters.
            Lower than TF-IDF default (0.5 vs 0.7) because embedding
            distances are more semantically meaningful.

    Returns:
        Dict mapping cluster_id -> list of ProcessedSignals.
    """
    if not _SKLEARN_AVAILABLE:
        logger.warning("sklearn not available, cannot cluster with embeddings")
        return {}

    # Filter to signals that have embeddings
    indexed_signals = []
    embedding_list = []
    for s in signals:
        emb = embeddings.get(s.content_hash)
        if emb:
            indexed_signals.append(s)
            embedding_list.append(emb)

    if len(indexed_signals) < 2:
        return {}

    # Compute cosine distance matrix from embeddings
    distance_matrix_raw = _compute_cosine_distance_matrix(embedding_list)

    # Convert to numpy for sklearn
    import numpy as np
    distance_matrix = np.array(distance_matrix_raw)
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
        clusters[int(label)].append(indexed_signals[idx])

    return clusters


def compute_cluster_centroid(
    signals: List[ProcessedSignal],
    embeddings: Dict[str, List[float]],
) -> Optional[List[float]]:
    """Compute the centroid embedding for a cluster of signals.

    The centroid is the element-wise mean of all signal embeddings
    in the cluster. Used for cluster-level similarity search.

    Args:
        signals: Signals in the cluster.
        embeddings: Dict mapping content_hash -> embedding vector.

    Returns:
        Centroid vector (same dimensions as input embeddings),
        or None if no signals have embeddings.
    """
    vectors = [
        embeddings[s.content_hash]
        for s in signals
        if s.content_hash in embeddings
    ]

    if not vectors:
        return None

    dim = len(vectors[0])
    centroid = [0.0] * dim

    for vec in vectors:
        for i, val in enumerate(vec):
            centroid[i] += val

    n = len(vectors)
    centroid = [x / n for x in centroid]

    return centroid


def cluster_signals_with_embeddings(
    signals: List[ProcessedSignal],
    embeddings: Dict[str, List[float]],
    llm_client: Optional[LLMClient] = None,
    distance_threshold: float = 0.5,
    min_cluster_size: int = 5,
) -> List[SignalClusterResult]:
    """Cluster signals using embedding vectors for higher-quality grouping.

    Same interface as cluster_signals() but uses precomputed embeddings
    instead of TF-IDF. Falls back to cluster_signals() if embedding
    clustering fails or produces no results.

    Args:
        signals: Classified ProcessedSignals to cluster.
        embeddings: Dict mapping content_hash -> embedding vector.
        llm_client: Optional LLM client for cluster labeling.
        distance_threshold: Distance threshold for agglomerative clustering.
        min_cluster_size: Minimum signals per cluster.

    Returns:
        List of SignalClusterResult sorted by signal count descending.
    """
    if not signals:
        return []

    if not embeddings:
        logger.info("No embeddings available, falling back to TF-IDF clustering")
        return cluster_signals(
            signals, llm_client, distance_threshold=0.7,
            min_cluster_size=min_cluster_size,
        )

    # Check that enough signals have embeddings
    signals_with_embeddings = [s for s in signals if s.content_hash in embeddings]
    coverage = len(signals_with_embeddings) / len(signals)

    if coverage < 0.5:
        logger.warning(
            "Only %.0f%% of signals have embeddings, falling back to TF-IDF",
            coverage * 100,
        )
        return cluster_signals(
            signals, llm_client, distance_threshold=0.7,
            min_cluster_size=min_cluster_size,
        )

    # Try embedding-based clustering
    try:
        raw_clusters = _cluster_with_embeddings(
            signals, embeddings, distance_threshold,
        )
    except Exception:
        logger.exception("Embedding clustering failed, falling back to TF-IDF")
        return cluster_signals(
            signals, llm_client, distance_threshold=0.7,
            min_cluster_size=min_cluster_size,
        )

    if not raw_clusters:
        logger.info("Embedding clustering produced no results, falling back to TF-IDF")
        return cluster_signals(
            signals, llm_client, distance_threshold=0.7,
            min_cluster_size=min_cluster_size,
        )

    # Build SignalClusterResult objects (same logic as cluster_signals)
    grouped: Dict[str, List[ProcessedSignal]] = {
        str(k): v for k, v in raw_clusters.items()
    }

    # Add signals without embeddings to a separate group
    embedded_hashes = set()
    for cluster_signals_list in grouped.values():
        for s in cluster_signals_list:
            embedded_hashes.add(s.content_hash)

    orphan_signals = [s for s in signals if s.content_hash not in embedded_hashes]
    if orphan_signals:
        # Group orphans by theme as fallback
        for s in orphan_signals:
            key = f"orphan_{s.theme or 'other'}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(s)

    # Split oversized clusters into tighter sub-clusters
    grouped = _split_large_clusters(grouped)

    results = _build_cluster_results(grouped, llm_client, min_cluster_size)

    logger.info(
        "Embedding-clustered %d signals into %d clusters (min_size=%d, coverage=%.0f%%)",
        len(signals),
        len(results),
        min_cluster_size,
        coverage * 100,
    )

    return results
