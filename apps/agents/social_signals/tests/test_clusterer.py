"""Tests for social signals clusterer — cluster_signals, _build_cluster_results,
_merge_similar_clusters, label_cluster, slugify_cluster_name, _cluster_by_theme."""

import pytest

from apps.agents.social_signals.clusterer import (
    _build_cluster_results,
    _cluster_by_theme,
    _merge_similar_clusters,
    cluster_signals,
    label_cluster,
    slugify_cluster_name,
)
from apps.agents.social_signals.models import (
    ProcessedSignal,
    SignalClusterResult,
    SocialPost,
)


# ---------------------------------------------------------------------------
# Shared helper — mirrors test_scorer._make_signal
# ---------------------------------------------------------------------------


def _make_signal(
    text: str = "test signal",
    platform: str = "twitter",
    author_handle: str = "user1",
    author_followers: int = 1000,
    authority_score: float = 0.5,
    sentiment: float = 0.0,
    is_commercial: bool = False,
    theme: str = "AI",
    sub_theme: str = "",
    url: str = "",
) -> ProcessedSignal:
    resolved_url = url or f"https://twitter.com/{author_handle}/status/1"
    post = SocialPost(
        text=text,
        url=resolved_url,
        platform=platform,
        author_handle=author_handle,
        author_display_name=author_handle,
        author_followers=author_followers,
        metrics={"likes": 0, "replies": 0, "reposts": 0},
    )
    return ProcessedSignal(
        post=post,
        theme=theme,
        sub_theme=sub_theme,
        authority_score=authority_score,
        sentiment=sentiment,
        is_commercial=is_commercial,
    )


# ---------------------------------------------------------------------------
# slugify_cluster_name
# ---------------------------------------------------------------------------


class TestSlugifyClusterName:
    def test_regular_ascii_text(self):
        assert slugify_cluster_name("AI Agents for Compliance") == "ai-agents-for-compliance"

    def test_accented_portuguese_chars(self):
        # ã, ç, é, ê, ô should be stripped or transliterated
        result = slugify_cluster_name("Inteligência Artificial")
        assert result == "inteligencia-artificial"

    def test_accented_fintech_label(self):
        result = slugify_cluster_name("Finanças Embutidas")
        assert result == "financas-embutidas"

    def test_empty_string_returns_fallback(self):
        assert slugify_cluster_name("") == "unnamed-cluster"

    def test_special_characters_become_hyphens(self):
        result = slugify_cluster_name("AI & Machine Learning: 2026!")
        assert "&" not in result
        assert "!" not in result
        assert ":" not in result
        # Should still produce a valid slug
        assert result.startswith("ai")

    def test_no_leading_or_trailing_hyphens(self):
        result = slugify_cluster_name("  --- Startups ---  ")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_consecutive_special_chars_collapse(self):
        result = slugify_cluster_name("AI  &&  FinTech")
        assert "--" not in result

    def test_all_special_chars_returns_fallback(self):
        result = slugify_cluster_name("!@#$%^&*()")
        assert result == "unnamed-cluster"

    def test_numbers_preserved(self):
        result = slugify_cluster_name("Web3 e DeFi 2026")
        assert "web3" in result
        assert "2026" in result


# ---------------------------------------------------------------------------
# label_cluster (no LLM — fallback path)
# ---------------------------------------------------------------------------


class TestLabelClusterFallback:
    def test_known_theme_returns_portuguese_label(self):
        signals = [_make_signal(theme="AI", sub_theme="") for _ in range(3)]
        result = label_cluster(signals, llm_client=None)
        assert result == "Inteligencia Artificial"

    def test_known_theme_sub_theme_combo(self):
        signals = [_make_signal(theme="AI", sub_theme="AI agents") for _ in range(3)]
        result = label_cluster(signals, llm_client=None)
        assert result == "Agentes de IA"

    def test_known_fintech_theme(self):
        signals = [_make_signal(theme="Fintech", sub_theme="Neobanks") for _ in range(2)]
        result = label_cluster(signals, llm_client=None)
        assert result == "Neobancos"

    def test_unknown_theme_returns_raw_key(self):
        # A theme not in _PORTUGUESE_LABELS should be returned as-is
        signals = [_make_signal(theme="SomeUnknownTheme", sub_theme="") for _ in range(2)]
        result = label_cluster(signals, llm_client=None)
        assert result == "SomeUnknownTheme"

    def test_unknown_theme_with_sub_theme_returns_combined_key(self):
        signals = [_make_signal(theme="SomeTheme", sub_theme="SomeSub") for _ in range(2)]
        result = label_cluster(signals, llm_client=None)
        assert result == "SomeTheme: SomeSub"

    def test_no_theme_returns_fallback(self):
        signals = [_make_signal(theme="", sub_theme="") for _ in range(2)]
        result = label_cluster(signals, llm_client=None)
        # Falls back to "General" key or "Sinais Diversos" when no theme set
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_signals_returns_fallback_string(self):
        result = label_cluster([], llm_client=None)
        assert result == "Sinais Diversos"

    def test_most_common_theme_wins(self):
        # 3 signals with "Fintech: Neobanks", 1 with "AI"
        signals = [_make_signal(theme="Fintech", sub_theme="Neobanks") for _ in range(3)]
        signals.append(_make_signal(theme="AI", sub_theme=""))
        result = label_cluster(signals, llm_client=None)
        assert result == "Neobancos"


