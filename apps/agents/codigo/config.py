"""Configuration for the CODIGO agent — data sources and parameters."""

from apps.agents.base.config import AgentConfig, DataSourceConfig

CODIGO_SOURCES: list[DataSourceConfig] = [
    # --- GitHub Trending ---
    DataSourceConfig(
        name="github_trending_daily",
        source_type="api",
        url="https://api.github.com/search/repositories",
        params={"window": "daily"},
    ),
    DataSourceConfig(
        name="github_trending_weekly",
        source_type="api",
        url="https://api.github.com/search/repositories",
        params={"window": "weekly"},
    ),

    # --- npm Registry ---
    DataSourceConfig(
        name="npm_popular",
        source_type="api",
        url="https://registry.npmjs.org/-/v1/search",
        params={"quality": 0.8, "popularity": 0.9},
    ),

    # --- PyPI ---
    DataSourceConfig(
        name="pypi_recent",
        source_type="api",
        url="https://pypi.org/rss/updates.xml",
    ),
    DataSourceConfig(
        name="pypi_new",
        source_type="rss",
        url="https://pypi.org/rss/packages.xml",
    ),

    # --- Stack Overflow ---
    DataSourceConfig(
        name="stackoverflow_trending",
        source_type="api",
        url="https://api.stackexchange.com/2.3/tags",
        params={"site": "stackoverflow", "sort": "popular", "pagesize": 50},
    ),

    # --- Dev Community RSS ---
    DataSourceConfig(
        name="devto",
        source_type="rss",
        url="https://dev.to/feed",
    ),
    DataSourceConfig(
        name="changelog",
        source_type="rss",
        url="https://changelog.com/feed",
    ),
]

CODIGO_CONFIG = AgentConfig(
    agent_name="codigo",
    version="0.1.0",
    description="Developer Ecosystem Signals — tracks GitHub, npm, PyPI, and Stack Overflow trends",
    data_sources=CODIGO_SOURCES,
    schedule_cron="0 4 * * 1",  # Every Monday at 4am UTC (before RADAR and SINTESE)
    output_content_type="ANALYSIS",
    min_confidence_to_publish=0.3,
    max_items_per_run=500,
)
