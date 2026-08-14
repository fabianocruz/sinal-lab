"""Tests for shared funding field normalizers.

Used by both the FUNDING collector (LLM fallback extraction) and the
Grok Live Search source, so they live in the shared source layer.
"""

import pytest

from apps.agents.sources.funding_normalize import (
    VALID_ROUND_TYPES,
    coerce_amount,
    normalize_round_type_token,
)


class TestCoerceAmount:
    """Amounts arrive as numbers or as loosely formatted strings."""

    @pytest.mark.parametrize("raw,expected", [
        (6_500_000, 6_500_000.0),
        (6_500_000.0, 6_500_000.0),
        ("6500000", 6_500_000.0),
        ("US$ 6.500.000", 6_500_000.0),
        ("6,5", 6.5),
    ])
    def test_valid_amounts(self, raw, expected) -> None:
        assert coerce_amount(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "não divulgado", 0, -5, True, False, [], {}])
    def test_invalid_amounts(self, raw) -> None:
        assert coerce_amount(raw) is None


class TestNormalizeRoundTypeToken:
    """LLMs return round types in many shapes; we store one vocabulary."""

    @pytest.mark.parametrize("raw,expected", [
        ("seed", "seed"),
        ("Seed", "seed"),
        ("seed round", "seed"),
        ("Seed Round", "seed"),
        ("pre-seed", "pre_seed"),
        ("Pre Seed", "pre_seed"),
        ("preseed", "pre_seed"),
        ("Series A", "series_a"),
        ("series-b", "series_b"),
        ("Série C", "series_c"),
        ("serie d", "series_d"),
        ("rodada Series E", "series_e"),
        ("venture", "venture"),
        ("ipo", "ipo"),
    ])
    def test_known_round_types(self, raw, expected) -> None:
        assert normalize_round_type_token(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "   ", 42, ["seed"], "growth equity", "series_z"])
    def test_unknown_round_types(self, raw) -> None:
        assert normalize_round_type_token(raw) == "unknown"

    def test_output_is_always_in_the_vocabulary(self) -> None:
        for raw in ("seed", "Series G", "nonsense", None):
            assert normalize_round_type_token(raw) in VALID_ROUND_TYPES
