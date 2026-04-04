"""Embedding generation for Social Signals.

Generates text embeddings using OpenAI's text-embedding-3-small model
(1536 dimensions). Falls back to TF-IDF vectors when the OpenAI API
is unavailable or the key is not configured.

Embeddings are generated for signal text (post + theme + sub_theme)
and stored as JSON arrays in the database. When pgvector is available,
they are also stored in a native vector column for fast similarity search.

Design decisions:
    - LRU cache on content_hash avoids re-embedding duplicates within a run
    - Batch API calls (up to 2048 texts per request) minimize latency
    - TF-IDF fallback produces 1536-dim vectors via truncation/padding
    - All errors are caught and logged; embedding failures never block the pipeline
"""

import logging
import os
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from apps.agents.social_signals.models import ProcessedSignal

logger = logging.getLogger(__name__)

# OpenAI embedding config
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 2048  # OpenAI max texts per request

# Try importing optional dependencies
_OPENAI_AVAILABLE = False
_SKLEARN_AVAILABLE = False

try:
    import openai

    _OPENAI_AVAILABLE = True
except ImportError:
    pass

try:
    from sklearn.feature_extraction.text import TfidfVectorizer

    _SKLEARN_AVAILABLE = True
except ImportError:
    pass


def _has_openai_key() -> bool:
    """Check if OPENAI_API_KEY is set in environment."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _prepare_embedding_text(signal: ProcessedSignal) -> str:
    """Build text input for embedding from a ProcessedSignal.

    Combines post text with theme/sub_theme labels and cleans noise
    (URLs, mentions, hashtags) to produce a clean embedding input.

    Args:
        signal: A classified ProcessedSignal.

    Returns:
        Cleaned text string ready for embedding.
    """
    parts = [signal.post.text]
    if signal.theme:
        parts.append(f"Theme: {signal.theme}")
    if signal.sub_theme:
        parts.append(f"Sub-theme: {signal.sub_theme}")

    text = " ".join(parts)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove @mentions and #hashtags (keep the word after)
    text = re.sub(r"[@#](\w+)", r"\1", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate to ~8000 chars (approx 2000 tokens, well within 8191 limit)
    return text[:8000]


# ---------------------------------------------------------------------------
# LRU cache for individual embeddings (keyed by content_hash)
# ---------------------------------------------------------------------------

# Module-level cache: content_hash -> embedding vector
_embedding_cache: Dict[str, List[float]] = {}
_CACHE_MAX_SIZE = 10000


def _cache_get(content_hash: str) -> Optional[List[float]]:
    """Retrieve a cached embedding by content_hash."""
    return _embedding_cache.get(content_hash)


def _cache_put(content_hash: str, embedding: List[float]) -> None:
    """Store an embedding in the cache, evicting oldest if full."""
    if len(_embedding_cache) >= _CACHE_MAX_SIZE:
        # Evict first 10% of entries (simple FIFO eviction)
        evict_count = _CACHE_MAX_SIZE // 10
        keys_to_evict = list(_embedding_cache.keys())[:evict_count]
        for k in keys_to_evict:
            del _embedding_cache[k]
    _embedding_cache[content_hash] = embedding


def clear_embedding_cache() -> None:
    """Clear the module-level embedding cache. Useful in tests."""
    _embedding_cache.clear()


# ---------------------------------------------------------------------------
# OpenAI embedding client
# ---------------------------------------------------------------------------


def _call_openai_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """Call OpenAI embeddings API for a batch of texts.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each 1536 floats), or None on failure.
    """
    if not _OPENAI_AVAILABLE or not _has_openai_key():
        return None

    try:
        client = openai.OpenAI()
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    except openai.AuthenticationError:
        logger.warning("OpenAI API key invalid, falling back to TF-IDF")
        return None
    except openai.RateLimitError:
        logger.warning("OpenAI rate limit hit, falling back to TF-IDF")
        return None
    except Exception:
        logger.exception("OpenAI embedding call failed, falling back to TF-IDF")
        return None


# ---------------------------------------------------------------------------
# TF-IDF fallback
# ---------------------------------------------------------------------------


def _generate_tfidf_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate TF-IDF based embeddings as a fallback.

    Produces vectors padded/truncated to EMBEDDING_DIMENSIONS (1536)
    so they are compatible with the same storage and similarity code.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each 1536 floats).
    """
    if not _SKLEARN_AVAILABLE:
        logger.warning("sklearn not available, returning zero vectors")
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

    vectorizer = TfidfVectorizer(
        max_features=EMBEDDING_DIMENSIONS,
        stop_words="english",
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Empty vocabulary (e.g., all stop words)
        logger.warning("TF-IDF produced empty vocabulary, returning zero vectors")
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

    embeddings: List[List[float]] = []
    for i in range(tfidf_matrix.shape[0]):
        row = tfidf_matrix[i].toarray().flatten().tolist()
        # Pad to EMBEDDING_DIMENSIONS if fewer features
        if len(row) < EMBEDDING_DIMENSIONS:
            row.extend([0.0] * (EMBEDDING_DIMENSIONS - len(row)))
        # Truncate if more (shouldn't happen with max_features set)
        row = row[:EMBEDDING_DIMENSIONS]
        embeddings.append(row)

    return embeddings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_embeddings(
    signals: List[ProcessedSignal],
    force_tfidf: bool = False,
) -> Dict[str, List[float]]:
    """Generate embeddings for a list of ProcessedSignals.

    Tries OpenAI text-embedding-3-small first, falls back to TF-IDF.
    Results are cached by content_hash to avoid redundant API calls.

    Args:
        signals: ProcessedSignals to embed.
        force_tfidf: If True, skip OpenAI and use TF-IDF directly.
            Useful for testing or when API costs are a concern.

    Returns:
        Dict mapping content_hash -> embedding vector (1536 floats).
    """
    if not signals:
        return {}

    result: Dict[str, List[float]] = {}

    # Check cache first
    uncached_signals: List[ProcessedSignal] = []
    uncached_texts: List[str] = []

    for signal in signals:
        cached = _cache_get(signal.content_hash)
        if cached is not None:
            result[signal.content_hash] = cached
        else:
            uncached_signals.append(signal)
            uncached_texts.append(_prepare_embedding_text(signal))

    if not uncached_signals:
        logger.info("All %d embeddings served from cache", len(signals))
        return result

    logger.info(
        "Generating embeddings: %d cached, %d to generate",
        len(result),
        len(uncached_signals),
    )

    # Try OpenAI first (in batches)
    embeddings: Optional[List[List[float]]] = None
    method = "none"

    if not force_tfidf and _OPENAI_AVAILABLE and _has_openai_key():
        all_embeddings: List[List[float]] = []
        success = True

        for i in range(0, len(uncached_texts), BATCH_SIZE):
            batch = uncached_texts[i : i + BATCH_SIZE]
            batch_result = _call_openai_embeddings(batch)

            if batch_result is None:
                success = False
                break

            all_embeddings.extend(batch_result)

        if success and len(all_embeddings) == len(uncached_texts):
            embeddings = all_embeddings
            method = "openai"

    # Fall back to TF-IDF
    if embeddings is None:
        embeddings = _generate_tfidf_embeddings(uncached_texts)
        method = "tfidf"

    # Store results and update cache
    for signal, embedding in zip(uncached_signals, embeddings):
        result[signal.content_hash] = embedding
        _cache_put(signal.content_hash, embedding)

    logger.info(
        "Generated %d embeddings via %s (total: %d)",
        len(uncached_signals),
        method,
        len(result),
    )

    return result


def get_embedding_method() -> str:
    """Return which embedding method is currently available.

    Returns:
        "openai" if API key is set and library available,
        "tfidf" if sklearn is available,
        "none" if neither is available.
    """
    if _OPENAI_AVAILABLE and _has_openai_key():
        return "openai"
    if _SKLEARN_AVAILABLE:
        return "tfidf"
    return "none"
