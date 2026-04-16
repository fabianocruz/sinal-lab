"""Signal clustering for the PULSO agent.

Groups related ProcessedSignals into SignalClusterResult objects using
TF-IDF vectorization and agglomerative clustering. Falls back to
simple theme-based grouping when scikit-learn is unavailable.

Key improvements over social_signals/clusterer.py:
    - Tighter distance threshold (0.35 vs 0.7) for fewer repetitive clusters
    - Cross-cluster deduplication removes signals appearing in multiple clusters
    - Merge by centroid cosine similarity (not just slug matching)
    - Smaller MAX_CLUSTER_SIZE (80 vs 150) for tighter clusters
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import defaultdict
from typing import Dict, List, Optional

from apps.agents.base.llm import LLMClient
from apps.agents.pulso.config import (
    CLUSTERING_DISTANCE_THRESHOLD,
    CLUSTER_NAME_BLOCKLIST,
    EMBEDDING_DISTANCE_THRESHOLD,
    MAX_CLUSTER_SIZE,
    MERGE_SIMILARITY_THRESHOLD,
    MIN_CLUSTER_SIZE,
)
from apps.agents.pulso.models import ProcessedSignal, SignalClusterResult

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
    """
    parts = [signal.post.text]
    if signal.theme:
        parts.append(signal.theme)
    if signal.sub_theme:
        parts.append(signal.sub_theme)

    text = " ".join(parts)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[@#](\w+)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Sklearn-based clustering
# ---------------------------------------------------------------------------


def _cluster_with_tfidf(
    signals: List[ProcessedSignal],
    distance_threshold: float = CLUSTERING_DISTANCE_THRESHOLD,
) -> Dict[int, List[ProcessedSignal]]:
    """Cluster signals using TF-IDF + agglomerative clustering.

    Uses cosine distance (1 - cosine_similarity) as the affinity metric
    with average linkage. Lower distance_threshold (0.35) produces
    tighter, more distinct clusters than the old 0.7 default.
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

    sim_matrix = cosine_similarity(tfidf_matrix)
    distance_matrix = 1.0 - sim_matrix
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

    Simple fallback when sklearn is not available.
    """
    groups: Dict[str, List[ProcessedSignal]] = defaultdict(list)

    for signal in signals:
        key = signal.theme or "uncategorized"
        if signal.sub_theme:
            key = f"{key}/{signal.sub_theme}"
        groups[key].append(signal)

    return groups


# ---------------------------------------------------------------------------
# Cross-cluster deduplication (NEW — fixes duplicate signals across clusters)
# ---------------------------------------------------------------------------


def _deduplicate_cross_cluster(
    clusters: Dict[int, List[ProcessedSignal]],
) -> Dict[int, List[ProcessedSignal]]:
    """Remove signals that appear in multiple clusters, keeping in largest cluster.

    Processes clusters by size (largest first = highest priority). Signals
    already seen in a larger cluster are removed from smaller ones. Clusters
    that drop below MIN_CLUSTER_SIZE after dedup are removed.
    """
    seen_hashes: set = set()
    sorted_ids = sorted(clusters.keys(), key=lambda k: len(clusters[k]), reverse=True)

    for cid in sorted_ids:
        deduped = [s for s in clusters[cid] if s.post.content_hash not in seen_hashes]
        seen_hashes.update(s.post.content_hash for s in deduped)
        clusters[cid] = deduped

    return {k: v for k, v in clusters.items() if len(v) >= MIN_CLUSTER_SIZE}


# ---------------------------------------------------------------------------
# Cluster labeling
# ---------------------------------------------------------------------------


# Portuguese fallback labels for common theme/sub_theme combinations.
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
    Falls back to Portuguese label map, then to most common theme.
    """
    if llm_client and llm_client.is_available and len(signals) >= 2:
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

        theme_dist: Dict[str, int] = defaultdict(int)
        for s in signals:
            if s.theme:
                theme_dist[s.theme] += 1
        theme_summary = ", ".join(
            f"{t} ({c})"
            for t, c in sorted(theme_dist.items(), key=lambda x: -x[1])[:3]
        )

        prompt = (
            f"These {len(signals)} social media posts are clustered together. "
            f"Theme distribution: {theme_summary}.\n\n"
            "Sample posts:\n" + "\n---\n".join(sample_texts) + "\n\n"
            "Generate a SPECIFIC label (3-7 words) for the shared topic.\n"
            "BAD labels: 'Publicacoes diversas', 'Tendencias em tecnologia', 'Conteudos variados'\n"
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
                "'diversos', 'variados', 'tendencias gerais'. "
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
    """
    if llm_client and llm_client.is_available and len(signals) >= 3:
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
    """Convert a cluster name to a URL-safe slug."""
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "unnamed-cluster"


# ---------------------------------------------------------------------------
# Cluster merging (improved: cosine similarity of centroids)
# ---------------------------------------------------------------------------


def _compute_centroid(
    signals: List[ProcessedSignal],
    vectorizer: object,
) -> Optional[list]:
    """Compute the TF-IDF centroid vector for a cluster.

    Returns None if the cluster is empty.
    """
    if not signals or not _SKLEARN_AVAILABLE:
        return None

    import numpy as np

    texts = [_prepare_text(s) for s in signals]
    try:
        tfidf_matrix = vectorizer.transform(texts)  # type: ignore[union-attr]
        centroid = tfidf_matrix.mean(axis=0)
        return np.asarray(centroid).flatten().tolist()
    except Exception:
        return None


def _merge_similar_clusters(
    clusters: List[SignalClusterResult],
    similarity_threshold: float = MERGE_SIMILARITY_THRESHOLD,
) -> List[SignalClusterResult]:
    """Merge clusters with similar centroids (cosine similarity >= threshold).

    Improvement over social_signals: merges by centroid similarity, not just
    identical slugs. This catches semantically equivalent clusters with
    slightly different LLM-generated names.
    """
    if len(clusters) <= 1:
        return clusters

    # First pass: merge by identical slugs (fast, no computation)
    slug_groups: Dict[str, List[SignalClusterResult]] = defaultdict(list)
    for cluster in clusters:
        slug_groups[cluster.slug].append(cluster)

    deduped_by_slug: List[SignalClusterResult] = []
    for slug, group in slug_groups.items():
        if len(group) == 1:
            deduped_by_slug.append(group[0])
            continue

        group.sort(key=lambda c: c.signal_count, reverse=True)
        primary = group[0]
        all_signals: List[ProcessedSignal] = []
        for c in group:
            all_signals.extend(c.signals)

        deduped_by_slug.append(SignalClusterResult(
            name=primary.name,
            slug=slug,
            theme=primary.theme,
            sub_theme=primary.sub_theme,
            signals=all_signals,
        ))

    # Second pass: merge by centroid cosine similarity
    if not _SKLEARN_AVAILABLE or len(deduped_by_slug) <= 1:
        return deduped_by_slug

    import numpy as np

    # Build a shared vectorizer from all signal texts
    all_texts = []
    for c in deduped_by_slug:
        all_texts.extend(_prepare_text(s) for s in c.signals)

    if not all_texts:
        return deduped_by_slug

    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        min_df=1,
        max_df=0.95,
        ngram_range=(1, 2),
    )
    try:
        vectorizer.fit(all_texts)
    except ValueError:
        return deduped_by_slug

    # Compute centroids
    centroids = []
    for c in deduped_by_slug:
        centroid = _compute_centroid(c.signals, vectorizer)
        centroids.append(centroid)

    # Find pairs to merge
    merged_into: Dict[int, int] = {}  # index -> merge target index
    for i in range(len(deduped_by_slug)):
        if i in merged_into:
            continue
        if centroids[i] is None:
            continue
        for j in range(i + 1, len(deduped_by_slug)):
            if j in merged_into:
                continue
            if centroids[j] is None:
                continue

            sim = cosine_similarity(
                np.array(centroids[i]).reshape(1, -1),
                np.array(centroids[j]).reshape(1, -1),
            )[0][0]

            if sim >= similarity_threshold:
                merged_into[j] = i

    # Build merged result
    merge_groups: Dict[int, List[int]] = defaultdict(list)
    for j, i in merged_into.items():
        merge_groups[i].append(j)

    result: List[SignalClusterResult] = []
    merged_count = 0

    for idx, cluster in enumerate(deduped_by_slug):
        if idx in merged_into:
            continue  # Will be merged into another

        if idx in merge_groups:
            # Merge children into this cluster
            all_signals = list(cluster.signals)
            for child_idx in merge_groups[idx]:
                all_signals.extend(deduped_by_slug[child_idx].signals)
                merged_count += 1

            result.append(SignalClusterResult(
                name=cluster.name,
                slug=cluster.slug,
                theme=cluster.theme,
                sub_theme=cluster.sub_theme,
                signals=all_signals,
            ))
        else:
            result.append(cluster)

    if merged_count:
        logger.info(
            "Merged %d similar clusters (threshold=%.2f): %d -> %d",
            merged_count, similarity_threshold, len(deduped_by_slug), len(result),
        )

    return result


