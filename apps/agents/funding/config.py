"""Configuration for the FUNDING agent — data sources and parameters."""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig

# LATAM VC firms and investment news sources (RSS/Atom feeds)
FUNDING_SOURCES: list[DataSourceConfig] = [
    # --- Brazilian VCs ---
    DataSourceConfig(name="kaszek", source_type="rss", url="https://kaszek.com/feed/"),
    DataSourceConfig(name="monashees", source_type="rss", url="https://www.monashees.com.br/feed/", enabled=False),  # SSL handshake timeout
    DataSourceConfig(name="valor_capital", source_type="rss", url="https://valorcapitalgroup.com/feed/", enabled=False),  # Returns HTML, not RSS
    DataSourceConfig(name="canary", source_type="rss", url="https://canary.vc/blog/rss.xml", enabled=False),  # Returns HTML, not RSS
    DataSourceConfig(name="maya_capital", source_type="rss", url="https://maya.capital/blog/rss", enabled=False),  # Returns HTML, not RSS
    DataSourceConfig(name="domo_invest", source_type="rss", url="https://domo.vc/feed/", enabled=False),  # 0 entries (empty feed)
    DataSourceConfig(name="astella", source_type="rss", url="https://www.astellapartners.com/feed/", enabled=False),  # DNS resolution failed

    # --- LATAM VCs (regional) ---
    DataSourceConfig(name="tiger_global_latam", source_type="rss", url="https://www.tigerglobal.com/feed/", enabled=False),  # 404
    DataSourceConfig(name="softbank_latam", source_type="rss", url="https://www.softbank.com/en/news/feed", enabled=False),  # Timeout
    DataSourceConfig(name="qed_investors", source_type="rss", url="https://qedinvestors.com/feed/", enabled=False),  # 404

    # --- Premium LATAM Business/Tech ---
    DataSourceConfig(name="bloomberg_linea", source_type="rss", url="https://www.bloomberglinea.com.br/arc/outboundfeeds/rss/?outputType=xml"),
    DataSourceConfig(name="lavca", source_type="rss", url="https://www.lavca.org/feed/"),

    # --- Investment News Sources ---
    DataSourceConfig(name="pipeline_valor", source_type="rss", url="https://pipelinevalor.globo.com/rss/", enabled=False),  # 404
    DataSourceConfig(name="neofeed", source_type="rss", url="https://neofeed.com.br/feed/"),
    DataSourceConfig(name="startupi", source_type="rss", url="https://startupi.com.br/feed/", enabled=False),  # Low editorial quality
    DataSourceConfig(name="distrito_funding", source_type="rss", url="https://distrito.me/blog/category/funding/feed/", enabled=False),  # 404
    DataSourceConfig(name="contxto", source_type="rss", url="https://contxto.com/feed/", enabled=False),  # SSL protocol error

    # --- VC Firms (portfolio announcements) ---
    DataSourceConfig(name="ycombinator", source_type="rss", url="https://www.ycombinator.com/blog/rss/"),
    DataSourceConfig(name="a16z", source_type="rss", url="https://a16z.substack.com/feed"),
    DataSourceConfig(name="sequoia", source_type="rss", url="https://www.sequoiacap.com/feed/"),
    DataSourceConfig(name="lightspeed", source_type="rss", url="https://lsvp.com/feed/"),
    DataSourceConfig(name="greylock", source_type="rss", url="https://greylock.com/feed/"),

    # --- Funding News (cross-validated with SINTESE sources) ---
    DataSourceConfig(name="crunchbase_news", source_type="rss", url="https://news.crunchbase.com/feed/"),
    DataSourceConfig(name="techcrunch_latam", source_type="rss", url="https://techcrunch.com/tag/latin-america/feed/"),
    DataSourceConfig(name="latamlist", source_type="rss", url="https://latamlist.com/feed/"),
    DataSourceConfig(name="abstartups", source_type="rss", url="https://abstartups.com.br/feed/"),
    DataSourceConfig(name="blocknews", source_type="rss", url="https://blocknews.com.br/feed/", enabled=False),  # 403 Forbidden (bot blocking)

    # --- Google News (LATAM funding) ---
    DataSourceConfig(
        name="gnews_funding_br",
        source_type="rss",
        url=None,
        params={"query": "startup investimento rodada aporte Brasil", "language": "pt-BR", "country": "BR"},
    ),
    DataSourceConfig(
        name="gnews_funding_latam",
        source_type="rss",
        url=None,
        params={"query": "startup funding round Latin America Series", "language": "en", "country": "BR"},
    ),

    # --- Dealroom API (freemium) ---
    DataSourceConfig(
        name="dealroom_api", source_type="api",
        url="https://api.dealroom.co/v1/funding_rounds",
        api_key_env="DEALROOM_API_KEY", rate_limit_per_minute=10,
        enabled=False,  # Enable when API key is available
        params={"countries": "BR,MX,AR,CO,CL,PE,UY", "days_ago": 7},
    ),

    # --- Crunchbase Basic API (free tier: 200 req/day) ---
    DataSourceConfig(
        name="crunchbase_funding_latam", source_type="api",
        url="https://api.crunchbase.com/api/v4/searches/funding_rounds",
        api_key_env="CRUNCHBASE_API_KEY",
        params={"locations": "Brazil,Mexico,Argentina,Colombia,Chile", "limit": 50},
    ),

    # --- SEC EDGAR Form D (regulatory cross-validation) ---
    DataSourceConfig(
        name="sec_form_d",
        source_type="api",
        url="https://efts.sec.gov/LATEST/search-index",
        params={"forms": "D", "date_range_days": 30},
    ),
]

FUNDING_PERSONA = AgentPersona(
    display_name="Rafael Oliveira",
    role_title="Analista de Investimentos",
    nationality="Brasileiro",
    bio_short="Especialista em capital de risco e rodadas LATAM",
    avatar_filename="rafael-oliveira.jpg",
)

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
    persona=FUNDING_PERSONA,
)
