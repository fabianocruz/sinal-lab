"""Configuration for the SINTESE agent — data sources, parameters, and feed list."""

from apps.agents.base.config import AgentCategory, AgentConfig, DataSourceConfig

# LATAM tech RSS/Atom feeds organized by category.
# Each feed is a DataSourceConfig for consistent handling.

LATAM_TECH_FEEDS: list[DataSourceConfig] = [
    # --- Brazilian Tech Media ---
    DataSourceConfig(name="startse", source_type="rss", url="https://www.startse.com/feed/"),
    DataSourceConfig(name="convergenciadigital", source_type="rss", url="https://www.convergenciadigital.com.br/rss.php"),
    DataSourceConfig(name="baguete", source_type="rss", url="https://www.baguete.com.br/rss"),

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
    DataSourceConfig(name="wired", source_type="rss", url="https://www.wired.com/feed/rss"),
    DataSourceConfig(name="geekwire", source_type="rss", url="https://www.geekwire.com/feed/"),
    DataSourceConfig(name="cnbc_tech", source_type="rss", url="https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"),
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
    DataSourceConfig(name="fintech_nexus", source_type="rss", url="https://www.fintechnexus.com/feed/"),
    DataSourceConfig(name="infomoney", source_type="rss", url="https://www.infomoney.com.br/feed/"),

    # --- VC & Startup Ops ---
    DataSourceConfig(name="a16z", source_type="rss", url="https://a16z.com/feed/"),
    DataSourceConfig(name="ycombinator", source_type="rss", url="https://www.ycombinator.com/blog/rss/"),
    DataSourceConfig(name="first_round", source_type="rss", url="https://review.firstround.com/feed.xml"),
    DataSourceConfig(name="crunchbase_news", source_type="rss", url="https://news.crunchbase.com/feed/"),

    # --- Newsletters as RSS ---
    DataSourceConfig(name="tldrnewsletter", source_type="rss", url="https://tldr.tech/rss"),
    DataSourceConfig(name="bytebytego", source_type="rss", url="https://blog.bytebytego.com/feed"),
    DataSourceConfig(name="pragmatic_engineer", source_type="rss", url="https://newsletter.pragmaticengineer.com/feed"),
    DataSourceConfig(name="simonwillison", source_type="rss", url="https://simonwillison.net/atom/everything/"),
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
