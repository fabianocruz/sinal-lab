"""Configuration for the FUNDING agent — data sources and parameters."""

from apps.agents.base.config import AgentCategory, AgentConfig, DataSourceConfig

# LATAM VC firms and investment news sources (RSS/Atom feeds)
FUNDING_SOURCES: list[DataSourceConfig] = [
    # --- Brazilian VCs ---
    DataSourceConfig(
        name="kaszek",
        source_type="rss",
        url="https://kaszek.com/feed/",
    ),
    DataSourceConfig(
        name="monashees",
        source_type="rss",
        url="https://www.monashees.com.br/feed/",
    ),
    DataSourceConfig(
        name="valor_capital",
        source_type="rss",
        url="https://valorcapitalgroup.com/feed/",
    ),
    DataSourceConfig(
        name="canary",
        source_type="rss",
        url="https://canary.vc/blog/rss.xml",
    ),
    DataSourceConfig(
        name="maya_capital",
        source_type="rss",
        url="https://maya.capital/blog/rss",
    ),
    DataSourceConfig(
        name="domo_invest",
        source_type="rss",
        url="https://domo.vc/feed/",
    ),
    DataSourceConfig(
        name="astella",
        source_type="rss",
        url="https://www.astellapartners.com/feed/",
    ),

    # --- LATAM VCs (regional) ---
    DataSourceConfig(
        name="tiger_global_latam",
        source_type="rss",
        url="https://www.tigerglobal.com/feed/",
    ),
    DataSourceConfig(
        name="softbank_latam",
        source_type="rss",
        url="https://www.softbank.com/en/news/feed",
    ),
    DataSourceConfig(
        name="qed_investors",
        source_type="rss",
        url="https://qedinvestors.com/feed/",
    ),

    # --- Investment News Sources ---
    DataSourceConfig(
        name="pipeline_valor",
        source_type="rss",
        url="https://pipelinevalor.globo.com/rss/",
    ),
    DataSourceConfig(
        name="neofeed",
        source_type="rss",
        url="https://neofeed.com.br/feed/",
    ),
    DataSourceConfig(
        name="startupi",
        source_type="rss",
        url="https://startupi.com.br/feed/",
    ),
    DataSourceConfig(
        name="distrito_funding",
        source_type="rss",
        url="https://distrito.me/blog/category/funding/feed/",
    ),
    DataSourceConfig(
        name="contxto",
        source_type="rss",
        url="https://contxto.com/feed/",
    ),

    # --- Dealroom API (freemium) ---
    # Note: Dealroom API requires API key, configured via environment variable
    DataSourceConfig(
        name="dealroom_api",
        source_type="api",
        url="https://api.dealroom.co/v1/funding_rounds",
        api_key_env="DEALROOM_API_KEY",
        rate_limit_per_minute=10,
        enabled=False,  # Enable when API key is available
        params={
            "countries": "BR,MX,AR,CO,CL,PE,UY",  # LATAM countries
            "days_ago": 7,  # Last 7 days
        },
    ),
]

FUNDING_CONFIG = AgentConfig(
    agent_name="funding",
    agent_category=AgentCategory.DATA,
    version="0.1.0",
    description="Investment Tracking — monitors VC announcements and funding rounds in LATAM startups",
    data_sources=FUNDING_SOURCES,
    schedule_cron="0 7 * * 1",  # Every Monday at 7am UTC (after SINTESE at 6am)
    output_content_type="DATA_REPORT",
    min_confidence_to_publish=0.4,  # Lower than SINTESE due to single-source funding announcements
    max_items_per_run=200,
)
