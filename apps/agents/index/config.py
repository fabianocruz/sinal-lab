"""Configuration for INDEX agent.

Data sources for comprehensive LATAM startup registry via bulk ingestion.
"""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig

INDEX_SOURCES: list[DataSourceConfig] = [
    # Receita Federal — Brazilian CNPJ registry (bulk CSV file)
    DataSourceConfig(
        name="receita_federal",
        source_type="file",
        url=None,  # File path provided at runtime via --rf-file
        params={"confidence": 0.9},
        enabled=False,  # Enabled only when CSV file is provided
    ),

    # ABStartups — StartupBase API
    DataSourceConfig(
        name="abstartups",
        source_type="api",
        url="https://startupbase.com.br/api/v1/startups",
        params={"max_pages": 10, "per_page": 50, "confidence": 0.7},
    ),

    # Y Combinator — LATAM portfolio
    DataSourceConfig(
        name="yc_portfolio",
        source_type="api",
        url="https://www.ycombinator.com/companies",
        params={"confidence": 0.85},
    ),

    # GitHub — LATAM tech organizations (reuses MERCADO sources)
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
    DataSourceConfig(
        name="github_santiago",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Santiago" type:org repos:>3', "sort": "repositories", "per_page": 30},
    ),
    DataSourceConfig(
        name="github_lima",
        source_type="api",
        url="https://api.github.com/search/users",
        params={"q": 'location:"Lima" type:org repos:>3', "sort": "repositories", "per_page": 30},
    ),

    # Crunchbase Open Data CSV (optional, bulk file)
    DataSourceConfig(
        name="crunchbase_open",
        source_type="file",
        url=None,
        params={"confidence": 0.8},
        enabled=False,  # Enabled only when CSV file is provided
    ),

    # Crunchbase Basic API (existing, reused from MERCADO)
    DataSourceConfig(
        name="crunchbase_companies_latam",
        source_type="api",
        url="https://api.crunchbase.com/api/v4/searches/organizations",
        api_key_env="CRUNCHBASE_API_KEY",
        params={
            "locations": "Brazil,Mexico,Argentina,Colombia,Chile",
            "categories": "fintech,artificial-intelligence,saas,marketplace",
            "limit": 30,
            "confidence": 0.8,
        },
    ),
]

INDEX_PERSONA = AgentPersona(
    display_name="Ana Torres",
    role_title="Pesquisadora de Dados",
    nationality="Brasileira",
    bio_short="Mantém o índice completo de startups LATAM com dados de múltiplas fontes",
    avatar_filename="ana-torres.jpg",
)

INDEX_CONFIG = AgentConfig(
    agent_name="index",
    agent_category=AgentCategory.DATA,
    version="0.1.0",
    description="LATAM Startup Index — comprehensive registry from multiple bulk sources",
    data_sources=INDEX_SOURCES,
    schedule_cron="0 6 * * 6",  # Every Saturday 6am UTC
    output_content_type="DATA_REPORT",
    min_confidence_to_publish=0.3,
    max_items_per_run=10000,
    persona=INDEX_PERSONA,
)
