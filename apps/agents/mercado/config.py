"""Configuration for MERCADO agent.

Data sources for startup discovery and ecosystem mapping across LATAM.
"""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig

# GitHub Search API: Discover tech companies via org profiles
# Free tier: 30 req/min, 5000 req/hour
_GITHUB_URL = "https://api.github.com/search/users"

# Cities grouped by tier:
# Tier 1 (major hubs, repos:>5): SP, CDMX, Buenos Aires, Bogotá, Santiago
# Tier 2 (secondary hubs, repos:>3): RJ, Lima, Montevideo, Medellín, Guadalajara, Monterrey
# Tier 3 (emerging, repos:>3): BH, Curitiba, Floripa, POA, Recife, Campinas, Córdoba, Quito, San José, Panama City
_GITHUB_CITIES: list[tuple[str, str, int]] = [
    # Brasil — Tier 1
    ("São Paulo", "github_sao_paulo", 5),
    # Brasil — Tier 2
    ("Rio de Janeiro", "github_rio", 3),
    ("Belo Horizonte", "github_belo_horizonte", 3),
    ("Curitiba", "github_curitiba", 3),
    ("Porto Alegre", "github_porto_alegre", 3),
    ("Florianópolis", "github_florianopolis", 3),
    ("Campinas", "github_campinas", 3),
    ("Recife", "github_recife", 3),
    # Mexico
    ("Mexico City", "github_mexico_city", 5),
    ("Guadalajara", "github_guadalajara", 3),
    ("Monterrey", "github_monterrey", 3),
    # Argentina
    ("Buenos Aires", "github_buenos_aires", 5),
    ("Córdoba", "github_cordoba", 3),
    # Colombia
    ("Bogotá", "github_bogota", 5),
    ("Medellín", "github_medellin", 3),
    # Chile
    ("Santiago", "github_santiago", 5),
    # Peru
    ("Lima", "github_lima", 3),
    # Uruguay
    ("Montevideo", "github_montevideo", 3),
    # Ecuador
    ("Quito", "github_quito", 3),
    # Costa Rica
    ("San José", "github_san_jose", 3),
    # Panama
    ("Panama City", "github_panama_city", 3),
]

MERCADO_SOURCES: list[DataSourceConfig] = [
    # Database — pre-collected companies from INDEX agent
    DataSourceConfig(
        name="companies_db",
        source_type="database",
        url=None,
        params={"limit": 500},
    ),

    # Coresignal — company discovery via LinkedIn data
    DataSourceConfig(
        name="coresignal_latam",
        source_type="api",
        url="https://api.coresignal.com/cdapi/v1/linkedin/company/search/filter",
        api_key_env="CORESIGNAL_API_KEY",
        params={
            "country": "Brazil,Mexico,Argentina,Colombia,Chile",
            "industry": "Technology,Financial Services,Information Technology",
            "employees_count_min": 5,
            "limit": 100,
        },
        rate_limit_per_minute=5,
    ),

    # GitHub Search — discover tech organizations by LATAM city
    # Uses /search/users endpoint with type:org filter
    *[
        DataSourceConfig(
            name=source_name,
            source_type="api",
            url=_GITHUB_URL,
            params={
                "q": f'location:"{city}" type:org repos:>{min_repos}',
                "sort": "repositories",
                "per_page": 100,
            },
        )
        for city, source_name, min_repos in _GITHUB_CITIES
    ],

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
