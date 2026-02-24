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
        params={"max_pages": 100, "per_page": 50, "confidence": 0.7},
    ),

    # Y Combinator — LATAM portfolio
    DataSourceConfig(
        name="yc_portfolio",
        source_type="api",
        url="https://www.ycombinator.com/companies",
        params={"confidence": 0.85},
    ),

    # GitHub — LATAM tech organizations (paginated, 33 cities across 14 countries)
    # Each source triggers one GitHub Search query; collect_from_github()
    # paginates automatically up to the 1,000-result API ceiling.
    # Major hubs (SP, CDMX, BA): repos:>5 filter; smaller cities: repos:>3
    # Brasil
    DataSourceConfig(name="github_sao_paulo", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"São Paulo" type:org repos:>5', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_rio", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Rio de Janeiro" type:org repos:>5', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_belo_horizonte", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Belo Horizonte" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_curitiba", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Curitiba" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_porto_alegre", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Porto Alegre" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_florianopolis", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Florianópolis" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_campinas", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Campinas" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_recife", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Recife" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_brasilia", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Brasília" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_salvador", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Salvador" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_fortaleza", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Fortaleza" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_manaus", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Manaus" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    # Mexico
    DataSourceConfig(name="github_mexico_city", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Mexico City" type:org repos:>5', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_guadalajara", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Guadalajara" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_monterrey", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Monterrey" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    # Argentina
    DataSourceConfig(name="github_buenos_aires", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Buenos Aires" type:org repos:>5', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_cordoba", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Córdoba" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_rosario", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Rosario" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    # Colombia
    DataSourceConfig(name="github_bogota", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Bogotá" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_medellin", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Medellín" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_cali", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Cali" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    # Chile, Peru, Uruguay, Ecuador, Costa Rica, Panama, DR, Paraguay, Bolivia, PR
    DataSourceConfig(name="github_santiago", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Santiago" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_lima", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Lima" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_montevideo", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Montevideo" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_quito", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Quito" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_san_jose", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"San José" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_panama_city", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Panama City" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_santo_domingo", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Santo Domingo" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_asuncion", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"Asunción" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_la_paz", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"La Paz" type:org repos:>3', "sort": "repositories", "per_page": 100}),
    DataSourceConfig(name="github_san_juan", source_type="api", url="https://api.github.com/search/users",
        params={"q": 'location:"San Juan" type:org repos:>3', "sort": "repositories", "per_page": 100}),

    # StartupsLatam — WordPress REST API directory (510+ startups)
    DataSourceConfig(
        name="startups_latam",
        source_type="api",
        url="https://startupslatam.com/wp-json/wp/v2/startup",
        params={"confidence": 0.7},
    ),

    # CoreSignal — LinkedIn-sourced company database API
    DataSourceConfig(
        name="coresignal_latam",
        source_type="api",
        url="https://api.coresignal.com/cdapi/v2/company_base",
        api_key_env="CORESIGNAL_API_KEY",
        params={"max_collect": 2000, "confidence": 0.8},
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
            "locations": "Brazil,Mexico,Argentina,Colombia,Chile,Peru,Uruguay,Ecuador,Costa Rica,Panama",
            "categories": "fintech,artificial-intelligence,saas,marketplace,edtech,healthtech",
            "limit": 500,
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
