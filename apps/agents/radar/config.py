"""Configuration for the RADAR agent — data sources and parameters."""

from apps.agents.base.config import AgentCategory, AgentConfig, DataSourceConfig

RADAR_SOURCES: list[DataSourceConfig] = [
    # --- Hacker News ---
    DataSourceConfig(
        name="hn_best",
        source_type="rss",
        url="https://hnrss.org/best",
        params={"points": 100},
    ),
    DataSourceConfig(
        name="hn_show",
        source_type="rss",
        url="https://hnrss.org/show",
    ),
    DataSourceConfig(
        name="hn_ask",
        source_type="rss",
        url="https://hnrss.org/ask",
    ),

    # --- GitHub Trending ---
    DataSourceConfig(
        name="github_trending_daily",
        source_type="api",
        url="https://api.github.com/search/repositories",
        params={"sort": "stars", "order": "desc", "window": "daily"},
    ),
    DataSourceConfig(
        name="github_trending_weekly",
        source_type="api",
        url="https://api.github.com/search/repositories",
        params={"sort": "stars", "order": "desc", "window": "weekly"},
    ),

    # --- arXiv (AI / ML / NLP) ---
    DataSourceConfig(
        name="arxiv_cs_ai",
        source_type="rss",
        url="https://rss.arxiv.org/rss/cs.AI",
    ),
    DataSourceConfig(
        name="arxiv_cs_lg",
        source_type="rss",
        url="https://rss.arxiv.org/rss/cs.LG",
    ),
    DataSourceConfig(
        name="arxiv_cs_cl",
        source_type="rss",
        url="https://rss.arxiv.org/rss/cs.CL",
    ),

    # --- Google Trends (PT-BR) ---
    DataSourceConfig(
        name="google_trends_br",
        source_type="api",
        url="https://trends.google.com/trends/trendingsearches/daily/rss",
        params={"geo": "BR"},
    ),

    # --- Lobsters (tech community) ---
    DataSourceConfig(
        name="lobsters",
        source_type="rss",
        url="https://lobste.rs/hottest.rss",
    ),

    # --- Product Hunt ---
    DataSourceConfig(
        name="producthunt",
        source_type="rss",
        url="https://www.producthunt.com/feed",
    ),
]

RADAR_CONFIG = AgentConfig(
    agent_name="radar",
    agent_category=AgentCategory.CONTENT,
    version="0.1.0",
    description="Trend Intelligence — detects emerging signals from HN, GitHub, arXiv, and Google Trends",
    data_sources=RADAR_SOURCES,
    schedule_cron="0 5 * * 1",  # Every Monday at 5am UTC (before SINTESE)
    output_content_type="ANALYSIS",
    min_confidence_to_publish=0.3,
    max_items_per_run=1000,
)
