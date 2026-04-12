"""Integration tests for the Social Signals pipeline.

Tests run_pipeline() end-to-end with the LLM client mocked out and
classify_posts_batch patched so we control classification output without
making real API calls. The clusterer and scorer run against real logic.
"""

import re
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.social_signals.models import (
    PipelineResult,
    ProcessedSignal,
    SignalClusterResult,
    SocialPost,
)
from apps.agents.social_signals.pipeline import run_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_post(
    text: str,
    url: str = "",
    platform: str = "twitter",
    author_handle: str = "user1",
) -> SocialPost:
    return SocialPost(
        text=text,
        url=url or f"https://x.com/{author_handle}/1",
        platform=platform,
        author_handle=author_handle,
    )


def _make_signal(post: SocialPost, theme: str = "AI") -> ProcessedSignal:
    return ProcessedSignal(
        post=post,
        theme=theme,
        sentiment=0.3,
        authority_score=0.5,
    )


def _make_classified_signals(posts: List[SocialPost], theme: str = "AI") -> List[ProcessedSignal]:
    """Return pre-classified ProcessedSignal objects for the given posts."""
    return [_make_signal(post, theme=theme) for post in posts]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_llm():
    """A mock LLMClient that reports unavailable (no real API calls)."""
    client = MagicMock()
    client.is_available = False
    return client


@pytest.fixture()
def ai_posts() -> List[SocialPost]:
    """15 posts covering AI-agent and compliance themes."""
    texts = [
        "AI agents are transforming compliance workflows at scale",
        "LLM-powered agents now handle audit trails automatically",
        "Large language models reduce compliance costs by 40%",
        "Agent-based systems replacing manual KYC reviews",
        "Agentic AI cuts compliance headcount in financial services",
        "AI in banking: chargeback detection via neural nets",
        "Fraud detection using transformer models is now mainstream",
        "Fintech startups betting on embedded finance rails",
        "Open banking APIs enabling new payment experiences",
        "Stablecoin adoption growing among LATAM remittance corridors",
        "Nubank expansion into Mexico shows neobank potential",
        "PIX payment volumes surpass credit card transactions in Brazil",
        "Machine learning models outperform human underwriters",
        "Deep learning for credit scoring gains regulatory acceptance",
        "Foundation models fine-tuned for financial risk assessment",
    ]
    return [
        _make_post(text, url=f"https://x.com/user{i}/status/{i}", author_handle=f"user{i}")
        for i, text in enumerate(texts)
    ]


# ---------------------------------------------------------------------------
# Test 1: Empty posts
# ---------------------------------------------------------------------------


def test_empty_posts_returns_empty_result():
    result = run_pipeline(posts=[], skip_embeddings=True)

    assert isinstance(result, PipelineResult)
    assert result.clusters == []
    assert result.all_signals == []


# ---------------------------------------------------------------------------
# Test 2: Basic pipeline produces clusters with dimensions set
# ---------------------------------------------------------------------------


def test_basic_pipeline_produces_clusters(mock_llm, ai_posts):
    classified = _make_classified_signals(ai_posts, theme="AI")

    with patch(
        "apps.agents.social_signals.pipeline.classify_posts_batch",
        return_value=classified,
    ):
        result = run_pipeline(
            posts=ai_posts,
            llm_client=mock_llm,
            skip_embeddings=True,
            min_cluster_size=2,
        )

    assert isinstance(result, PipelineResult)
    assert len(result.clusters) >= 1, "Expected at least one cluster from 15 themed posts"

    for cluster in result.clusters:
        assert cluster.dimensions is not None, f"Cluster '{cluster.name}' is missing dimensions"


# ---------------------------------------------------------------------------
# Test 3: No themed signals → empty clusters, all_signals populated
# ---------------------------------------------------------------------------


def test_no_themed_signals_returns_empty_clusters(mock_llm, ai_posts):
    unthemed = [ProcessedSignal(post=p, theme="") for p in ai_posts]

    with patch(
        "apps.agents.social_signals.pipeline.classify_posts_batch",
        return_value=unthemed,
    ):
        result = run_pipeline(
            posts=ai_posts,
            llm_client=mock_llm,
            skip_embeddings=True,
        )

    assert result.clusters == [], "No themed signals should produce zero clusters"
    assert len(result.all_signals) == len(ai_posts), (
        "all_signals should contain every signal, even those without a theme"
    )


