"""Configuration for the SINTESE agent — data sources, parameters, and feed list."""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig

# LATAM tech RSS/Atom feeds organized by category.
# Each feed is a DataSourceConfig for consistent handling.

LATAM_TECH_FEEDS: list[DataSourceConfig] = [
    # --- Brazilian Tech Media ---
    DataSourceConfig(name="startse", source_type="rss", url="https://www.startse.com/feed/", enabled=False),  # Returns HTML instead of RSS feed
    DataSourceConfig(name="convergenciadigital", source_type="rss", url="https://convergenciadigital.com.br/feed/", enabled=False),  # Telecom/regulatory focus, not aligned with technical audience
    DataSourceConfig(name="baguete", source_type="rss", url="https://www.baguete.com.br/rss/noticias/feed", enabled=False),  # Corporate IT news, low relevance for founders/CTOs

    # --- Premium LATAM Business/Tech ---
    DataSourceConfig(name="bloomberg_linea", source_type="rss", url="https://www.bloomberglinea.com.br/arc/outboundfeeds/rss/?outputType=xml"),
    DataSourceConfig(name="mobile_time", source_type="rss", url="https://www.mobiletime.com.br/feed/"),

    # --- Startup & VC ---
    DataSourceConfig(name="distrito", source_type="rss", url="https://distrito.me/blog/feed/", enabled=False),  # RSS feed removed
    DataSourceConfig(name="abstartups", source_type="rss", url="https://abstartups.com.br/feed/"),
    DataSourceConfig(name="startupi", source_type="rss", url="https://startupi.com.br/feed/", enabled=False),  # Low editorial quality
    DataSourceConfig(name="pipeline_valor", source_type="rss", url="https://pipelinevalor.globo.com/rss/", enabled=False),  # RSS feed removed
    DataSourceConfig(name="neofeed", source_type="rss", url="https://neofeed.com.br/feed/"),
    DataSourceConfig(name="blocknews", source_type="rss", url="https://blocknews.com.br/feed/", enabled=False),  # 403 Forbidden (bot blocking)
    DataSourceConfig(name="lavca", source_type="rss", url="https://www.lavca.org/feed/"),

    # --- LATAM (non-Brazil) ---
    DataSourceConfig(name="contxto", source_type="rss", url="https://contxto.com/feed/", enabled=False),  # SSL protocol error (TLS version mismatch)
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

    # --- Independent Tech Journalism ---
    DataSourceConfig(name="404media", source_type="rss", url="https://www.404media.co/rss/"),

    # --- AI & ML ---
    DataSourceConfig(name="theaibeat", source_type="rss", url="https://venturebeat.com/category/ai/feed/"),
    DataSourceConfig(name="mit_tech_review", source_type="rss", url="https://www.technologyreview.com/feed/"),
    DataSourceConfig(name="deeplearning_ai", source_type="rss", url="https://www.deeplearning.ai/blog/feed/", enabled=False),  # RSS feed removed

    # --- Developer & Infrastructure ---
    DataSourceConfig(name="infoq", source_type="rss", url="https://www.infoq.com/feed/"),
    DataSourceConfig(name="devto", source_type="rss", url="https://dev.to/feed"),
    DataSourceConfig(name="github_blog", source_type="rss", url="https://github.blog/feed/"),
    DataSourceConfig(name="netlify_blog", source_type="rss", url="https://www.netlify.com/blog/rss.xml", enabled=False),  # RSS feed removed (404)
    DataSourceConfig(name="vercel_blog", source_type="rss", url="https://vercel.com/atom", max_items=20),  # Atom feed returns all posts; cap to recent 20
    DataSourceConfig(name="cloudflare_blog", source_type="rss", url="https://blog.cloudflare.com/rss/"),

    # --- Fintech ---
    DataSourceConfig(name="fintechfutures", source_type="rss", url="https://www.fintechfutures.com/feed/", enabled=False),  # 403 Forbidden (bot blocking)
    DataSourceConfig(name="fintech_nexus", source_type="rss", url="https://www.fintechnexus.com/feed/"),
    DataSourceConfig(name="infomoney", source_type="rss", url="https://www.infomoney.com.br/feed/"),

    # --- VC & Startup Ops ---
    DataSourceConfig(name="a16z", source_type="rss", url="https://a16z.substack.com/feed"),  # Migrated from a16z.com/feed/ to Substack
    DataSourceConfig(name="ycombinator", source_type="rss", url="https://www.ycombinator.com/blog/rss/"),
    DataSourceConfig(name="first_round", source_type="rss", url="https://review.firstround.com/feed.xml", enabled=False),  # RSS feed removed
    DataSourceConfig(name="crunchbase_news", source_type="rss", url="https://news.crunchbase.com/feed/"),

    # --- Newsletters as RSS ---
    DataSourceConfig(name="tldrnewsletter", source_type="rss", url="https://tldr.tech/rss"),
    DataSourceConfig(name="bytebytego", source_type="rss", url="https://blog.bytebytego.com/feed"),
    DataSourceConfig(name="pragmatic_engineer", source_type="rss", url="https://newsletter.pragmaticengineer.com/feed"),
    DataSourceConfig(name="simonwillison", source_type="rss", url="https://simonwillison.net/atom/everything/"),
]

