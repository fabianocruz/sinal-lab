"""Tests for CODIGO agent configuration — source definitions."""

from apps.agents.codigo.config import CODIGO_CONFIG, CODIGO_SOURCES


class TestCodigoSources:
    """Verify CODIGO data sources are well-formed."""

    def test_source_count(self):
        # 11 original + 5 fintech + 3 (infoq, experienceddevs, selfhosted) = 19
        assert len(CODIGO_SOURCES) == 19

    def test_all_sources_have_names(self):
        names = [s.name for s in CODIGO_SOURCES]
        assert len(names) == len(set(names)), "Duplicate source names found"

    def test_rss_sources_have_url(self):
        rss_sources = [s for s in CODIGO_SOURCES if s.source_type == "rss"]
        for s in rss_sources:
            assert s.url, f"RSS source '{s.name}' has no URL"

    def test_fintech_github_source_present(self):
        names = {s.name for s in CODIGO_SOURCES}
        assert "github_trending_fintech" in names

    def test_fintech_github_has_topics(self):
        source = next(s for s in CODIGO_SOURCES if s.name == "github_trending_fintech")
        topics = source.params.get("topics", "")
        assert "fintech" in topics
        assert "stablecoin" in topics

    def test_fintech_rss_sources_present(self):
        names = {s.name for s in CODIGO_SOURCES}
        expected = {"ethereum_blog", "a16z_crypto"}
        assert expected.issubset(names)

    def test_fintech_reddit_sources_present(self):
        names = {s.name for s in CODIGO_SOURCES}
        expected = {"reddit_defi_dev", "reddit_solana_dev"}
        assert expected.issubset(names)

    def test_reddit_sources_have_subreddit_param(self):
        reddit_sources = [s for s in CODIGO_SOURCES if s.name.startswith("reddit_")]
        for s in reddit_sources:
            assert "subreddit" in s.params, f"Reddit source '{s.name}' missing subreddit param"

    def test_config_agent_name(self):
        assert CODIGO_CONFIG.agent_name == "codigo"

    def test_config_has_all_sources(self):
        assert CODIGO_CONFIG.data_sources is CODIGO_SOURCES