# ---------------------------------------------------------------------------
# Large cluster splitting
# ---------------------------------------------------------------------------


def _split_large_clusters(
    grouped: Dict[str, List[ProcessedSignal]],
    max_size: int = MAX_CLUSTER_SIZE,
    tighter_threshold: float = 0.25,
) -> Dict[str, List[ProcessedSignal]]:
    """Re-cluster oversized groups with a tighter distance threshold."""
    if not _SKLEARN_AVAILABLE:
        return grouped

    result: Dict[str, List[ProcessedSignal]] = {}
    split_count = 0

    for key, signals in grouped.items():
        if len(signals) <= max_size:
            result[key] = signals
            continue

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


# ---------------------------------------------------------------------------
# Build cluster results
# ---------------------------------------------------------------------------


def _build_cluster_results(
    grouped: Dict[str, List[ProcessedSignal]],
    llm_client: Optional[LLMClient] = None,
    min_cluster_size: int = MIN_CLUSTER_SIZE,
) -> List[SignalClusterResult]:
    """Build SignalClusterResult objects from grouped signals.

    Groups smaller than min_cluster_size are merged into a catch-all
    "Outros Sinais" cluster.
    """
    results: List[SignalClusterResult] = []
    small_cluster_signals: List[ProcessedSignal] = []

    for _key, cluster_signals_list in grouped.items():
        if len(cluster_signals_list) < min_cluster_size:
            small_cluster_signals.extend(cluster_signals_list)
            continue

        name = label_cluster(cluster_signals_list, llm_client)

        # Check blocklist
        name_lower = name.lower()
        if any(p in name_lower for p in CLUSTER_NAME_BLOCKLIST):
            small_cluster_signals.extend(cluster_signals_list)
            continue

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

        cluster = SignalClusterResult(
            name=name,
            slug=slugify_cluster_name(name),
            theme=dominant_theme,
            sub_theme=dominant_sub,
            signals=cluster_signals_list,
        )
        cluster.compute_platform_distribution()
        results.append(cluster)

    # Merge small clusters into catch-all
    if small_cluster_signals:
        catch_all = SignalClusterResult(
            name="Outros Sinais",
            slug="outros-sinais",
            theme="",
            sub_theme="",
            signals=small_cluster_signals,
        )
        catch_all.compute_platform_distribution()
        results.append(catch_all)

    # Merge clusters with similar centroids or identical slugs
    results = _merge_similar_clusters(results)

    # Sort by signal count descending
    results.sort(key=lambda c: c.signal_count, reverse=True)

    return results


