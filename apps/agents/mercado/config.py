"""Configuration for MERCADO agent.

Data sources for startup discovery and ecosystem mapping across LATAM.
"""

from apps.agents.base.config import AgentCategory, AgentConfig, DataSourceConfig

# GitHub Search API: Discover tech companies via org profiles
# Free tier: 30 req/min, 5000 req/hour
MERCADO_SOURCES: list[DataSourceConfig] = [
    # GitHub Search — discover tech organizations by LATAM city
    # Uses /search/users endpoint with type:org filter
    DataSourceConfig(
        name="github_sao_paulo",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"São Paulo" type:org repos:>5', "sort": "repositories", "per_page": 100},
    ),
    DataSourceConfig(
        name="github_rio",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Rio de Janeiro" type:org repos:>5', "sort": "repositories", "per_page": 100},
    ),
    DataSourceConfig(
        name="github_mexico_city",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Mexico City" type:org repos:>5', "sort": "repositories", "per_page": 100},
    ),
    DataSourceConfig(
        name="github_buenos_aires",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Buenos Aires" type:org repos:>3', "sort": "repositories", "per_page": 100},
    ),
    DataSourceConfig(
        name="github_bogota",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Bogotá" type:org repos:>3', "sort": "repositories", "per_page": 100},
    ),

    # Dealroom API (freemium tier: 100 req/day)
    DataSourceConfig(
        name="dealroom_api", source_type="api",
        url="https://api.dealroom.co/v1/companies",
        api_key_env="DEALROOM_API_KEY",
        enabled=False,  # Enable when API key configured
        params={"filter": "hq_location:latam", "limit": 100},
        rate_limit_per_minute=2,
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
