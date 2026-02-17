"""Configuration for the SINTESE agent — data sources, parameters, and feed list."""

from apps.agents.base.config import AgentCategory, AgentConfig, DataSourceConfig

# LATAM tech RSS/Atom feeds organized by category.
# Each feed is a DataSourceConfig for consistent handling.

LATAM_TECH_FEEDS: list[DataSourceConfig] = [
    # --- Brazilian Tech Media ---
    DataSourceConfig(name="startse", source_type="rss", url="https://www.startse.com/feed/"),
    DataSourceConfig(name="tecmundo", source_type="rss", url="https://www.tecmundo.com.br/rss"),
    DataSourceConfig(name="canaltech", source_type="rss", url="https://canaltech.com.br/rss/"),
    DataSourceConfig(name="olhardigital", source_type="rss", url="https://olhardigital.com.br/feed/"),
    DataSourceConfig(name="tecnoblog", source_type="rss", url="https://tecnoblog.net/feed/"),
    DataSourceConfig(name="convergenciadigital", source_type="rss", url="https://www.convergenciadigital.com.br/rss.php"),
    DataSourceConfig(name="baguete", source_type="rss", url="https://www.baguete.com.br/rss"),
    DataSourceConfig(name="mundoconectado", source_type="rss", url="https://mundoconectado.com.br/feed"),
    DataSourceConfig(name="meiobit", source_type="rss", url="https://meiobit.com/feed/"),
    DataSourceConfig(name="gabordi", source_type="rss", url="https://gabordi.com/feed/"),

    # --- Startup & VC ---
    DataSourceConfig(name="distrito", source_type="rss", url="https://distrito.me/blog/feed/"),
    DataSourceConfig(name="abstartups", source_type="rss", url="https://abstartups.com.br/feed/"),
    DataSourceConfig(name="startupi", source_type="rss", url="https://startupi.com.br/feed/"),
    DataSourceConfig(name="pipeline_valor", source_type="rss", url="https://pipelinevalor.globo.com/rss/"),
    DataSourceConfig(name="neofeed", source_type="rss", url="https://neofeed.com.br/feed/"),
    DataSourceConfig(name="blocknews", source_type="rss", url="https://blocknews.com.br/feed/"),

    # --- LATAM (non-Brazil) ---
    DataSourceConfig(name="contxto", source_type="rss", url="https://contxto.com/feed/"),
    DataSourceConfig(name="techcrunch_latam", source_type="rss", url="https://techcrunch.com/tag/latin-america/feed/"),
    DataSourceConfig(name="restofworld", source_type="rss", url="https://restofworld.org/feed/"),
    DataSourceConfig(name="latamlist", source_type="rss", url="https://latamlist.com/feed/"),

    # --- Global Tech (English, filtered for LATAM relevance) ---
    DataSourceConfig(name="techcrunch", source_type="rss", url="https://techcrunch.com/feed/"),
    DataSourceConfig(name="theverge", source_type="rss", url="https://www.theverge.com/rss/index.xml"),
    DataSourceConfig(name="arstechnica", source_type="rss", url="https://feeds.arstechnica.com/arstechnica/index"),
    DataSourceConfig(name="hackernews_best", source_type="rss", url="https://hnrss.org/best"),
    DataSourceConfig(name="lobsters", source_type="rss", url="https://lobste.rs/rss"),

    # --- AI & ML ---
    DataSourceConfig(name="theaibeat", source_type="rss", url="https://venturebeat.com/category/ai/feed/"),
    DataSourceConfig(name="mit_tech_review", source_type="rss", url="https://www.technologyreview.com/feed/"),
    DataSourceConfig(name="deeplearning_ai", source_type="rss", url="https://www.deeplearning.ai/blog/feed/"),

    # --- Developer & Infrastructure ---
    DataSourceConfig(name="devto", source_type="rss", url="https://dev.to/feed"),
    DataSourceConfig(name="github_blog", source_type="rss", url="https://github.blog/feed/"),
    DataSourceConfig(name="netlify_blog", source_type="rss", url="https://www.netlify.com/blog/rss.xml"),
    DataSourceConfig(name="vercel_blog", source_type="rss", url="https://vercel.com/blog/rss.xml"),
    DataSourceConfig(name="cloudflare_blog", source_type="rss", url="https://blog.cloudflare.com/rss/"),

    # --- Fintech ---
    DataSourceConfig(name="fintechfutures", source_type="rss", url="https://www.fintechfutures.com/feed/"),
    DataSourceConfig(name="infomoney", source_type="rss", url="https://www.infomoney.com.br/feed/"),

    # --- Newsletters as RSS ---
    DataSourceConfig(name="tldrnewsletter", source_type="rss", url="https://tldr.tech/rss"),
    DataSourceConfig(name="bytebytego", source_type="rss", url="https://blog.bytebytego.com/feed"),
]

SINTESE_CONFIG = AgentConfig(
    agent_name="sintese",
    agent_category=AgentCategory.CONTENT,
    version="0.1.0",
    description="Newsletter Synthesizer — aggregates and curates LATAM tech news into Sinal Semanal",
    data_sources=LATAM_TECH_FEEDS,
    schedule_cron="0 6 * * 1",  # Every Monday at 6am UTC
    output_content_type="DATA_REPORT",
    min_confidence_to_publish=0.3,
    max_items_per_run=500,
)
