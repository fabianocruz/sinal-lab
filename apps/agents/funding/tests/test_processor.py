"""Tests for FUNDING agent processor."""

import pytest

from apps.agents.funding.collector import FundingEvent
from apps.agents.funding.processor import (
    normalize_currency,
    normalize_round_type,
    slugify,
)


def test_normalize_currency_brl_to_usd():
    """Test currency normalization from BRL to USD."""
    event = FundingEvent(
        company_name="Test Co",
        round_type="seed",
        source_url="http://test.com",
        source_name="test",
        amount_local=50.0,  # 50M BRL
        currency="BRL",
    )

    normalized = normalize_currency(event)

    assert normalized.amount_usd is not None
    assert normalized.amount_usd == pytest.approx(10.0, rel=0.1)  # 50 * 0.20 = 10


def test_normalize_currency_already_usd():
    """Test currency normalization when already in USD."""
    event = FundingEvent(
        company_name="Test Co",
        round_type="seed",
        source_url="http://test.com",
        source_name="test",
        amount_usd=10.0,
        currency="USD",
    )

    normalized = normalize_currency(event)

    assert normalized.amount_usd == 10.0


def test_normalize_round_type_series_a():
    """Test round type normalization for Series A variations."""
    assert normalize_round_type("Series A") == "series_a"
    assert normalize_round_type("Série A") == "series_a"
    assert normalize_round_type("serie a") == "series_a"
    assert normalize_round_type("Series A Round") == "series_a"


def test_normalize_round_type_seed():
    """Test round type normalization for seed rounds."""
    assert normalize_round_type("Seed") == "seed"
    assert normalize_round_type("Seed Round") == "seed"
    assert normalize_round_type("Pre-Seed") == "pre_seed"
    assert normalize_round_type("Pre Seed") == "pre_seed"


def test_slugify_company_name():
    """Test company name slugification."""
    assert slugify("Nubank Inc.") == "nubank"
    assert slugify("Stone Co. Ltd.") == "stone-co"
    assert slugify("Creditas S.A.") == "creditas"
    assert slugify("VTEX Platform") == "vtex-platform"
