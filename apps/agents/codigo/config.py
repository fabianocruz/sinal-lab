"""Configuration for the CODIGO agent — data sources and parameters."""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig

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

    # --- Reddit (developer communities) ---
    DataSourceConfig(
        name="reddit_devops", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "devops", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_webdev", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "webdev", "sort": "hot", "limit": 25},
    ),

    # --- GitHub Trending (fintech/DeFi topics) ---
    DataSourceConfig(
        name="github_trending_fintech",
        source_type="api",
        url="https://api.github.com/search/repositories",
        params={
            "window": "weekly",
            "topics": "fintech,open-banking,pix,stablecoin,decentralized-finance",
        },
    ),

    # --- Fintech/DeFi Dev RSS ---
    DataSourceConfig(
        name="ethereum_blog",
        source_type="rss",
        url="https://blog.ethereum.org/feed.xml",
    ),
    DataSourceConfig(
        name="a16z_crypto",
        source_type="rss",
        url="https://a16zcrypto.com/feed/",
    ),

    # --- Reddit (fintech/DeFi dev communities) ---
    DataSourceConfig(
        name="reddit_defi_dev", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "ethdev", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_solana_dev", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "solanadev", "sort": "hot", "limit": 25},
    ),

    # --- ProductHunt GraphQL (dev token, free) ---
    DataSourceConfig(
        name="producthunt_tools", source_type="api",
        url="https://api.producthunt.com/v2/api/graphql",
        api_key_env="PRODUCTHUNT_TOKEN",
        params={"limit": 20},
    ),
]

CODIGO_PERSONA = AgentPersona(
    display_name="Marina Costa",
    role_title="Pesquisadora de Tecnologia",
    nationality="Brasileira",
    bio_short="Engenheira focada em ecossistema dev e infraestrutura",
    avatar_filename="marina-costa.jpg",
)

CODIGO_CONFIG = AgentConfig(
    agent_name="codigo",
    agent_category=AgentCategory.CONTENT,
    version="0.1.0",
    description="Developer Ecosystem Signals — tracks GitHub, npm, PyPI, and Stack Overflow trends",
    data_sources=CODIGO_SOURCES,
    schedule_cron="0 4 * * 1",  # Every Monday at 4am UTC (before RADAR and SINTESE)
    output_content_type="ANALYSIS",
    min_confidence_to_publish=0.3,
    max_items_per_run=500,
    persona=CODIGO_PERSONA,
)
