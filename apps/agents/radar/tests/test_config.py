"""Tests for RADAR agent configuration — source definitions."""

from apps.agents.radar.config import RADAR_CONFIG, RADAR_SOURCES


class TestRadarSources:
    """Verify RADAR data sources are well-formed."""

    def test_source_count(self):
        # 19 original + 8 fintech + 2 reddit (localllama, artificial) = 29
        assert len(RADAR_SOURCES) == 29

    def test_all_sources_have_names(self):
        names = [s.name for s in RADAR_SOURCES]
        assert len(names) == len(set(names)), "Duplicate source names found"

    def test_rss_sources_have_url(self):
        # Google News sources use source_type="rss" but url=None (url built at runtime)
        gnews = {"gnews_tech_trends_br", "gnews_tech_trends_latam"}
        rss_sources = [s for s in RADAR_SOURCES if s.source_type == "rss" and s.name not in gnews]
        for s in rss_sources:
            assert s.url, f"RSS source '{s.name}' has no URL"

    def test_fintech_rss_sources_present(self):
        names = {s.name for s in RADAR_SOURCES}
        expected = {"coindesk", "cointelegraph_defi", "decrypt", "theblock", "fintechnews_latam"}
        assert expected.issubset(names)

    def test_fintech_reddit_sources_present(self):
        names = {s.name for s in RADAR_SOURCES}
        expected = {"reddit_defi", "reddit_cryptocurrency", "reddit_ethfinance"}
        assert expected.issubset(names)

    def test_reddit_sources_have_subreddit_param(self):
        reddit_sources = [s for s in RADAR_SOURCES if s.name.startswith("reddit_")]
        for s in reddit_sources:
            assert "subreddit" in s.params, f"Reddit source '{s.name}' missing subreddit param"

    def test_config_agent_name(self):
        assert RADAR_CONFIG.agent_name == "radar"

    def test_config_has_all_sources(self):
        assert RADAR_CONFIG.data_sources is RADAR_SOURCES