# ---------------------------------------------------------------------------
# _cluster_by_theme (fallback clustering)
# ---------------------------------------------------------------------------


class TestClusterByTheme:
    def test_groups_by_theme(self):
        signals = [
            _make_signal(theme="AI", sub_theme=""),
            _make_signal(theme="AI", sub_theme=""),
            _make_signal(theme="Fintech", sub_theme=""),
        ]
        result = _cluster_by_theme(signals)
        assert "AI" in result
        assert "Fintech" in result
        assert len(result["AI"]) == 2
        assert len(result["Fintech"]) == 1

    def test_splits_by_sub_theme(self):
        signals = [
            _make_signal(theme="AI", sub_theme="AI agents"),
            _make_signal(theme="AI", sub_theme="LLM infrastructure"),
        ]
        result = _cluster_by_theme(signals)
        assert "AI/AI agents" in result
        assert "AI/LLM infrastructure" in result

    def test_no_theme_goes_to_uncategorized(self):
        signals = [_make_signal(theme="", sub_theme="")]
        result = _cluster_by_theme(signals)
        assert "uncategorized" in result

    def test_empty_input_returns_empty_dict(self):
        result = _cluster_by_theme([])
        assert result == {}

    def test_same_theme_different_sub_theme_separate_groups(self):
        signals = [
            _make_signal(theme="Fintech", sub_theme="Payments infrastructure"),
            _make_signal(theme="Fintech", sub_theme="Neobanks"),
            _make_signal(theme="Fintech", sub_theme="Neobanks"),
        ]
        result = _cluster_by_theme(signals)
        assert len(result["Fintech/Neobanks"]) == 2
        assert len(result["Fintech/Payments infrastructure"]) == 1


# ---------------------------------------------------------------------------
# _merge_similar_clusters
# ---------------------------------------------------------------------------


class TestMergeSimilarClusters:
    def _make_cluster(
        self, name: str, slug: str, signal_count: int = 5
    ) -> SignalClusterResult:
        signals = [_make_signal() for _ in range(signal_count)]
        return SignalClusterResult(
            name=name,
            slug=slug,
            theme="AI",
            sub_theme="",
            signals=signals,
        )

    def test_no_duplicates_passthrough(self):
        clusters = [
            self._make_cluster("Agentes de IA", "agentes-de-ia"),
            self._make_cluster("Neobancos", "neobancos"),
        ]
        result = _merge_similar_clusters(clusters)
        assert len(result) == 2

    def test_identical_slugs_merged(self):
        clusters = [
            self._make_cluster("Agentes de IA", "agentes-de-ia", signal_count=6),
            self._make_cluster("Agentes de IA", "agentes-de-ia", signal_count=4),
        ]
        result = _merge_similar_clusters(clusters)
        assert len(result) == 1
        assert result[0].slug == "agentes-de-ia"

    def test_merged_signal_count_is_combined(self):
        clusters = [
            self._make_cluster("Cluster A", "cluster-a", signal_count=7),
            self._make_cluster("Cluster A", "cluster-a", signal_count=3),
        ]
        result = _merge_similar_clusters(clusters)
        assert result[0].signal_count == 10

    def test_merged_name_comes_from_largest(self):
        # Cluster with 8 signals uses name "Agentes de IA (maior)"
        larger = self._make_cluster("Agentes de IA maior", "agentes-de-ia", signal_count=8)
        smaller = self._make_cluster("Agentes de IA menor", "agentes-de-ia", signal_count=2)
        result = _merge_similar_clusters([smaller, larger])
        assert result[0].name == "Agentes de IA maior"

    def test_single_cluster_passthrough(self):
        clusters = [self._make_cluster("Solo", "solo")]
        result = _merge_similar_clusters(clusters)
        assert len(result) == 1

    def test_empty_list_passthrough(self):
        result = _merge_similar_clusters([])
        assert result == []

    def test_three_identical_slugs_merged_into_one(self):
        clusters = [
            self._make_cluster("X", "same-slug", signal_count=5),
            self._make_cluster("X", "same-slug", signal_count=3),
            self._make_cluster("X", "same-slug", signal_count=2),
        ]
        result = _merge_similar_clusters(clusters)
        assert len(result) == 1
        assert result[0].signal_count == 10


# ---------------------------------------------------------------------------
# _build_cluster_results
# ---------------------------------------------------------------------------