# ---------------------------------------------------------------------------
# Main clustering functions
# ---------------------------------------------------------------------------


def cluster_signals(
    signals: List[ProcessedSignal],
    llm_client: Optional[LLMClient] = None,
    distance_threshold: float = CLUSTERING_DISTANCE_THRESHOLD,
    min_cluster_size: int = MIN_CLUSTER_SIZE,
) -> List[SignalClusterResult]:
    """Cluster related signals and build SignalClusterResult objects.

    Uses TF-IDF + agglomerative clustering when sklearn is available,
    otherwise falls back to theme-based grouping. Applies cross-cluster
    deduplication to remove duplicate signals.
    """
    if not signals:
        return []

    if len(signals) == 1:
        name = label_cluster(signals, llm_client)
        cluster = SignalClusterResult(
            name=name,
            slug=slugify_cluster_name(name),
            theme=signals[0].theme,
            sub_theme=signals[0].sub_theme,
            signals=signals,
        )
        cluster.compute_platform_distribution()
        return [cluster]

    # Cluster using sklearn or fallback
    if _SKLEARN_AVAILABLE and len(signals) >= 3:
        raw_clusters = _cluster_with_tfidf(signals, distance_threshold)
        # Cross-cluster deduplication
        raw_clusters = _deduplicate_cross_cluster(raw_clusters)
        grouped: Dict[str, List[ProcessedSignal]] = {
            str(k): v for k, v in raw_clusters.items()
        }
    else:
        grouped = _cluster_by_theme(signals)

    # Split oversized clusters
    grouped = _split_large_clusters(grouped)

    results = _build_cluster_results(grouped, llm_client, min_cluster_size)

    logger.info(
        "Clustered %d signals into %d clusters (threshold=%.2f, min_size=%d)",
        len(signals),
        len(results),
        distance_threshold,
        min_cluster_size,
    )

    return results


