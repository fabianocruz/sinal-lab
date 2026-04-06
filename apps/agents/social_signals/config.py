"""Configuration for Social Signal Intelligence agent.

Defines data sources, taxonomy, persona, and signal scoring parameters
for monitoring social media and detecting emerging trends in AI, Fintech,
and Banking across LATAM and global markets.
"""

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona, DataSourceConfig

# ---------------------------------------------------------------------------
# Thematic taxonomy — macro themes, subtemas, and narrative patterns
# ---------------------------------------------------------------------------

SIGNAL_TAXONOMY = {
    "AI": {
        "subtemas": [
            "AI agents",
            "LLM infrastructure",
            "AI safety and governance",
            "Open source AI",
            "AI in healthcare",
            "AI developer tools",
            "Multimodal AI",
            "Edge AI and on-device",
        ],
        "narratives": [
            "AI replacing analysts",
            "open source catching up to closed models",
            "AI regulation accelerating",
            "enterprise AI ROI reality check",
        ],
    },
    "Fintech": {
        "subtemas": [
            "Payments infrastructure",
            "Embedded finance",
            "Lending and credit",
            "Neobanks",
            "Crypto and DeFi",
            "Insurtech",
            "Wealthtech",
            "Cross-border payments",
            "Open banking",
            "BaaS",
        ],
        "narratives": [
            "B2B payments infrastructure",
            "open banking monetization",
            "stablecoin rails for LATAM",
            "embedded finance as default",
        ],
    },
    "AI in Banking": {
        "subtemas": [
            "AI agents for compliance",
            "KYC automation",
            "Underwriting copilots",
            "Fraud detection AI",
            "AML monitoring",
            "Core banking modernization",
            "Model risk governance",
            "GenAI compliance",
            "Voice AI in collections",
        ],
        "narratives": [
            "banks adopting copilots",
            "agentic compliance workflows",
            "AI underwriting replacing FICO",
            "real-time fraud with LLMs",
        ],
    },
}

# ---------------------------------------------------------------------------
# Signal scoring parameters
# ---------------------------------------------------------------------------

SIGNAL_DIMENSIONS = [
    "volume",
    "velocity",
    "authority_concentration",
    "cross_platform_propagation",
    "sentiment_shift",
    "new_entrants",
    "narrative_maturity",
    "commercial_signals",
]

DIMENSION_WEIGHTS = {
    "volume": 0.10,
    "velocity": 0.20,
    "authority_concentration": 0.15,
    "cross_platform_propagation": 0.15,
    "sentiment_shift": 0.10,
    "new_entrants": 0.10,
    "narrative_maturity": 0.10,
    "commercial_signals": 0.10,
}

# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

