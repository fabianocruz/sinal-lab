"""Tests for the MERCADO v2 editorial classifier.

Regression focus: a thin week (one real funding round) used to produce
"0 movimentos" because every bucket fell below min_events_per_section
and was silently dropped.
"""

from datetime import date

from apps.agents.mercado.market_event import MarketEvent
from apps.agents.mercado.v2_classifier import (
    DEFAULT_BUCKET,
    build_sections,
    classify_event,
    group_by_sector,
)


def _event(
    company: str = "Plata",
    sector: str = "Fintech",
    amount_usd: float = 405_000_000.0,
    title: str = None,
) -> MarketEvent:
    """Build a realistic funding MarketEvent (shape from v2_collector)."""
    return MarketEvent(
        company_name=company,
        company_slug=company.lower(),
        event_type="funding_round",
        occurred_at=date(2026, 8, 10),
        sector=sector,
        country="MX",
        amount_usd=amount_usd,
        round_type="series_c",
        title=title or f"{company} — Série C (${amount_usd / 1_000_000:.0f}M)",
        summary=f"{company} levantou capital para expandir sua operação.",
        source_url=f"https://example.com/{company.lower()}",
        source_name="crunchbase_manual_dump",
        investors=["Kaszek"],
    )


class TestClassifyEvent:
    """Sector bucket assignment."""

    def test_fintech_event(self) -> None:
        assert classify_event(_event(sector="Fintech")) == "fintech"

    def test_ai_event(self) -> None:
        assert classify_event(_event(company="Neuro", sector="AI")) == "ai"

    def test_unknown_sector_falls_back_to_default_bucket(self) -> None:
        event = MarketEvent(
            company_name="Genericorp",
            company_slug="genericorp",
            event_type="funding_round",
            occurred_at=date(2026, 8, 10),
            title="Genericorp capta rodada",
        )

        assert classify_event(event) == DEFAULT_BUCKET[0]

    def test_group_by_sector(self) -> None:
        groups = group_by_sector([
            _event(company="Plata", sector="Fintech"),
            _event(company="Neuro", sector="AI"),
        ])

        assert set(groups) == {"fintech", "ai"}


class TestBuildSectionsThinWeek:
    """A non-empty event list must always yield a non-empty section."""

    def test_single_event_still_produces_a_section(self) -> None:
        sections = build_sections([_event()], max_sections=4, min_events_per_section=2)

        assert len(sections) >= 1
        assert sum(len(s.events) for s in sections) == 1
        assert sections[0].heading

    def test_single_event_is_preserved_verbatim(self) -> None:
        event = _event()

        sections = build_sections([event], max_sections=4, min_events_per_section=2)

        assert sections[0].events[0] is event

    def test_thin_buckets_merge_into_cross_section(self) -> None:
        """Three lonely sector events become one general section."""
        events = [
            _event(company="Plata", sector="Fintech"),
            _event(company="Neuro", sector="AI"),
            _event(company="Deployx", sector="DevTools"),
        ]

        sections = build_sections(events, max_sections=4, min_events_per_section=2)

        assert len(sections) == 1
        assert sections[0].sector_slug == DEFAULT_BUCKET[0]
        assert len(sections[0].events) == 3

    def test_empty_input_produces_no_sections(self) -> None:
        assert build_sections([], max_sections=4, min_events_per_section=2) == []


class TestBuildSectionsNormalWeek:
    """Behaviour with enough volume must not change."""

    def test_qualifying_bucket_becomes_its_own_section(self) -> None:
        events = [
            _event(company="Plata", sector="Fintech"),
            _event(company="Kesh", sector="Fintech"),
            _event(company="Nubank", sector="Fintech"),
        ]

        sections = build_sections(events, max_sections=4, min_events_per_section=2)

        assert len(sections) == 1
        assert sections[0].sector_slug == "fintech"
        assert len(sections[0].events) == 3

    def test_thin_bucket_merges_alongside_qualifying_bucket(self) -> None:
        """A lone event is not dropped when other sectors qualify."""
        events = [
            _event(company="Plata", sector="Fintech"),
            _event(company="Kesh", sector="Fintech"),
            _event(company="Neuro", sector="AI"),
            _event(company="Mind", sector="AI"),
            _event(company="Deployx", sector="DevTools"),
        ]

        sections = build_sections(events, max_sections=4, min_events_per_section=2)

        slugs = {s.sector_slug for s in sections}
        assert {"fintech", "ai"} <= slugs
        assert sum(len(s.events) for s in sections) == 5

    def test_sections_are_ordered_by_editorial_weight(self) -> None:
        events = [
            _event(company="Plata", sector="Fintech", amount_usd=405_000_000.0),
            _event(company="Kesh", sector="Fintech", amount_usd=110_000_000.0),
            _event(company="Neuro", sector="AI", amount_usd=1_000_000.0),
            _event(company="Mind", sector="AI", amount_usd=2_000_000.0),
        ]

        sections = build_sections(events, max_sections=4, min_events_per_section=2)

        assert [s.sector_slug for s in sections] == ["fintech", "ai"]

    def test_agent_process_phase_keeps_a_single_event(self) -> None:
        """End-to-end guard for the reported "0 movimentos" symptom."""
        from apps.agents.mercado.agent import MercadoAgent

        sections = MercadoAgent(week_number=33).process([_event()])

        assert len(sections) >= 1
        assert sum(len(s.events) for s in sections) == 1

    def test_max_sections_is_respected(self) -> None:
        events = []
        for sector in ("Fintech", "AI", "DevTools", "Marketplace", "HealthTech"):
            events.extend([
                _event(company=f"{sector}1", sector=sector),
                _event(company=f"{sector}2", sector=sector),
            ])

        sections = build_sections(events, max_sections=2, min_events_per_section=2)

        assert len(sections) == 2
