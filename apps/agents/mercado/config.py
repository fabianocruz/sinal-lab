"""Configuration for MERCADO agent.

Data sources for startup discovery and ecosystem mapping across LATAM.
"""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig

# GitHub Search API: Discover tech companies via org profiles
# Free tier: 30 req/min, 5000 req/hour
MERCADO_SOURCES: list[DataSourceConfig] = [
    # --- Primary source: companies table (populated by INDEX agent) ---
    DataSourceConfig(
        name="companies_db",
        source_type="database",
        url=None,
        params={"limit": 500},
    ),

    # GitHub Search — discover tech organizations by LATAM city
    # Uses /search/users endpoint with type:org filter
    DataSourceConfig(
        name="github_sao_paulo",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"São Paulo" type:org repos:>5', "sort": "repositories", "per_page": 30},
    ),
    DataSourceConfig(
        name="github_rio",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Rio de Janeiro" type:org repos:>5', "sort": "repositories", "per_page": 30},
    ),
    DataSourceConfig(
        name="github_mexico_city",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Mexico City" type:org repos:>5', "sort": "repositories", "per_page": 30},
    ),
    DataSourceConfig(
        name="github_buenos_aires",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Buenos Aires" type:org repos:>3', "sort": "repositories", "per_page": 30},
    ),
    DataSourceConfig(
        name="github_bogota",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Bogotá" type:org repos:>3', "sort": "repositories", "per_page": 30},
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

    # Google Trends — enriched tech trend signals for market context
    DataSourceConfig(
        name="gtrends_latam_tech",
        source_type="api",
        url=None,
        params={"method": "related_queries", "region": "BR", "keywords": "startup,fintech,AI,venture capital"},
    ),

    # LinkedIn RapidAPI — company discovery (experimental, disabled by default)
    DataSourceConfig(
        name="linkedin_latam_companies", source_type="api",
        url="https://linkedin-data-api.p.rapidapi.com/search-companies",
        api_key_env="RAPIDAPI_KEY", enabled=False,
        params={"query": "startup fintech AI Brazil LATAM", "limit": 10},
    ),

    # --- Crunchbase Basic API (free tier: 200 req/day) ---
    DataSourceConfig(
        name="crunchbase_companies_latam", source_type="api",
        url="https://api.crunchbase.com/api/v4/searches/organizations",
        api_key_env="CRUNCHBASE_API_KEY",
        params={
            "locations": "Brazil,Mexico,Argentina,Colombia,Chile",
            "categories": "fintech,artificial-intelligence,saas,marketplace",
            "limit": 30,
        },
    ),

    # --- BCB Authorized Financial Institutions (regulatory) ---
    DataSourceConfig(
        name="bcb_authorized",
        source_type="api",
        url="https://olinda.bcb.gov.br/olinda/servico/DASFN/versao/v1/odata/IfDataDes662",
        params={"segments": "b1,b2,b4"},
    ),

    # --- Gupy Jobs (tech stack enrichment) ---
    DataSourceConfig(
        name="gupy_jobs",
        source_type="api",
        url=None,  # URL built per-company
        params={"max_slugs": 20},
    ),
]

MERCADO_PERSONA = AgentPersona(
    display_name="Valentina Rojas",
    role_title="Especialista LATAM",
    nationality="Colombiana",
    bio_short="Analista de ecossistemas e mapeamento de startups",
    avatar_filename="valentina-rojas.jpg",
)

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
    persona=MERCADO_PERSONA,
)
