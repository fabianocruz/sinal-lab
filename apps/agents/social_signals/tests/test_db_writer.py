"""Tests for social_signals db_writer — upsert persistence functions.

Uses SQLite in-memory with StaticPool so all threads share the same
database connection. This matches the pattern used across the API test
suite (apps/api/tests/test_signals.py).

Run: python3 -m pytest apps/agents/social_signals/tests/test_db_writer.py -v
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base
from packages.database.models.signal_cluster import SignalCluster
from packages.database.models.social_signal import SocialSignal
from packages.database.models.weekly_pulse import WeeklyPulse

from apps.agents.social_signals.models import (
    EntityMention,
    ProcessedSignal,
    SignalClusterResult,
    SignalDimensions,
    SocialPost,
)

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite session per test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Helpers — factory functions for test data
# ---------------------------------------------------------------------------


def _make_post(
    url: str = "https://twitter.com/founder/status/123",
    text: str = "AI is disrupting LATAM fintech",
    platform: str = "twitter",
    author_handle: str = "founder_br",
    author_display_name: str = "Founder BR",
    published_at: Optional[datetime] = None,
) -> SocialPost:
    return SocialPost(
        text=text,
        url=url,
        platform=platform,
        author_handle=author_handle,
        author_display_name=author_display_name,
        author_followers=10000,
        published_at=published_at or datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc),
        metrics={"likes": 50, "replies": 5, "reposts": 12},
    )


def _make_signal(
    url: str = "https://twitter.com/founder/status/123",
    theme: str = "AI",
    sub_theme: str = "Fintech AI",
    sentiment: float = 0.7,
    authority_score: float = 0.8,
) -> ProcessedSignal:
    post = _make_post(url=url)
    return ProcessedSignal(
        post=post,
        theme=theme,
        sub_theme=sub_theme,
        entities=[
            EntityMention(name="Nubank", entity_type="company", confidence=0.9),
            EntityMention(name="Claude Moraes", entity_type="person", confidence=0.6),
        ],
        sentiment=sentiment,
        authority_score=authority_score,
    )


def _make_dimensions(
    volume: float = 0.6,
    velocity: float = 0.5,
    authority_concentration: float = 0.7,
    narrative_maturity: float = 0.4,
) -> SignalDimensions:
    return SignalDimensions(
        volume=volume,
        velocity=velocity,
        authority_concentration=authority_concentration,
        cross_platform_propagation=0.3,
        sentiment_shift=0.2,
        new_entrants=0.1,
        narrative_maturity=narrative_maturity,
        commercial_signals=0.2,
    )


def _make_cluster(
    name: str = "AI in Fintech",
    slug: str = "ai-in-fintech",
    theme: str = "AI",
    narrative_stage: str = "accelerating",
    signals: Optional[List[ProcessedSignal]] = None,
    composite_override: Optional[float] = None,
) -> SignalClusterResult:
    if signals is None:
        signals = [_make_signal()]

    dims = _make_dimensions()
    cluster = SignalClusterResult(
        name=name,
        slug=slug,
        theme=theme,
        sub_theme="Fintech AI",
        description="AI applications disrupting financial services in LATAM",
        signals=signals,
        dimensions=dims,
        narrative_stage=narrative_stage,
        top_voices=[{"handle": "founder_br", "name": "Founder BR", "authority": 0.8}],
        top_posts=[{"url": "https://twitter.com/founder/status/123", "text": "AI disrupts fintech"}],
        related_companies=[{"name": "Nubank", "mention_count": 5}],
    )

    # Allow forcing a composite_score for pulse quality filter tests
    if composite_override is not None:
        cluster.dimensions = SignalDimensions(
            volume=composite_override,
            velocity=composite_override,
            authority_concentration=composite_override,
            cross_platform_propagation=composite_override,
            sentiment_shift=composite_override,
            new_entrants=composite_override,
            narrative_maturity=composite_override,
            commercial_signals=composite_override,
        )

    return cluster


# ---------------------------------------------------------------------------
# Test 1: insert a new ProcessedSignal — verify all fields persisted
# ---------------------------------------------------------------------------


def test_upsert_new_signal_persists_all_fields(db_session):
    """Insert a new ProcessedSignal via _upsert_social_signal, verify all
    fields written to social_signals table."""
    from apps.agents.social_signals.db_writer import _upsert_social_signal

    signal = _make_signal()
    result = _upsert_social_signal(
        db_session,
        signal,
        cluster_db_id="cluster-uuid-001",
        agent_run_id="run-001",
    )
    db_session.commit()

    assert result == "inserted"

    row = db_session.query(SocialSignal).filter_by(content_hash=signal.content_hash).first()
    assert row is not None
    assert row.platform == "twitter"
    assert row.author_handle == "founder_br"
    assert row.author_display_name == "Founder BR"
    assert row.theme == "AI"
    assert row.sub_theme == "Fintech AI"
    assert row.sentiment == pytest.approx(0.7)
    assert row.authority_score == pytest.approx(0.8)
    assert row.cluster_id == "cluster-uuid-001"
    assert row.agent_run_id == "run-001"
    assert row.content_hash == signal.content_hash
    assert row.post_url == "https://twitter.com/founder/status/123"
    # Entities stored as list of dicts
    assert isinstance(row.entities, list)
    assert len(row.entities) == 2
    entity_names = {e["name"] for e in row.entities}
    assert entity_names == {"Nubank", "Claude Moraes"}


def test_upsert_new_signal_truncates_text_at_2000_chars(db_session):
    """Long post text must be truncated to 2000 characters on insert."""
    from apps.agents.social_signals.db_writer import _upsert_social_signal

    long_text = "A" * 3000
    post = _make_post(text=long_text)
    signal = ProcessedSignal(post=post, theme="AI", sentiment=0.0, authority_score=0.5)

    _upsert_social_signal(db_session, signal, agent_run_id="run-truncate")
    db_session.commit()

    row = db_session.query(SocialSignal).filter_by(content_hash=signal.content_hash).first()
    assert row is not None
    assert len(row.text) == 2000


def test_upsert_new_signal_with_empty_entities(db_session):
    """Signal with no entities stores empty list, not None, in DB."""
    from apps.agents.social_signals.db_writer import _upsert_social_signal

    post = _make_post(url="https://twitter.com/empty/status/999")
    signal = ProcessedSignal(post=post, theme="DevTools", entities=[], sentiment=0.1, authority_score=0.3)

    _upsert_social_signal(db_session, signal, agent_run_id="run-empty")
    db_session.commit()

    row = db_session.query(SocialSignal).filter_by(content_hash=signal.content_hash).first()
    assert row is not None
    assert row.entities == []


# ---------------------------------------------------------------------------
# Test 2: upsert existing signal — update classification, no duplicate
# ---------------------------------------------------------------------------


def test_upsert_existing_signal_updates_classification_not_duplicated(db_session):
    """Second upsert with same content_hash must update, not insert a new row."""
    from apps.agents.social_signals.db_writer import _upsert_social_signal

    signal = _make_signal(theme="AI", sentiment=0.4)

    result_1 = _upsert_social_signal(db_session, signal, agent_run_id="run-001")
    db_session.commit()
    assert result_1 == "inserted"

    # Mutate theme and sentiment — same content_hash
    signal.theme = "Fintech"
    signal.sub_theme = "Payments"
    signal.sentiment = 0.9

    result_2 = _upsert_social_signal(
        db_session, signal, cluster_db_id="new-cluster-id", agent_run_id="run-002"
    )
    db_session.commit()
    assert result_2 == "updated"

    # Only one row must exist
    all_rows = db_session.query(SocialSignal).filter_by(content_hash=signal.content_hash).all()
    assert len(all_rows) == 1

    row = all_rows[0]
    assert row.theme == "Fintech"
    assert row.sub_theme == "Payments"
    assert row.sentiment == pytest.approx(0.9)
    assert row.cluster_id == "new-cluster-id"
    assert row.agent_run_id == "run-002"


def test_upsert_existing_signal_preserves_theme_when_new_theme_empty(db_session):
    """If updated signal has empty theme, original theme must be preserved."""
    from apps.agents.social_signals.db_writer import _upsert_social_signal

    signal = _make_signal(theme="AI")
    _upsert_social_signal(db_session, signal, agent_run_id="run-001")
    db_session.commit()

    signal.theme = ""  # empty — should NOT overwrite existing
    _upsert_social_signal(db_session, signal, agent_run_id="run-002")
    db_session.commit()

    row = db_session.query(SocialSignal).filter_by(content_hash=signal.content_hash).first()
    assert row.theme == "AI"  # original preserved


# ---------------------------------------------------------------------------
# Test 3: upsert SignalClusterResult — verify slug includes year-week format
# ---------------------------------------------------------------------------


def test_upsert_signal_cluster_slug_includes_year_week_format(db_session):
    """_upsert_signal_cluster must produce slug in '{original}-{year}-w{week:02d}' format."""
    from apps.agents.social_signals.db_writer import _upsert_signal_cluster

    cluster = _make_cluster(slug="ai-in-fintech")
    db_id = _upsert_signal_cluster(
        db_session, cluster, week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    assert db_id is not None
    # Query by slug — avoids UUID type coercion issues with SQLite
    row = db_session.query(SignalCluster).filter_by(slug="ai-in-fintech-2026-w15").first()
    assert row is not None
    assert row.slug == "ai-in-fintech-2026-w15"
    assert str(row.id) == db_id


def test_upsert_signal_cluster_persists_all_fields(db_session):
    """All cluster fields must be written correctly on insert."""
    from apps.agents.social_signals.db_writer import _upsert_signal_cluster

    cluster = _make_cluster(
        name="AI in Fintech",
        slug="ai-in-fintech",
        theme="AI",
        narrative_stage="accelerating",
    )
    _upsert_signal_cluster(
        db_session, cluster, week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    row = db_session.query(SignalCluster).filter_by(slug="ai-in-fintech-2026-w15").first()
    assert row is not None
    assert row.name == "AI in Fintech"
    assert row.theme == "AI"
    assert row.sub_theme == "Fintech AI"
    assert row.narrative_stage == "accelerating"
    assert row.week_number == 15
    assert row.year == 2026
    assert row.agent_run_id == "run-001"
    assert row.signal_count == 1  # one signal in the cluster
    assert isinstance(row.dimensions, dict)
    assert "volume" in row.dimensions
    assert isinstance(row.top_voices, list)
    assert len(row.top_voices) == 1
    assert row.top_voices[0]["handle"] == "founder_br"


def test_upsert_signal_cluster_single_digit_week_has_leading_zero(db_session):
    """Week numbers 1-9 must be zero-padded in the slug: w01, w09."""
    from apps.agents.social_signals.db_writer import _upsert_signal_cluster

    cluster = _make_cluster(slug="funding-surge")
    _upsert_signal_cluster(
        db_session, cluster, week_number=3, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    row = db_session.query(SignalCluster).filter_by(slug="funding-surge-2026-w03").first()
    assert row is not None
    assert row.slug == "funding-surge-2026-w03"


# ---------------------------------------------------------------------------
# Test 4: cluster slug uniqueness — same slug same week → update not duplicate
# ---------------------------------------------------------------------------


def test_upsert_cluster_slug_uniqueness_updates_not_duplicates(db_session):
    """Upserting the same cluster slug+week twice must update the existing row."""
    from apps.agents.social_signals.db_writer import _upsert_signal_cluster

    cluster = _make_cluster(name="AI in Fintech", slug="ai-in-fintech")
    db_id_1 = _upsert_signal_cluster(
        db_session, cluster, week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    # Second upsert: updated name and signal count
    cluster.name = "AI in Fintech (updated)"
    # Add another signal to bump signal_count
    cluster.signals.append(_make_signal(url="https://twitter.com/another/status/456"))

    db_id_2 = _upsert_signal_cluster(
        db_session, cluster, week_number=15, year=2026, agent_run_id="run-002"
    )
    db_session.commit()

    # Same DB id returned — same row
    assert db_id_1 == db_id_2

    # Only one cluster row for that slug
    rows = db_session.query(SignalCluster).filter_by(slug="ai-in-fintech-2026-w15").all()
    assert len(rows) == 1

    row = rows[0]
    assert row.name == "AI in Fintech (updated)"
    assert row.signal_count == 2
    assert row.agent_run_id == "run-002"


def test_upsert_cluster_different_weeks_creates_separate_rows(db_session):
    """Same base slug in different weeks must produce two distinct DB rows."""
    from apps.agents.social_signals.db_writer import _upsert_signal_cluster

    cluster = _make_cluster(slug="funding-surge")

    _upsert_signal_cluster(db_session, cluster, week_number=14, year=2026, agent_run_id="run-1")
    _upsert_signal_cluster(db_session, cluster, week_number=15, year=2026, agent_run_id="run-2")
    db_session.commit()

    w14 = db_session.query(SignalCluster).filter_by(slug="funding-surge-2026-w14").first()
    w15 = db_session.query(SignalCluster).filter_by(slug="funding-surge-2026-w15").first()

    assert w14 is not None
    assert w15 is not None
    assert str(w14.id) != str(w15.id)


# ---------------------------------------------------------------------------
# Test 5: weekly pulse upsert — verify accelerating_themes and emerging_signals
# ---------------------------------------------------------------------------


def test_weekly_pulse_upsert_populates_accelerating_and_emerging(db_session):
    """_upsert_weekly_pulse must separate clusters by narrative_stage."""
    from apps.agents.social_signals.db_writer import _upsert_weekly_pulse

    # Cluster with high-enough composite score (> MIN_CLUSTER_COMPOSITE_SCORE = 0.3)
    accelerating = _make_cluster(
        name="AI in Fintech",
        slug="ai-in-fintech",
        narrative_stage="accelerating",
        composite_override=0.8,
    )
    emerging = _make_cluster(
        name="DevTools LATAM",
        slug="devtools-latam",
        narrative_stage="emerging",
        composite_override=0.5,
    )

    result = _upsert_weekly_pulse(
        db_session, [accelerating, emerging], week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    assert result == "inserted"

    row = db_session.query(WeeklyPulse).filter_by(slug="pulse-2026-w15").first()
    assert row is not None
    assert row.week_number == 15
    assert row.year == 2026
    assert row.status == "draft"
    assert row.agent_run_id == "run-001"

    accelerating_names = [t["name"] for t in row.accelerating_themes]
    assert "AI in Fintech" in accelerating_names

    emerging_names = [s["name"] for s in row.emerging_signals]
    assert "DevTools LATAM" in emerging_names


def test_weekly_pulse_upsert_updates_existing_row(db_session):
    """Second call with same week must update, not insert a duplicate."""
    from apps.agents.social_signals.db_writer import _upsert_weekly_pulse

    cluster = _make_cluster(name="AI in Fintech", narrative_stage="accelerating", composite_override=0.8)

    result_1 = _upsert_weekly_pulse(
        db_session, [cluster], week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()
    assert result_1 == "inserted"

    # Second call — different cluster name
    cluster.name = "AI in Fintech v2"
    result_2 = _upsert_weekly_pulse(
        db_session, [cluster], week_number=15, year=2026, agent_run_id="run-002"
    )
    db_session.commit()
    assert result_2 == "updated"

    rows = db_session.query(WeeklyPulse).filter_by(slug="pulse-2026-w15").all()
    assert len(rows) == 1
    assert rows[0].agent_run_id == "run-002"


def test_weekly_pulse_excludes_low_score_clusters(db_session):
    """Clusters below MIN_CLUSTER_COMPOSITE_SCORE (0.3) must be excluded."""
    from apps.agents.social_signals.db_writer import _upsert_weekly_pulse

    low_score = _make_cluster(
        name="Low Signal Cluster",
        slug="low-signal",
        narrative_stage="accelerating",
        composite_override=0.1,  # below 0.3 threshold
    )

    _upsert_weekly_pulse(
        db_session, [low_score], week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    row = db_session.query(WeeklyPulse).filter_by(slug="pulse-2026-w15").first()
    assert row is not None
    # accelerating_themes empty because cluster was filtered out
    assert row.accelerating_themes == []


def test_weekly_pulse_excludes_blocklisted_cluster_names(db_session):
    """Clusters whose names match CLUSTER_NAME_BLOCKLIST must be excluded from pulse."""
    from apps.agents.social_signals.db_writer import _upsert_weekly_pulse

    # "publicações diversas" is in the blocklist
    blocklisted = _make_cluster(
        name="Publicações Diversas de Redes Sociais",
        slug="publicacoes-diversas",
        narrative_stage="accelerating",
        composite_override=0.9,  # high score — should still be excluded
    )

    _upsert_weekly_pulse(
        db_session, [blocklisted], week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    row = db_session.query(WeeklyPulse).filter_by(slug="pulse-2026-w15").first()
    assert row is not None
    assert row.accelerating_themes == []


def test_weekly_pulse_aggregates_top_voices_deduped_by_handle(db_session):
    """top_voices in pulse must deduplicate by handle across clusters."""
    from apps.agents.social_signals.db_writer import _upsert_weekly_pulse

    shared_voice = {"handle": "founder_br", "name": "Founder BR", "authority": 0.9}

    c1 = _make_cluster(name="AI", slug="ai", composite_override=0.8)
    c1.top_voices = [shared_voice]

    c2 = _make_cluster(name="Fintech", slug="fintech", composite_override=0.7)
    c2.top_voices = [shared_voice]  # same handle — must appear only once

    _upsert_weekly_pulse(
        db_session, [c1, c2], week_number=15, year=2026, agent_run_id="run-001"
    )
    db_session.commit()

    row = db_session.query(WeeklyPulse).filter_by(slug="pulse-2026-w15").first()
    handles = [v["handle"] for v in (row.top_voices or [])]
    assert handles.count("founder_br") == 1


# ---------------------------------------------------------------------------
# Test 6: persist_social_signals full flow with MockAgent
# ---------------------------------------------------------------------------


class MockAgent:
    """Minimal mock of SocialSignalsAgent for persist_social_signals tests."""

    def __init__(
        self,
        clusters: List[SignalClusterResult],
        all_signals: List[ProcessedSignal],
        week_number: int = 15,
        run_id: str = "test-run-001",
    ) -> None:
        self._clusters = clusters
        self._all_signals = all_signals
        self.week_number = week_number
        self.run_id = run_id


def test_persist_social_signals_full_flow_creates_clusters_signals_and_pulse(db_session):
    """persist_social_signals() must atomically create clusters, signals, and pulse."""
    from apps.agents.social_signals.db_writer import persist_social_signals

    signal_a = _make_signal(
        url="https://twitter.com/founder/status/111",
        theme="AI",
        sentiment=0.8,
        authority_score=0.9,
    )
    signal_b = _make_signal(
        url="https://reddit.com/r/startups/post/222",
        theme="AI",
        sentiment=0.6,
        authority_score=0.7,
    )
    signal_b.post.platform = "reddit"

    cluster = _make_cluster(
        name="AI in Fintech",
        slug="ai-in-fintech",
        narrative_stage="accelerating",
        signals=[signal_a, signal_b],
        composite_override=0.8,
    )

    agent = MockAgent(
        clusters=[cluster],
        all_signals=[signal_a, signal_b],
        week_number=15,
        run_id="test-run-001",
    )

    # persist_social_signals imports get_last_signal_embeddings lazily inside a
    # try/except ImportError block — patch at the pipeline module level.
    with patch(
        "apps.agents.social_signals.pipeline.get_last_signal_embeddings",
        return_value={},
    ):
        persist_social_signals(agent, agent_output=None, session=db_session)

    db_session.commit()

    # Clusters persisted
    clusters_in_db = db_session.query(SignalCluster).all()
    assert len(clusters_in_db) == 1
    assert clusters_in_db[0].slug == "ai-in-fintech-2026-w15"

    # Signals persisted
    signals_in_db = db_session.query(SocialSignal).all()
    assert len(signals_in_db) == 2
    platforms = {s.platform for s in signals_in_db}
    assert platforms == {"twitter", "reddit"}

    # Signals linked to cluster (cluster_id stored as string UUID)
    cluster_db_id = str(clusters_in_db[0].id)
    for sig in signals_in_db:
        assert sig.cluster_id == cluster_db_id

    # Pulse persisted
    pulses_in_db = db_session.query(WeeklyPulse).all()
    assert len(pulses_in_db) == 1
    pulse = pulses_in_db[0]
    assert pulse.slug == "pulse-2026-w15"
    assert pulse.status == "draft"
    assert pulse.agent_run_id == "test-run-001"
    accelerating_names = [t["name"] for t in (pulse.accelerating_themes or [])]
    assert "AI in Fintech" in accelerating_names


def test_persist_social_signals_no_clusters_skips_pulse(db_session):
    """persist_social_signals() must not create a pulse when there are no clusters."""
    from apps.agents.social_signals.db_writer import persist_social_signals

    signal = _make_signal()
    agent = MockAgent(clusters=[], all_signals=[signal], week_number=15, run_id="run-empty")

    with patch(
        "apps.agents.social_signals.pipeline.get_last_signal_embeddings",
        return_value={},
    ):
        persist_social_signals(agent, agent_output=None, session=db_session)

    db_session.commit()

    assert db_session.query(WeeklyPulse).count() == 0
    # The unclustered signal is still persisted (cluster_id will be None)
    assert db_session.query(SocialSignal).count() == 1
    row = db_session.query(SocialSignal).first()
    assert row.cluster_id is None


def test_persist_social_signals_signal_linked_to_correct_cluster(db_session):
    """Signals belonging to a cluster must carry its cluster_id, others get None."""
    from apps.agents.social_signals.db_writer import persist_social_signals

    clustered_signal = _make_signal(url="https://twitter.com/a/status/1", theme="AI")
    orphan_signal = _make_signal(url="https://twitter.com/b/status/2", theme="Funding")

    cluster = _make_cluster(
        name="AI Cluster",
        slug="ai-cluster",
        signals=[clustered_signal],
        composite_override=0.8,
    )

    agent = MockAgent(
        clusters=[cluster],
        all_signals=[clustered_signal, orphan_signal],
        week_number=15,
        run_id="run-link-test",
    )

    with patch(
        "apps.agents.social_signals.pipeline.get_last_signal_embeddings",
        return_value={},
    ):
        persist_social_signals(agent, agent_output=None, session=db_session)

    db_session.commit()

    rows = db_session.query(SocialSignal).all()
    assert len(rows) == 2

    cluster_row = db_session.query(SignalCluster).first()
    cluster_db_id = str(cluster_row.id)

    by_hash = {r.content_hash: r for r in rows}
    assert by_hash[clustered_signal.content_hash].cluster_id == cluster_db_id
    assert by_hash[orphan_signal.content_hash].cluster_id is None


def test_persist_social_signals_idempotent_on_second_run(db_session):
    """Running persist_social_signals twice with same data must not duplicate rows."""
    from apps.agents.social_signals.db_writer import persist_social_signals

    signal = _make_signal(theme="AI", sentiment=0.7)
    cluster = _make_cluster(signals=[signal], composite_override=0.8)

    agent = MockAgent(clusters=[cluster], all_signals=[signal], week_number=15, run_id="run-001")

    for _ in range(2):
        with patch(
            "apps.agents.social_signals.pipeline.get_last_signal_embeddings",
            return_value={},
        ):
            persist_social_signals(agent, agent_output=None, session=db_session)
        db_session.commit()

    assert db_session.query(SocialSignal).count() == 1
    assert db_session.query(SignalCluster).count() == 1
    assert db_session.query(WeeklyPulse).count() == 1


# ---------------------------------------------------------------------------
# Cluster identity — a bucket is what it contains, not what the LLM called it
# ---------------------------------------------------------------------------


def _persist_run(db_session, name: str, slug: str, signals, run_id: str) -> str:
    """Persist one agent run: cluster row plus its signals, linked.

    Mirrors what persist_social_signals_data does — the cluster is upserted
    first, then each signal is written carrying that cluster's id.
    """
    from apps.agents.social_signals.db_writer import (
        _upsert_signal_cluster,
        _upsert_social_signal,
    )

    cluster = _make_cluster(name=name, slug=slug, signals=signals)
    cluster_db_id = _upsert_signal_cluster(
        db_session, cluster, week_number=17, year=2026, agent_run_id=run_id
    )
    for signal in signals:
        _upsert_social_signal(
            db_session, signal, agent_run_id=run_id, cluster_db_id=cluster_db_id
        )
    db_session.commit()
    return cluster_db_id


def _signals(n: int, offset: int = 0):
    return [
        _make_signal(url=f"https://twitter.com/founder/status/{i + offset}")
        for i in range(n)
    ]


def test_relabelled_cluster_updates_instead_of_inserting(db_session):
    """The same signals under a new LLM name must not create a second row.

    This is the root cause of ~277 cluster rows a week for ~10 real
    clusters: the upsert key was a slug of a name regenerated every run.
    """
    signals = _signals(10)

    first = _persist_run(
        db_session, "Operacoes e Crescimento de Startups", "operacoes-crescimento", signals, "run-1"
    )
    second = _persist_run(
        db_session, "Comunidade de Fundadores e Operacoes", "comunidade-fundadores", signals, "run-2"
    )

    assert first == second, "same signals must resolve to the same cluster row"
    assert db_session.query(SignalCluster).count() == 1


def test_relabelled_cluster_keeps_its_published_name_and_slug(db_session):
    """Identity is stable: the site keeps linking to the same URL and title."""
    signals = _signals(10)

    _persist_run(db_session, "Operacoes e Crescimento", "operacoes-crescimento", signals, "run-1")
    _persist_run(db_session, "Nome Totalmente Diferente", "nome-diferente", signals, "run-2")

    row = db_session.query(SignalCluster).one()
    assert row.name == "Operacoes e Crescimento"
    assert row.slug == "operacoes-crescimento-2026-w17"


def test_relabelled_cluster_still_refreshes_its_metrics(db_session):
    """Keeping the name must not freeze the numbers."""
    signals = _signals(10)
    _persist_run(db_session, "Primeiro Nome", "primeiro-nome", signals, "run-1")

    grown = signals + _signals(6, offset=100)
    _persist_run(db_session, "Segundo Nome", "segundo-nome", grown, "run-2")

    row = db_session.query(SignalCluster).one()
    assert row.signal_count == 16
    assert row.agent_run_id == "run-2"


def test_cluster_growing_during_the_week_is_still_the_same_cluster(db_session):
    """The signal pool grows between runs; a superset is not a new bucket."""
    base = _signals(10)
    _persist_run(db_session, "Cluster A", "cluster-a", base, "run-1")
    _persist_run(db_session, "Cluster A rotulado outra vez", "cluster-a-2", base + _signals(5, offset=200), "run-2")

    assert db_session.query(SignalCluster).count() == 1


def test_genuinely_different_clusters_are_not_merged(db_session):
    """Disjoint signals must stay separate rows."""
    _persist_run(db_session, "Fintech LATAM", "fintech-latam", _signals(10), "run-1")
    _persist_run(db_session, "DevTools LATAM", "devtools-latam", _signals(10, offset=500), "run-1")

    assert db_session.query(SignalCluster).count() == 2


def test_small_overlap_does_not_merge_clusters(db_session):
    """A few shared posts is not the same bucket — the floor guards this."""
    shared = _signals(3)
    _persist_run(db_session, "Cluster A", "cluster-a", shared + _signals(9, offset=300), "run-1")
    _persist_run(db_session, "Cluster B", "cluster-b", shared + _signals(9, offset=600), "run-2")

    assert db_session.query(SignalCluster).count() == 2


def test_different_weeks_still_create_separate_clusters(db_session):
    """Week boundaries keep history intact even for identical signals."""
    from apps.agents.social_signals.db_writer import (
        _upsert_signal_cluster,
        _upsert_social_signal,
    )

    signals = _signals(10)
    cluster = _make_cluster(name="Mesmo Cluster", slug="mesmo-cluster", signals=signals)

    id_w17 = _upsert_signal_cluster(db_session, cluster, week_number=17, year=2026, agent_run_id="r1")
    for s in signals:
        _upsert_social_signal(db_session, s, agent_run_id="r1", cluster_db_id=id_w17)
    db_session.commit()

    id_w18 = _upsert_signal_cluster(db_session, cluster, week_number=18, year=2026, agent_run_id="r2")
    db_session.commit()

    assert id_w17 != id_w18
    assert db_session.query(SignalCluster).count() == 2
