"""Configuration for MERCADO agent.

Data sources for startup discovery and ecosystem mapping across LATAM.
"""

from apps.agents.base.config import AgentCategory, AgentConfig, DataSourceConfig

# GitHub Search API: Discover tech companies via org profiles
# Free tier: 30 req/min, 5000 req/hour
MERCADO_SOURCES: list[DataSourceConfig] = [
    # GitHub Search — São Paulo, Brasil
    DataSourceConfig(
        name="github_sao_paulo",
        source_type="api",
        url="https://api.github.com/search/repositories",
        enabled=True,
        params={
            "q": "location:São+Paulo stars:>100",
            "sort": "stars",
            "per_page": 100,
        },
    ),
    # GitHub Search — Rio de Janeiro, Brasil
    DataSourceConfig(
        name="github_rio",
        source_type="api",
        url="https://api.github.com/search/repositories",
        enabled=True,
        params={
            "q": "location:Rio+de+Janeiro stars:>100",
            "sort": "stars",
            "per_page": 100,
        },
    ),
    # GitHub Search — Mexico City, Mexico
    DataSourceConfig(
        name="github_mexico_city",
        source_type="api",
        url="https://api.github.com/search/repositories",
        enabled=True,
        params={
            "q": "location:Mexico+City stars:>100",
            "sort": "stars",
            "per_page": 100,
        },
    ),
    # GitHub Search — Buenos Aires, Argentina
    DataSourceConfig(
        name="github_buenos_aires",
        source_type="api",
        url="https://api.github.com/search/repositories",
        enabled=True,
        params={
            "q": "location:Buenos+Aires stars:>50",
            "sort": "stars",
            "per_page": 100,
        },
    ),
    # GitHub Search — Bogotá, Colombia
    DataSourceConfig(
        name="github_bogota",
        source_type="api",
        url="https://api.github.com/search/repositories",
        enabled=True,
        params={
            "q": "location:Bogotá stars:>50",
            "sort": "stars",
            "per_page": 100,
        },
    ),
    # Dealroom API (freemium tier: 100 req/day)
    # Enabled when API key is available
    DataSourceConfig(
        name="dealroom_api",
        source_type="api",
        url="https://api.dealroom.co/v1/companies",
        api_key_env="DEALROOM_API_KEY",
        enabled=False,  # Enable when API key configured
        params={
            "filter": "hq_location:latam",
            "limit": 100,
        },
        rate_limit_per_minute=2,  # Conservative for free tier
    ),
]

MERCADO_CONFIG = AgentConfig(
    agent_name="mercado",
    agent_category=AgentCategory.DATA,
    version="0.1.0",
    description="LATAM startup mapping and ecosystem intelligence",
    data_sources=MERCADO_SOURCES,
    schedule_cron="0 7 * * 3",  # Every Wednesday 7am UTC
    output_content_type="DATA_REPORT",
    min_confidence_to_publish=0.4,
    max_items_per_run=500,
)