# Google News RSS — zero-auth, query-based news aggregation
GOOGLE_NEWS_SOURCES: list[DataSourceConfig] = [
    DataSourceConfig(
        name="gnews_fintech_br", source_type="rss", url=None,
        params={"query": "fintech open finance pix banco digital Brasil", "language": "pt-BR", "country": "BR"},
    ),
    DataSourceConfig(
        name="gnews_ai_latam", source_type="rss", url=None,
        params={"query": "artificial intelligence AI startup Latin America", "language": "en", "country": "BR"},
    ),
    DataSourceConfig(
        name="gnews_venture_br", source_type="rss", url=None,
        params={"query": "venture capital investimento startup rodada Brasil", "language": "pt-BR", "country": "BR"},
    ),
]

# X/Twitter API sources — one per editorial territory.
# Requires X_BEARER_TOKEN env var. Gracefully skipped when not set.
TWITTER_SOURCES: list[DataSourceConfig] = [
    DataSourceConfig(
        name="twitter_fintech", source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN", rate_limit_per_minute=10,
        params={"territory": "fintech"},
    ),
    DataSourceConfig(
        name="twitter_ai", source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN", rate_limit_per_minute=10,
        params={"territory": "ai"},
    ),
    DataSourceConfig(
        name="twitter_engenharia", source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN", rate_limit_per_minute=10,
        params={"territory": "engenharia"},
    ),
    DataSourceConfig(
        name="twitter_venture", source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN", rate_limit_per_minute=10,
        params={"territory": "venture"},
    ),
]

# LinkedIn RapidAPI — experimental, disabled by default.
# Requires RAPIDAPI_KEY env var. ~20 calls/run within free tier.
LINKEDIN_SOURCES: list[DataSourceConfig] = [
    DataSourceConfig(
        name="linkedin_fintech_posts", source_type="api",
        url="https://linkedin-data-api.p.rapidapi.com/search-posts",
        api_key_env="RAPIDAPI_KEY", enabled=False,
        params={"query": "fintech open finance pix Brasil", "limit": 10},
    ),
    DataSourceConfig(
        name="linkedin_ai_posts", source_type="api",
        url="https://linkedin-data-api.p.rapidapi.com/search-posts",
        api_key_env="RAPIDAPI_KEY", enabled=False,
        params={"query": "AI machine learning startup LATAM", "limit": 10},
    ),
]

# Reddit API — requires REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET env vars.
REDDIT_SOURCES: list[DataSourceConfig] = [
    DataSourceConfig(
        name="reddit_brdev", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "brdev", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_startups", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "startups", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_localllama", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "LocalLLaMA", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_fintech", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "fintech", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_venturecapital", source_type="api",
        url=None, api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "venturecapital", "sort": "hot", "limit": 25},
    ),
]

# Bluesky AT Protocol — no auth required.
BLUESKY_SOURCES: list[DataSourceConfig] = [
    DataSourceConfig(
        name="bluesky_fintech", source_type="api",
        url="https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params={"query": "fintech pix open finance Brasil", "limit": 25},
    ),
    DataSourceConfig(
        name="bluesky_ai", source_type="api",
        url="https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params={"query": "AI startup machine learning LATAM", "limit": 25},
    ),
]

SINTESE_PERSONA = AgentPersona(
    display_name="Clara Medeiros",
    role_title="Editora-chefe",
    nationality="Brasileira",
    bio_short="Jornalista especializada em tecnologia e startups LATAM",
    avatar_filename="clara-medeiros.jpg",
)

SINTESE_CONFIG = AgentConfig(
    agent_name="sintese",
    agent_category=AgentCategory.CONTENT,
    version="0.2.0",
    description="Newsletter Synthesizer — aggregates and curates LATAM tech news into Sinal Semanal",
    data_sources=(
        LATAM_TECH_FEEDS + GOOGLE_NEWS_SOURCES + TWITTER_SOURCES
        + LINKEDIN_SOURCES + REDDIT_SOURCES + BLUESKY_SOURCES
    ),
    schedule_cron="0 6 * * 1",  # Every Monday at 6am UTC
    output_content_type="DATA_REPORT",
    min_confidence_to_publish=0.3,
    max_items_per_run=500,
    persona=SINTESE_PERSONA,
)
