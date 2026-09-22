"""Small helpers for reading tunables from environment variables."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def int_from_env(name: str, default: int, minimum: int = 1) -> int:
    """Read a positive integer from the environment, falling back to ``default``.

    Unset, blank, non-numeric or below-``minimum`` values all fall back to
    ``default`` (with a warning for the malformed cases) so a typo in ``.env``
    never silently changes agent behaviour.
    """
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning("%s=%r is not an integer; using default %d", name, raw, default)
        return default
    if value < minimum:
        logger.warning("%s=%d is below minimum %d; using default %d", name, value, minimum, default)
        return default
    return value
