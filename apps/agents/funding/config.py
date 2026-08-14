"""Configuration for the FUNDING agent — data sources and parameters.

Source types:
    - ``rss``: RSS/Atom feed parsed with feedparser.
    - ``html``: blog index page scraped with
      ``sources.web_scraper.scrape_article_listing`` (fallback for VC
      blogs that dropped their feeds).
    - ``api``: dedicated client module per source.
"""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig


def _html_blog_params() -> dict:
    """Default scraping params for HTML blog indexes.

    Returns a fresh dict per source so configs never share mutable state.
    Keeps the crawl small: one index request + up to 8 article requests
    per source, per weekly run.
    """
    return {"max_items": 8, "fetch_content": True}


# LATAM VC firms and investment news sources (RSS/Atom feeds)
FUNDING_SOURCES: list[DataSourceConfig] = [
    # --- Brazilian VCs ---
    DataSourceConfig(name="kaszek", source_type="rss", url="https://kaszek.com/feed/"),
    # The four sources below serve rendered HTML where a feed used to be.
    # URLs verified 2026-08-13: valor_capital and maya_capital expose a
    # server-rendered post list; canary and monashees are JS-only shells
    # today (0 posts extracted) but are kept enabled so they resume
    # automatically if the sites start rendering their content again.
    DataSourceConfig(name="monashees", source_type="html", url="https://www.monashees.com/", params=_html_blog_params()),
    DataSourceConfig(name="valor_capital", source_type="html", url="https://valorcapitalgroup.com/writing-listing/", params=_html_blog_params()),
    DataSourceConfig(name="canary", source_type="html", url="https://www.canary.com.br/", params=_html_blog_params()),
    DataSourceConfig(name="maya_capital", source_type="html", url="https://maya.capital/blog", params=_html_blog_params()),
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

    # --- Google News (LATAM funding — multiple queries for coverage) ---
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
    DataSourceConfig(
        name="gnews_funding_latam_es",
        source_type="rss",
        url=None,
        params={"query": "startup ronda inversion America Latina Serie", "language": "es"},
    ),
    DataSourceConfig(
        name="gnews_series_a_br",
        source_type="rss",
        url=None,
        params={"query": "Serie A startup Brasil captou levantou", "language": "pt-BR", "country": "BR"},
    ),
    DataSourceConfig(
        name="gnews_seed_br",
        source_type="rss",
        url=None,
        params={"query": "seed round pre-seed startup Brasil fintech", "language": "pt-BR", "country": "BR"},
    ),

    # --- Additional LATAM funding news ---
    DataSourceConfig(name="the_block_latam", source_type="rss", url="https://www.theblock.co/rss/all"),
    DataSourceConfig(name="sifted", source_type="rss", url="https://sifted.eu/feed"),
    DataSourceConfig(name="rest_of_world", source_type="rss", url="https://restofworld.org/feed/"),

    # --- Dealroom API (freemium) ---
    DataSourceConfig(
        name="dealroom_api", source_type="api",
        url="https://api.dealroom.co/v1/funding_rounds",
        api_key_env="DEALROOM_API_KEY", rate_limit_per_minute=10,
        enabled=False,  # Enable when API key is available
        params={"countries": "BR,MX,AR,CO,CL,PE,UY", "days_ago": 7},
    ),

    # --- Grok Live Search (xAI) — live web search for LATAM rounds ---
    # Reaches deals that never appear in the configured feeds. Skips
    # itself with a warning when XAI_API_KEY is not set.
    DataSourceConfig(
        name="grok_live_search", source_type="api",
        url="https://api.x.ai/v1/responses",
        api_key_env="XAI_API_KEY", rate_limit_per_minute=5,
        params={"model": "grok-4.3", "days_back": 7},
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