# ---------------------------------------------------------------------------
# Test 4: HTML in post text is stripped from cluster descriptions
# ---------------------------------------------------------------------------


def test_cluster_descriptions_are_html_free(mock_llm):
    html_posts = [
        _make_post(
            f"<p>AI agents are transforming compliance <b>sector {i}</b></p>",
            url=f"https://x.com/user{i}/status/{i}",
            author_handle=f"user{i}",
        )
        for i in range(10)
    ]
    classified = _make_classified_signals(html_posts, theme="AI")

    with patch(
        "apps.agents.social_signals.pipeline.classify_posts_batch",
        return_value=classified,
    ):
        result = run_pipeline(
            posts=html_posts,
            llm_client=mock_llm,
            skip_embeddings=True,
            min_cluster_size=2,
        )

    html_tag_pattern = re.compile(r"<[^>]+>")
    for cluster in result.clusters:
        assert not html_tag_pattern.search(cluster.description), (
            f"Cluster '{cluster.name}' description contains HTML: {cluster.description!r}"
        )


# ---------------------------------------------------------------------------
# Test 5: PipelineResult has signal_embeddings dict (may be empty)
# ---------------------------------------------------------------------------


def test_pipeline_result_contains_embeddings_key(mock_llm, ai_posts):
    classified = _make_classified_signals(ai_posts, theme="AI")

    with patch(
        "apps.agents.social_signals.pipeline.classify_posts_batch",
        return_value=classified,
    ):
        result = run_pipeline(
            posts=ai_posts,
            llm_client=mock_llm,
            skip_embeddings=True,
        )

    assert hasattr(result, "signal_embeddings"), "PipelineResult must have signal_embeddings"
    assert isinstance(result.signal_embeddings, dict)
    # With skip_embeddings=True the dict should be empty
    assert result.signal_embeddings == {}


# ---------------------------------------------------------------------------
# Test 6: PipelineResult has narrative_shifts list
# ---------------------------------------------------------------------------


def test_pipeline_result_contains_narrative_shifts(mock_llm, ai_posts):
    classified = _make_classified_signals(ai_posts, theme="AI")

    with patch(
        "apps.agents.social_signals.pipeline.classify_posts_batch",
        return_value=classified,
    ):
        result = run_pipeline(
            posts=ai_posts,
            llm_client=mock_llm,
            skip_embeddings=True,
            min_cluster_size=2,
        )

    assert hasattr(result, "narrative_shifts"), "PipelineResult must have narrative_shifts"
    assert isinstance(result.narrative_shifts, list)


# ---------------------------------------------------------------------------
# Test 7: Clusters are sorted descending by composite_score
# ---------------------------------------------------------------------------


def test_clusters_sorted_by_composite_score(mock_llm, ai_posts):
    classified = _make_classified_signals(ai_posts, theme="AI")

    with patch(
        "apps.agents.social_signals.pipeline.classify_posts_batch",
        return_value=classified,
    ):
        result = run_pipeline(
            posts=ai_posts,
            llm_client=mock_llm,
            skip_embeddings=True,
            min_cluster_size=2,
        )

    scores = [c.composite_score for c in result.clusters]
    assert scores == sorted(scores, reverse=True), (
        f"Clusters must be sorted descending by composite_score, got: {scores}"
    )


# ---------------------------------------------------------------------------
# Test 8: skip_embeddings=True uses TF-IDF path and still produces clusters
# ---------------------------------------------------------------------------


def test_skip_embeddings_uses_tfidf(mock_llm):
    posts = [
        _make_post(
            f"AI agents transforming compliance and fintech sector {i}",
            url=f"https://x.com/user{i}/status/{i}",
            author_handle=f"user{i}",
        )
        for i in range(12)
    ]
    classified = _make_classified_signals(posts, theme="AI")

    with patch(
        "apps.agents.social_signals.pipeline.classify_posts_batch",
        return_value=classified,
    ):
        # Confirm embedding generation is NOT called
        with patch(
            "apps.agents.social_signals.pipeline.generate_embeddings"
        ) as mock_embed:
            result = run_pipeline(
                posts=posts,
                llm_client=mock_llm,
                skip_embeddings=True,
                min_cluster_size=2,
            )
            mock_embed.assert_not_called()

    assert isinstance(result, PipelineResult)
    assert len(result.clusters) >= 1, "TF-IDF path should still produce clusters"
    assert result.signal_embeddings == {}, "skip_embeddings=True must leave embeddings empty"