class TestBuildClusterResults:
    def test_basic_grouping_produces_one_result_per_large_group(self):
        grouped = {
            "group_a": [_make_signal(theme="AI") for _ in range(6)],
            "group_b": [_make_signal(theme="Fintech") for _ in range(7)],
        }
        results = _build_cluster_results(grouped, llm_client=None, min_cluster_size=5)
        # Excludes "Outros Sinais" — both groups are large enough
        outros = [r for r in results if r.slug == "outros-sinais"]
        assert len(outros) == 0
        assert len(results) == 2

    def test_small_groups_merged_into_outros_sinais(self):
        grouped = {
            "small_a": [_make_signal() for _ in range(2)],
            "small_b": [_make_signal() for _ in range(3)],
        }
        results = _build_cluster_results(grouped, llm_client=None, min_cluster_size=5)
        slugs = [r.slug for r in results]
        assert "outros-sinais" in slugs

    def test_outros_sinais_contains_all_small_signals(self):
        grouped = {
            "small_a": [_make_signal() for _ in range(2)],
            "small_b": [_make_signal() for _ in range(3)],
        }
        results = _build_cluster_results(grouped, llm_client=None, min_cluster_size=5)
        outros = next(r for r in results if r.slug == "outros-sinais")
        assert outros.signal_count == 5

    def test_sorted_by_signal_count_descending(self):
        grouped = {
            "group_a": [_make_signal(theme="AI") for _ in range(5)],
            "group_b": [_make_signal(theme="Fintech") for _ in range(10)],
        }
        results = _build_cluster_results(grouped, llm_client=None, min_cluster_size=5)
        counts = [r.signal_count for r in results]
        assert counts == sorted(counts, reverse=True)

    def test_empty_grouped_dict_returns_empty_list(self):
        results = _build_cluster_results({}, llm_client=None, min_cluster_size=5)
        assert results == []

    def test_dominant_theme_set_on_result(self):
        # Most signals in group have theme "Fintech"
        signals = [_make_signal(theme="Fintech") for _ in range(4)]
        signals.append(_make_signal(theme="AI"))
        grouped = {"group": signals}
        results = _build_cluster_results(grouped, llm_client=None, min_cluster_size=5)
        assert results[0].theme == "Fintech"

    def test_min_cluster_size_zero_no_outros(self):
        grouped = {"tiny": [_make_signal()]}
        results = _build_cluster_results(grouped, llm_client=None, min_cluster_size=0)
        slugs = [r.slug for r in results]
        assert "outros-sinais" not in slugs


# ---------------------------------------------------------------------------
# cluster_signals (main entry point)
# ---------------------------------------------------------------------------


class TestClusterSignals:
    def test_empty_input_returns_empty_list(self):
        result = cluster_signals([])
        assert result == []

    def test_single_signal_returns_one_cluster(self):
        signals = [_make_signal(theme="AI")]
        result = cluster_signals(signals, min_cluster_size=1)
        assert len(result) == 1
        assert result[0].signal_count == 1

    def test_single_signal_slug_is_valid(self):
        signals = [_make_signal(theme="AI")]
        result = cluster_signals(signals, min_cluster_size=1)
        slug = result[0].slug
        assert slug
        assert " " not in slug
        assert slug == slug.lower()

    def test_min_cluster_size_filters_small_clusters(self):
        # 3 signals on theme "AI", 2 on "Fintech" — min_cluster_size=5 should
        # push both into "Outros Sinais" (or one large group if sklearn merges them)
        signals = [_make_signal(theme="AI") for _ in range(3)]
        signals += [_make_signal(theme="Fintech") for _ in range(2)]
        result = cluster_signals(signals, min_cluster_size=5)
        # All signals below threshold → single catch-all or outros
        total_signals = sum(r.signal_count for r in result)
        assert total_signals == 5

    def test_basic_grouping_by_theme_fallback(self):
        # Uses _cluster_by_theme when sklearn is unavailable or < 3 signals
        # We test with enough signals via theme fallback directly
        signals = [_make_signal(theme="AI") for _ in range(6)]
        signals += [_make_signal(theme="Fintech") for _ in range(6)]
        result = cluster_signals(signals, min_cluster_size=3)
        # Should produce at least 1 cluster covering all 12 signals
        total_signals = sum(r.signal_count for r in result)
        assert total_signals == 12

    def test_outros_sinais_catch_all_present_when_all_small(self):
        signals = [_make_signal(theme="AI") for _ in range(2)]
        result = cluster_signals(signals, min_cluster_size=5)
        slugs = [r.slug for r in result]
        assert "outros-sinais" in slugs

    def test_result_sorted_by_signal_count_descending(self):
        signals = [_make_signal(theme="AI") for _ in range(8)]
        signals += [_make_signal(theme="Fintech") for _ in range(5)]
        result = cluster_signals(signals, min_cluster_size=3)
        counts = [r.signal_count for r in result]
        assert counts == sorted(counts, reverse=True)

    def test_all_signals_accounted_for(self):
        signals = [_make_signal(theme="AI") for _ in range(10)]
        result = cluster_signals(signals, min_cluster_size=3)
        total = sum(r.signal_count for r in result)
        assert total == 10

    def test_returns_list_of_signal_cluster_result(self):
        signals = [_make_signal() for _ in range(5)]
        result = cluster_signals(signals, min_cluster_size=1)
        for r in result:
            assert isinstance(r, SignalClusterResult)
