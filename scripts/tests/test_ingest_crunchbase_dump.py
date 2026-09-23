"""Tests for the Crunchbase manual dump ingestion (dedup with date tolerance).

Crunchbase profile cards shift announced dates between dumps, so the
same deal can reappear ~1 month later. Dedup must match on
(slug, round_type) + compatible amount + date within tolerance, keeping
the oldest date as canonical. See the UnblockPay triple-insert incident
(ed 56) that motivated this.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base
from packages.database.models.funding_round import FundingRound
from scripts.ingest_crunchbase_dump import (
    DATE_TOLERANCE_DAYS,
    ParsedRound,
    dedup_rounds,
    upsert_round,
)


def _round(
    slug: str = "unblockpay",
    round_type: str = "seed",
    amount: float | None = 4_500_000.0,
    announced: date = date(2026, 3, 25),
) -> ParsedRound:
    return ParsedRound(
        company_name=slug.title(),
        company_slug=slug,
        city="São Paulo",
        country="Brasil",
        round_type_raw=round_type.title(),
        round_type=round_type,
        amount_usd=amount,
        announced_date=announced,
    )


# ---------------------------------------------------------------------------
# dedup_rounds (intra-dump)
# ---------------------------------------------------------------------------


class TestDedupRounds:
    def test_exact_duplicate_removed(self):
        rounds = [_round(), _round()]
        assert len(dedup_rounds(rounds)) == 1

    def test_shifted_date_within_tolerance_is_same_deal(self):
        rounds = [
            _round(announced=date(2026, 3, 25)),
            _round(announced=date(2026, 4, 20)),  # 26 days later
        ]
        unique = dedup_rounds(rounds)
        assert len(unique) == 1
        # Older date is canonical
        assert unique[0].announced_date == date(2026, 3, 25)

    def test_newer_entry_first_still_keeps_oldest_date(self):
        rounds = [
            _round(announced=date(2026, 4, 20)),
            _round(announced=date(2026, 3, 25)),
        ]
        unique = dedup_rounds(rounds)
        assert len(unique) == 1
        assert unique[0].announced_date == date(2026, 3, 25)

    def test_shifted_date_beyond_tolerance_kept_as_two_deals(self):
        rounds = [
            _round(announced=date(2026, 1, 10)),
            _round(announced=date(2026, 3, 25)),
        ]
        assert len(dedup_rounds(rounds)) == 2

    def test_different_amounts_within_window_are_different_deals(self):
        rounds = [
            _round(amount=4_500_000.0),
            _round(amount=10_000_000.0, announced=date(2026, 4, 1)),
        ]
        assert len(dedup_rounds(rounds)) == 2

    def test_undisclosed_amount_merges_and_fills(self):
        rounds = [
            _round(amount=None, announced=date(2026, 3, 25)),
            _round(amount=4_500_000.0, announced=date(2026, 4, 1)),
        ]
        unique = dedup_rounds(rounds)
        assert len(unique) == 1
        assert unique[0].amount_usd == 4_500_000.0

    def test_different_round_types_are_kept(self):
        rounds = [_round(round_type="seed"), _round(round_type="series_a")]
        assert len(dedup_rounds(rounds)) == 2

    def test_different_companies_are_kept(self):
        rounds = [_round(slug="unblockpay"), _round(slug="otherco")]
        assert len(dedup_rounds(rounds)) == 2


# ---------------------------------------------------------------------------
# upsert_round (against the DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


def _db_round(
    slug: str = "unblockpay",
    round_type: str = "seed",
    amount: float | None = 4_500_000.0,
    announced: date = date(2026, 3, 25),
) -> FundingRound:
    return FundingRound(
        id=uuid.uuid4(),
        company_name=slug.title(),
        company_slug=slug,
        round_type=round_type,
        amount_usd=amount,
        announced_date=announced,
        source_name="latamlist",
    )


class TestUpsertRound:
    def test_inserts_new_round(self, session):
        assert upsert_round(session, _round()) == "inserted"
        session.flush()
        assert session.query(FundingRound).count() == 1

    def test_skips_exact_existing(self, session):
        session.add(_db_round())
        session.flush()

        assert upsert_round(session, _round()) == "skipped"
        assert session.query(FundingRound).count() == 1

    def test_shifted_reimport_does_not_duplicate(self, session):
        """The UnblockPay case: re-import with date shifted ~1 month."""
        session.add(_db_round(announced=date(2026, 3, 25)))
        session.flush()

        result = upsert_round(session, _round(announced=date(2026, 4, 20)))

        assert result == "skipped"
        assert session.query(FundingRound).count() == 1

    def test_older_incoming_date_becomes_canonical(self, session):
        session.add(_db_round(announced=date(2026, 4, 20)))
        session.flush()

        result = upsert_round(session, _round(announced=date(2026, 3, 25)))

        assert result == "updated"
        row = session.query(FundingRound).one()
        assert row.announced_date == date(2026, 3, 25)

    def test_fills_missing_amount(self, session):
        session.add(_db_round(amount=None))
        session.flush()

        result = upsert_round(session, _round(amount=4_500_000.0))

        assert result == "updated"
        assert session.query(FundingRound).one().amount_usd == 4_500_000.0

    def test_beyond_tolerance_inserts_new_row(self, session):
        session.add(_db_round(announced=date(2026, 1, 10)))
        session.flush()

        result = upsert_round(session, _round(announced=date(2026, 3, 25)))

        assert result == "inserted"
        session.flush()
        assert session.query(FundingRound).count() == 2

    def test_different_amount_within_window_inserts_new_row(self, session):
        session.add(_db_round(amount=4_500_000.0))
        session.flush()

        result = upsert_round(
            session, _round(amount=10_000_000.0, announced=date(2026, 4, 1))
        )

        assert result == "inserted"
        session.flush()
        assert session.query(FundingRound).count() == 2

    def test_tolerance_constant_is_30_days(self):
        assert DATE_TOLERANCE_DAYS == 30


# ---------------------------------------------------------------------------
# CSV export format
# ---------------------------------------------------------------------------

from scripts.ingest_crunchbase_dump import parse_csv  # noqa: E402

CSV_HEADER = (
    "Organization Name,Organization Name URL,Organization Location,Announced Date,"
    "Funding Type,Money Raised,Money Raised Currency,Money Raised (in USD),"
    "Description,Transaction Name,Transaction Name URL\n"
)

CSV_SAMPLE = CSV_HEADER + (
    'Primero AI,https://www.crunchbase.com/organization/primero-ai,'
    '"Mexico City, Distrito Federal, Mexico, North America",2026-08-25,Seed,'
    '12000000,USD,12000000,Primero AI raised $12000000 on 2026-08-25 in Seed Round,'
    'Seed Round - Primero AI,https://www.crunchbase.com/funding_round/primero-ai-seed--cd83c950\n'
    'Flash,https://www.crunchbase.com/organization/flash-cd07,'
    '"São Paulo, Sao Paulo, Brazil, South America",2026-08-19,Series D,'
    '150000000,BRL,28776432,Flash raised $28776432 on 2026-08-19 in Series D,'
    'Series D - Flash,https://www.crunchbase.com/funding_round/flash-cd07-series-d--53cf67fb\n'
    'MercadoLibre,https://www.crunchbase.com/organization/mercadolibre,'
    '"Buenos Aires, Distrito Federal, Argentina, South America",2026-09-09,Post-IPO Debt,'
    '500000000,USD,500000000,MercadoLibre raised $500000000 on 2026-09-09 in Post-IPO Debt,'
    'Post-IPO Debt - MercadoLibre,https://www.crunchbase.com/funding_round/meli-debt\n'
    'Doroth,https://www.crunchbase.com/organization/doroth,'
    '"Piracicaba, Sao Paulo, Brazil, South America",2026-09-01,Venture - Series Unknown,'
    ',,,Doroth raised an undisclosed amount on 2026-09-01 in Venture Round,'
    'Venture Round - Doroth,https://www.crunchbase.com/funding_round/doroth-venture\n'
)


class TestParseCsv:
    def test_parses_vc_rounds_and_skips_debt(self):
        rounds = parse_csv(CSV_SAMPLE)
        slugs = [r.company_slug for r in rounds]
        assert slugs == ["primero-ai", "flash", "doroth"]

    def test_uses_usd_normalized_amount_not_local_currency(self):
        rounds = {r.company_slug: r for r in parse_csv(CSV_SAMPLE)}
        assert rounds["flash"].amount_usd == 28776432.0
        assert rounds["flash"].round_type == "series_d"

    def test_blank_amount_is_undisclosed(self):
        rounds = {r.company_slug: r for r in parse_csv(CSV_SAMPLE)}
        assert rounds["doroth"].amount_usd is None
        assert rounds["doroth"].round_type == "venture"

    def test_location_date_and_source_url(self):
        r = {x.company_slug: x for x in parse_csv(CSV_SAMPLE)}["primero-ai"]
        assert (r.city, r.country) == ("Mexico City", "Mexico")
        assert r.announced_date == date(2026, 8, 25)
        assert r.source_url.endswith("primero-ai-seed--cd83c950")
        assert r.source_name == "crunchbase_manual_dump"

    def test_missing_required_column_raises(self):
        with pytest.raises(ValueError, match="missing required columns"):
            parse_csv("Organization Name,Funding Type\nFoo,Seed\n")

    def test_bad_date_row_is_skipped(self):
        bad = CSV_HEADER + 'Foo,,"X, Y, Z, W",not-a-date,Seed,1,USD,1,,,\n'
        assert parse_csv(bad) == []

    def test_csv_rounds_dedup_against_dump_rounds(self):
        csv_rounds = parse_csv(CSV_SAMPLE)
        again = parse_csv(CSV_SAMPLE)
        assert len(dedup_rounds(csv_rounds + again)) == 3