SOCIAL_SIGNAL_SOURCES = [
    # --- Twitter/X ---
    DataSourceConfig(
        name="twitter_ai_fintech",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "(AI agents OR fintech OR neobank OR LLM) lang:en -is:retweet", "max_results": 100},
    ),
    DataSourceConfig(
        name="twitter_banking_ai",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "(banking AI OR compliance AI OR underwriting OR KYC automation) lang:en -is:retweet", "max_results": 100},
    ),
    DataSourceConfig(
        name="twitter_latam_tech",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "(startup LATAM OR fintech Brasil OR VC Latin America) -is:retweet", "max_results": 100},
    ),
    # Twitter — tweets sharing YouTube/video content about AI & fintech
    DataSourceConfig(
        name="twitter_ai_videos",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "(AI OR LLM OR GPT OR fintech) (url:youtube.com OR url:youtu.be) -is:retweet lang:en", "max_results": 50},
    ),
    DataSourceConfig(
        name="twitter_tech_videos_ptbr",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "(inteligência artificial OR fintech OR startup) (url:youtube.com OR url:youtu.be) -is:retweet lang:pt", "max_results": 50},
    ),

    # --- Reddit ---
    DataSourceConfig(
        name="reddit_fintech",
        source_type="api",
        url=None,
        api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "fintech", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_machinelearning",
        source_type="api",
        url=None,
        api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "MachineLearning", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_banking",
        source_type="api",
        url=None,
        api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "banking", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_cryptocurrency",
        source_type="api",
        url=None,
        api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "CryptoCurrency", "sort": "hot", "limit": 25},
    ),

    # --- Reddit RSS (fallback, no auth required) ---
    DataSourceConfig(
        name="reddit_rss_fintech",
        source_type="rss",
        url="https://www.reddit.com/r/fintech/hot.rss",
    ),
    DataSourceConfig(
        name="reddit_rss_machinelearning",
        source_type="rss",
        url="https://www.reddit.com/r/MachineLearning/hot.rss",
    ),
    DataSourceConfig(
        name="reddit_rss_banking",
        source_type="rss",
        url="https://www.reddit.com/r/banking/hot.rss",
    ),
    DataSourceConfig(
        name="reddit_rss_cryptocurrency",
        source_type="rss",
        url="https://www.reddit.com/r/CryptoCurrency/hot.rss",
    ),
    DataSourceConfig(
        name="reddit_rss_artificial",
        source_type="rss",
        url="https://www.reddit.com/r/artificial/hot.rss",
    ),
    DataSourceConfig(
        name="reddit_rss_startups",
        source_type="rss",
        url="https://www.reddit.com/r/startups/hot.rss",
    ),

    # --- Bluesky ---
    DataSourceConfig(
        name="bluesky_ai_fintech",
        source_type="api",
        url="https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params={"query": "AI fintech banking startup", "limit": 25},
    ),

    # --- LinkedIn ---
    DataSourceConfig(
        name="linkedin_fintech_ai",
        source_type="api",
        url="https://linkedin-data-api.p.rapidapi.com/search-posts",
        api_key_env="RAPIDAPI_KEY",
        enabled=False,  # Enable when RapidAPI key configured
        params={"query": "fintech AI banking LATAM", "limit": 25},
    ),

    # --- Newsletters/Blogs (RSS) ---
    DataSourceConfig(
        name="this_week_in_fintech",
        source_type="rss",
        url="https://www.thisweekinfintech.com/feed",
    ),
    DataSourceConfig(
        name="fintech_brain_food",
        source_type="rss",
        url="https://brainfood.substack.com/feed",
    ),
    DataSourceConfig(
        name="fintech_takes",
        source_type="rss",
        url="https://newsletter.fintechtakes.com/feed",
    ),
    DataSourceConfig(
        name="not_boring",
        source_type="rss",
        url="https://www.notboring.co/feed",
    ),
    DataSourceConfig(
        name="the_batch_andrew_ng",
        source_type="rss",
        url="https://www.deeplearning.ai/the-batch/feed/",
    ),
    DataSourceConfig(
        name="stratechery",
        source_type="rss",
        url="https://stratechery.com/feed/",
    ),
    DataSourceConfig(
        name="the_information",
        source_type="rss",
        url="https://www.theinformation.com/feed",
    ),
    DataSourceConfig(
        name="a16z_blog",
        source_type="rss",
        url="https://a16z.com/feed/",
    ),
    DataSourceConfig(
        name="sequoia_blog",
        source_type="rss",
        url="https://www.sequoiacap.com/feed/",
    ),
    DataSourceConfig(
        name="fintech_blueprint",
        source_type="rss",
        url="https://lex.substack.com/feed",
    ),

    # --- Hacker News (reused from RADAR agent) ---
    DataSourceConfig(
        name="hn_best_signals",
        source_type="rss",
        url="https://hnrss.org/best",
        params={"points": 50},
    ),
    DataSourceConfig(
        name="hn_show_signals",
        source_type="rss",
        url="https://hnrss.org/show",
    ),

    # --- GitHub Trending (reused from CODIGO/RADAR agents) ---
    DataSourceConfig(
        name="github_trending_signals",
        source_type="api",
        url="https://api.github.com/search/repositories",
        params={"sort": "stars", "order": "desc", "window": "weekly"},
    ),

    # --- YouTube ---
    DataSourceConfig(
        name="youtube_ai_fintech",
        source_type="api",
        url="https://www.googleapis.com/youtube/v3/search",
        api_key_env="YOUTUBE_API_KEY",
        params={"query": "AI agents fintech banking", "max_results": 25},
    ),
    DataSourceConfig(
        name="youtube_latam_startups",
        source_type="api",
        url="https://www.googleapis.com/youtube/v3/search",
        api_key_env="YOUTUBE_API_KEY",
        params={"query": "startups LATAM venture capital tecnologia", "max_results": 25},
    ),
    DataSourceConfig(
        name="youtube_open_banking",
        source_type="api",
        url="https://www.googleapis.com/youtube/v3/search",
        api_key_env="YOUTUBE_API_KEY",
        params={"query": "open banking Brasil pagamentos digitais", "max_results": 25},
    ),

    # --- Web scraper sources (newsletter archives without RSS) ---
    DataSourceConfig(
        name="newcomer_archive",
        source_type="scraper",
        url="https://www.newcomer.co/archive",
        params={"max_items": 10, "fetch_content": True},
    ),
    DataSourceConfig(
        name="the_generalist_archive",
        source_type="scraper",
        url="https://www.generalist.com/archive",
        params={"max_items": 10, "fetch_content": True},
    ),
    DataSourceConfig(
        name="pragmatic_engineer_archive",
        source_type="scraper",
        url="https://newsletter.pragmaticengineer.com/archive",
        params={"max_items": 10, "fetch_content": False},
    ),
]

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

SOCIAL_SIGNALS_PERSONA = AgentPersona(
    display_name="Lucas Chen",
    role_title="Analista de Sinais Sociais",
    nationality="Brasileiro-Chinês",
    bio_short="Rastreia sinais emergentes em redes sociais para AI, Fintech e Banking",
    avatar_filename="lucas-chen.jpg",
)

# ---------------------------------------------------------------------------
# Agent config
# ---------------------------------------------------------------------------

SOCIAL_SIGNALS_CONFIG = AgentConfig(
    agent_name="social_signals",
    agent_category=AgentCategory.DATA,
    version="0.1.0",
    description="Social Signal Intelligence for AI, Fintech, and Banking emerging themes",
    data_sources=SOCIAL_SIGNAL_SOURCES,
    schedule_cron="0 8 * * 1",  # Monday 8am UTC
    output_content_type="ANALYSIS",
    min_confidence_to_publish=0.3,
    max_items_per_run=2000,
    persona=SOCIAL_SIGNALS_PERSONA,
)