def cluster_signals_with_embeddings(
    signals: List[ProcessedSignal],
    embeddings: Dict[str, List[float]],
    llm_client: Optional[LLMClient] = None,
    distance_threshold: float = EMBEDDING_DISTANCE_THRESHOLD,
    min_cluster_size: int = MIN_CLUSTER_SIZE,
) -> List[SignalClusterResult]:
    """Cluster signals using embedding vectors for higher-quality grouping.

    Falls back to cluster_signals() if embedding clustering fails or
    produces no results.
    """
    if not signals:
        return []

    if not embeddings:
        logger.info("No embeddings available, falling back to TF-IDF clustering")
        return cluster_signals(
            signals, llm_client, distance_threshold=CLUSTERING_DISTANCE_THRESHOLD,
            min_cluster_size=min_cluster_size,
        )

    signals_with_embeddings = [s for s in signals if s.content_hash in embeddings]
    coverage = len(signals_with_embeddings) / len(signals)

    if coverage < 0.5:
        logger.warning(
            "Only %.0f%% of signals have embeddings, falling back to TF-IDF",
            coverage * 100,
        )
        return cluster_signals(
            signals, llm_client, distance_threshold=CLUSTERING_DISTANCE_THRESHOLD,
            min_cluster_size=min_cluster_size,
        )

    try:
        raw_clusters = _cluster_with_embeddings(
            signals, embeddings, distance_threshold,
        )
    except Exception:
        logger.exception("Embedding clustering failed, falling back to TF-IDF")
        return cluster_signals(
            signals, llm_client, distance_threshold=CLUSTERING_DISTANCE_THRESHOLD,
            min_cluster_size=min_cluster_size,
        )

    if not raw_clusters:
        logger.info("Embedding clustering produced no results, falling back to TF-IDF")
        return cluster_signals(
            signals, llm_client, distance_threshold=CLUSTERING_DISTANCE_THRESHOLD,
            min_cluster_size=min_cluster_size,
        )

    # Cross-cluster deduplication
    raw_clusters = _deduplicate_cross_cluster(raw_clusters)

    grouped: Dict[str, List[ProcessedSignal]] = {
        str(k): v for k, v in raw_clusters.items()
    }

    # Add signals without embeddings to orphan groups
    embedded_hashes = set()
    for cluster_signals_list in grouped.values():
        for s in cluster_signals_list:
            embedded_hashes.add(s.content_hash)

    orphan_signals = [s for s in signals if s.content_hash not in embedded_hashes]
    if orphan_signals:
        for s in orphan_signals:
            key = f"orphan_{s.theme or 'other'}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(s)

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


# ---------------------------------------------------------------------------
# Embedding-based clustering helpers
# ---------------------------------------------------------------------------


def _compute_cosine_distance_matrix(embeddings: List[List[float]]) -> List[List[float]]:
    """Compute pairwise cosine distance matrix from embedding vectors."""
    import math

    n = len(embeddings)
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
    distance_threshold: float = EMBEDDING_DISTANCE_THRESHOLD,
) -> Dict[int, List[ProcessedSignal]]:
    """Cluster signals using precomputed embeddings + agglomerative clustering."""
    if not _SKLEARN_AVAILABLE:
        logger.warning("sklearn not available, cannot cluster with embeddings")
        return {}

    indexed_signals = []
    embedding_list = []
    for s in signals:
        emb = embeddings.get(s.content_hash)
        if emb:
            indexed_signals.append(s)
            embedding_list.append(emb)

    if len(indexed_signals) < 2:
        return {}

    distance_matrix_raw = _compute_cosine_distance_matrix(embedding_list)

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
    """Compute the centroid embedding for a cluster of signals."""
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
