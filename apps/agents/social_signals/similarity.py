"""Similarity search for Social Signals using pgvector or JSON fallback.

Provides find_similar_signals() which uses the pgvector <=> (cosine distance)
operator when available, falling back to in-memory cosine similarity on
the embedding_json column when pgvector is not installed.

No pgvector Python package is used. All vector operations go through raw SQL.
"""

import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Module-level cache for pgvector availability check
_pgvector_available: Optional[bool] = None


def check_pgvector_available(session: Session) -> bool:
    """Check if pgvector extension is installed in the database.

    Caches the result for the lifetime of the process to avoid
    repeated queries.

    Args:
        session: SQLAlchemy session.

    Returns:
        True if pgvector is available and the vector column exists.
    """
    global _pgvector_available

    if _pgvector_available is not None:
        return _pgvector_available

    try:
        result = session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        has_extension = result.fetchone() is not None

        if has_extension:
            # Also verify the column exists on social_signals
            col_check = session.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'social_signals' "
                    "AND column_name = 'embedding_vector'"
                )
            )
            has_column = col_check.fetchone() is not None
            _pgvector_available = has_extension and has_column
        else:
            _pgvector_available = False

    except Exception:
        logger.warning("Could not check pgvector availability, assuming unavailable")
        _pgvector_available = False

    logger.info("pgvector available: %s", _pgvector_available)
    return _pgvector_available


def reset_pgvector_cache() -> None:
    """Reset the pgvector availability cache. Useful in tests."""
    global _pgvector_available
    _pgvector_available = None


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity (-1 to 1), or 0.0 if either vector is zero.
    """
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


def find_similar_signals(
    session: Session,
    embedding: List[float],
    limit: int = 10,
    min_similarity: float = 0.7,
    exclude_content_hash: Optional[str] = None,
    theme_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find signals most similar to a given embedding vector.

    Uses pgvector's <=> (cosine distance) operator when available.
    Falls back to loading embedding_json and computing cosine similarity
    in Python.

    Args:
        session: SQLAlchemy session.
        embedding: Query embedding vector (1536 floats).
        limit: Maximum number of results.
        min_similarity: Minimum cosine similarity threshold (0-1).
        exclude_content_hash: Content hash to exclude (e.g., the query signal itself).
        theme_filter: If set, only return signals with this theme.

    Returns:
        List of dicts with keys: id, content_hash, text, theme, platform,
        similarity_score, published_at. Sorted by similarity descending.
    """
    if not embedding:
        return []

    use_pgvector = check_pgvector_available(session)

    if use_pgvector:
        return _find_similar_pgvector(
            session, embedding, limit, min_similarity,
            exclude_content_hash, theme_filter,
        )
    else:
        return _find_similar_json_fallback(
            session, embedding, limit, min_similarity,
            exclude_content_hash, theme_filter,
        )


def _find_similar_pgvector(
    session: Session,
    embedding: List[float],
    limit: int,
    min_similarity: float,
    exclude_content_hash: Optional[str],
    theme_filter: Optional[str],
) -> List[Dict[str, Any]]:
    """Find similar signals using pgvector <=> operator.

    The <=> operator computes cosine distance (1 - cosine_similarity),
    so we filter where distance < (1 - min_similarity).

    Args:
        session: SQLAlchemy session.
        embedding: Query vector.
        limit: Max results.
        min_similarity: Min cosine similarity.
        exclude_content_hash: Content hash to exclude.
        theme_filter: Optional theme filter.

    Returns:
        List of similar signal dicts.
    """
    max_distance = 1.0 - min_similarity
    embedding_str = "[" + ",".join(str(f) for f in embedding) + "]"

    # Build WHERE clause dynamically
    where_parts = [
        "embedding_vector IS NOT NULL",
        f"(embedding_vector <=> :query_vec) < :max_dist",
    ]
    params: Dict[str, Any] = {
        "query_vec": embedding_str,
        "max_dist": max_distance,
        "lim": limit,
    }

    if exclude_content_hash:
        where_parts.append("content_hash != :exclude_hash")
        params["exclude_hash"] = exclude_content_hash

    if theme_filter:
        where_parts.append("theme = :theme")
        params["theme"] = theme_filter

    where_clause = " AND ".join(where_parts)

    query = text(f"""
        SELECT
            id,
            content_hash,
            text,
            theme,
            sub_theme,
            platform,
            published_at,
            1.0 - (embedding_vector <=> :query_vec) AS similarity_score
        FROM social_signals
        WHERE {where_clause}
        ORDER BY embedding_vector <=> :query_vec
        LIMIT :lim
    """)

    try:
        rows = session.execute(query, params).fetchall()

        return [
            {
                "id": str(row.id),
                "content_hash": row.content_hash,
                "text": row.text,
                "theme": row.theme,
                "sub_theme": row.sub_theme,
                "platform": row.platform,
                "published_at": str(row.published_at) if row.published_at else None,
                "similarity_score": round(float(row.similarity_score), 4),
            }
            for row in rows
        ]

    except Exception:
        logger.exception("pgvector similarity search failed, falling back to JSON")
        return _find_similar_json_fallback(
            session, embedding, limit, min_similarity,
            exclude_content_hash, theme_filter,
        )


def _find_similar_json_fallback(
    session: Session,
    embedding: List[float],
    limit: int,
    min_similarity: float,
    exclude_content_hash: Optional[str],
    theme_filter: Optional[str],
) -> List[Dict[str, Any]]:
    """Find similar signals using in-memory cosine similarity on embedding_json.

    Loads all signals with non-null embedding_json and computes similarity
    in Python. Less efficient than pgvector but works everywhere.

    Args:
        session: SQLAlchemy session.
        embedding: Query vector.
        limit: Max results.
        min_similarity: Min cosine similarity.
        exclude_content_hash: Content hash to exclude.
        theme_filter: Optional theme filter.

    Returns:
        List of similar signal dicts.
    """
    where_parts = ["embedding_json IS NOT NULL"]
    params: Dict[str, Any] = {}

    if exclude_content_hash:
        where_parts.append("content_hash != :exclude_hash")
        params["exclude_hash"] = exclude_content_hash

    if theme_filter:
        where_parts.append("theme = :theme")
        params["theme"] = theme_filter

    where_clause = " AND ".join(where_parts)

    query = text(f"""
        SELECT id, content_hash, text, theme, sub_theme, platform,
               published_at, embedding_json
        FROM social_signals
        WHERE {where_clause}
    """)

    try:
        rows = session.execute(query, params).fetchall()
    except Exception:
        logger.exception("JSON fallback similarity search failed")
        return []

    results: List[Tuple[float, Dict[str, Any]]] = []

    for row in rows:
        try:
            stored_embedding = row.embedding_json
            if isinstance(stored_embedding, str):
                stored_embedding = json.loads(stored_embedding)

            if not isinstance(stored_embedding, list) or not stored_embedding:
                continue

            sim = _cosine_similarity(embedding, stored_embedding)

            if sim >= min_similarity:
                results.append((
                    sim,
                    {
                        "id": str(row.id),
                        "content_hash": row.content_hash,
                        "text": row.text,
                        "theme": row.theme,
                        "sub_theme": row.sub_theme,
                        "platform": row.platform,
                        "published_at": str(row.published_at) if row.published_at else None,
                        "similarity_score": round(sim, 4),
                    },
                ))
        except (json.JSONDecodeError, TypeError):
            continue

    # Sort by similarity descending
    results.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in results[:limit]]
