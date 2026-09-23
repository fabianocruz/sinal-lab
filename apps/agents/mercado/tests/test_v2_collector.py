"""Tests for MERCADO v2 collector (reader of funding_rounds)."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.mercado.v2_collector import (
    NOISE_CONFIDENCE_THRESHOLD,
    collect_funding_events,
    is_noise_round,
)
from packages.database.models.base import Base
from packages.database.models.funding_round import FundingRound


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _round(slug: str, amount_usd, confidence: float, days_ago: int = 1) -> FundingRound:
    return FundingRound(
        id=uuid.uuid4(),
        company_slug=slug,
        company_name=slug.title(),
        round_type="seed",
        amount_usd=amount_usd,
        currency="USD",
        announced_date=date.today() - timedelta(days=days_ago),
        source_url=f"https://example.com/{slug}",
        source_name="test",
        confidence=confidence,
    )


def test_is_noise_round():
    assert is_noise_round(_round("a", None, 0.3)) is True
    assert is_noise_round(_round("b", None, NOISE_CONFIDENCE_THRESHOLD)) is False  # curated undisclosed
    assert is_noise_round(_round("c", 1_000_000, 0.3)) is False  # has amount
    assert is_noise_round(_round("d", 1_000_000, 0.8)) is False


def test_collect_skips_amountless_low_confidence_rows(session):
    session.add_all([
        _round("kapital", 125_000_000, 0.8),
        _round("omme", None, 0.8),          # Crunchbase undisclosed: kept
        _round("rss-noise", None, 0.3),     # RSS headline row: dropped
        _round("bull", 3.7, 0.384),         # legacy millions, has amount: kept
    ])
    session.commit()

    events = collect_funding_events(session, days_back=7)
    slugs = sorted(e.company_slug for e in events)
    assert slugs == ["bull", "kapital", "omme"]


def test_collect_respects_days_back(session):
    session.add_all([
        _round("recent", 1_000_000, 0.8, days_ago=3),
        _round("old", 1_000_000, 0.8, days_ago=20),
    ])
    session.commit()

    assert [e.company_slug for e in collect_funding_events(session, days_back=7)] == ["recent"]
    assert len(collect_funding_events(session, days_back=30)) == 2
