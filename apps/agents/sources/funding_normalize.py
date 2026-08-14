"""Shared normalizers for loosely structured funding data.

LLM-based extraction (FUNDING's RSS fallback, Grok Live Search) returns
amounts and round types in whatever shape the model felt like emitting.
These helpers coerce both into the vocabulary the rest of the pipeline
stores, so every extraction path agrees on ``series_a`` vs ``Series A``
and on what counts as a usable amount.

Usage:
    from apps.agents.sources.funding_normalize import (
        coerce_amount, normalize_round_type_token,
    )

    amount = coerce_amount("US$ 6.500.000")   # 6500000.0
    round_type = normalize_round_type_token("Série C")  # "series_c"
"""

import re
from typing import Any, Optional

#: Canonical round types stored across the platform. Anything outside
#: this set becomes "unknown" rather than polluting the taxonomy.
VALID_ROUND_TYPES = frozenset(
    {
        "pre_seed",
        "seed",
        "series_a",
        "series_b",
        "series_c",
        "series_d",
        "series_e",
        "series_f",
        "series_g",
        "venture",
        "angel",
        "bridge",
        "extension",
        "debt",
        "grant",
        "ipo",
        "unknown",
    }
)


def coerce_amount(raw: Any) -> Optional[float]:
    """Coerce a model-provided amount into a positive float.

    Accepts numbers and loosely formatted strings ("US$ 6.500.000",
    "6,5"). Booleans are rejected explicitly (``bool`` is an ``int``).

    Args:
        raw: Value emitted by the model.

    Returns:
        Positive float, or None when the value is missing or unusable.
    """
    if raw is None or isinstance(raw, bool):
        return None

    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if value > 0 else None

    if isinstance(raw, str):
        digits = re.sub(r"[^\d.]", "", raw.replace(",", "."))
        # Keep only one decimal separator: "6.500.000" -> "6500000"
        parts = digits.split(".")
        if len(parts) > 2:
            digits = parts[0] + "".join(parts[1:])
        try:
            value = float(digits)
        except ValueError:
            return None
        return value if value > 0 else None

    return None


def normalize_round_type_token(raw: Any) -> str:
    """Map a free-form round type onto :data:`VALID_ROUND_TYPES`.

    Examples:
        >>> normalize_round_type_token("Series A")
        'series_a'
        >>> normalize_round_type_token("Série C")
        'series_c'
        >>> normalize_round_type_token("growth equity")
        'unknown'

    Args:
        raw: Value emitted by the model (str or anything else).

    Returns:
        A canonical round type, or "unknown".
    """
    if not isinstance(raw, str) or not raw.strip():
        return "unknown"

    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = normalized.replace("é", "e")
    # Drop noise words wherever they appear ("rodada series e" -> "series_e")
    normalized = re.sub(r"(^|_)(round|rodada|ronda)(_|$)", r"\1", normalized).strip("_")

    match = re.search(r"(?:^|_)(?:series|serie)_([a-g])$", normalized)
    if match:
        return f"series_{match.group(1)}"

    if normalized == "preseed":
        return "pre_seed"

    return normalized if normalized in VALID_ROUND_TYPES else "unknown"
