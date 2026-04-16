"""Configuration for the VOZES agent.

Defines data sources, taxonomy, persona, authority thresholds, LATAM relevance
config, and spam/self-promo filters for social media voice monitoring.
"""

from apps.agents.base.config import (
    AgentCategory,
    AgentConfig,
    AgentPersona,
    DataSourceConfig,
)

# ---------------------------------------------------------------------------
# Thematic taxonomy -- imported from social_signals for consistency.
# Both VOZES (classification) and PULSO (clustering) use the same taxonomy.
# ---------------------------------------------------------------------------

from apps.agents.social_signals.config import SIGNAL_TAXONOMY  # noqa: F401

# ---------------------------------------------------------------------------
# Authority thresholds
# ---------------------------------------------------------------------------

MIN_AUTHORITY_SCORE = 0.1  # Filter out very low-authority noise

BOT_PATTERNS: list[str] = [
    "grok", "chatgpt", "copilot", "perplexity_ai", "claudeai",
    "openai", "gemini", "bard", "bot", "automod", "automoderator",
]

# ---------------------------------------------------------------------------
# LATAM relevance config
# ---------------------------------------------------------------------------

MIN_LATAM_RELEVANCE = 0.15  # Below this, non-global-topic signals are skipped

# Global topics allowed even with low LATAM relevance
GLOBAL_TOPICS_ALLOWED: list[str] = ["AI", "Funding", "DevTools", "Cybersecurity"]

LATAM_COUNTRIES: list[str] = [
    "Brasil", "Brazil", "Mexico", "México", "Colombia", "Colômbia",
    "Argentina", "Chile", "Peru", "Perú", "Ecuador", "Uruguay",
    "Paraguay", "Paraguai", "Bolivia", "Bolívia", "Venezuela",
    "Costa Rica", "Panama", "Panamá", "Guatemala", "Honduras",
    "El Salvador", "República Dominicana", "Dominican Republic",
]

LATAM_CITIES: list[str] = [
    "São Paulo", "Sao Paulo", "Rio de Janeiro", "Belo Horizonte",
    "Curitiba", "Porto Alegre", "Florianópolis", "Florianopolis",
    "Recife", "Campinas", "Brasília", "Brasilia", "Salvador",
    "Ciudad de México", "Mexico City", "Guadalajara", "Monterrey",
    "Bogotá", "Bogota", "Medellín", "Medellin",
    "Buenos Aires", "Santiago", "Lima",
]

LATAM_COMPANIES: list[str] = [
    # Fintech
    "Nubank", "Mercado Libre", "Mercado Pago", "Stone", "PagSeguro",
    "Creditas", "C6 Bank", "Inter", "Neon", "Clip", "Ualá", "Konfio",
    "Rappi", "dLocal", "VTEX", "Brex", "Ebanx", "Nuvemshop",
    # Tech / SaaS
    "TOTVS", "Movile", "iFood", "99", "QuintoAndar", "Loft",
    "Gympass", "Wellhub", "Loggi", "Olist", "Cloudwalk", "Cora",
    "Bitso", "Kavak", "Globant", "MercadoLibre", "Despegar",
    # HealthTech
    "Alice", "Pipo Saude", "Feegow", "Dr. Consulta",
    # EdTech
    "Descomplica", "Platzi", "Alura", "Rocketseat",
    # Enterprise / Data
    "Semantix", "Caju", "Flash", "Gupy", "Sólides",
    # New wave
    "Pomelo", "Belvo", "Jeeves", "Tribal Credit", "Clara",
]

# ---------------------------------------------------------------------------
# Spam / self-promo / off-topic filters
# ---------------------------------------------------------------------------

BLOCKED_PATTERNS: list[str] = [
    # Reddit megathreads and self-promo
    "weekly thread", "self-promo", "self-promotion", "shameless plug",
    "show hn:", "hiring thread", "who is hiring", "freelance thread",
    "monthly thread", "daily discussion", "megathread",
    # Generic promotional
    "check out my", "i just launched", "we just launched",
    "our new product", "sign up for", "use my referral",
    "use my code", "discount code", "affiliate link",
    # Off-topic noise
    "weekly roundup thread", "ask hn:", "tell hn:",
]

# ---------------------------------------------------------------------------
# Ticker-to-company resolution
# ---------------------------------------------------------------------------

TICKER_TO_NAME: dict[str, str] = {
    "NU": "Nubank",
    "MELI": "Mercado Libre",
    "STNE": "Stone",
    "PAGS": "PagSeguro",
    "VTEX": "VTEX",
    "XP": "XP Inc",
    "GLOB": "Globant",
    "DESP": "Despegar",
    "DLO": "dLocal",
    "BREX": "Brex",
    "DASH": "DoorDash",
    "MSFT": "Microsoft",
    "GOOG": "Google",
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "META": "Meta",
    "NVDA": "Nvidia",
    "TSLA": "Tesla",
    "CRM": "Salesforce",
    "SNOW": "Snowflake",
}

# ---------------------------------------------------------------------------
# Data sources — rebalanced from social_signals (47 -> 38 sources)
# ---------------------------------------------------------------------------

VOZES_SOURCES: list[DataSourceConfig] = [
    # --- Twitter/X (8 sources) ---
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
    # NEW: LATAM-focused Twitter searches
    DataSourceConfig(
        name="twitter_latam_startups",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "startup LATAM OR startup Brasil OR startup Mexico lang:pt OR lang:es", "sort": "recent", "max_results": 50},
    ),
    DataSourceConfig(
        name="twitter_latam_funding",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "rodada investimento OR fundraise LATAM OR Serie A Brasil", "sort": "recent", "max_results": 30},
    ),
    DataSourceConfig(
        name="twitter_latam_ai",
        source_type="api",
        url="https://api.twitter.com/2/tweets/search/recent",
        api_key_env="X_BEARER_TOKEN",
        params={"query": "IA Brasil OR AI LATAM OR inteligencia artificial startup", "sort": "recent", "max_results": 30},
    ),

    # --- Reddit (8 sources: 4 API + 4 RSS fallback) ---
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
        name="reddit_cryptocurrency",
        source_type="api",
        url=None,
        api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "CryptoCurrency", "sort": "hot", "limit": 25},
    ),
    DataSourceConfig(
        name="reddit_startups",
        source_type="api",
        url=None,
        api_key_env="REDDIT_CLIENT_ID",
        params={"subreddit": "startups", "sort": "hot", "limit": 25},
    ),
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
        name="reddit_rss_artificial",
        source_type="rss",
        url="https://www.reddit.com/r/artificial/hot.rss",
    ),
    DataSourceConfig(
        name="reddit_rss_startups",
        source_type="rss",
        url="https://www.reddit.com/r/startups/hot.rss",
    ),

    # --- Bluesky (3 sources) ---
    DataSourceConfig(
        name="bluesky_ai_agents",
        source_type="api",
        url="https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params={"query": "AI agents LLM", "limit": 15},
    ),
    DataSourceConfig(
        name="bluesky_fintech",
        source_type="api",
        url="https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params={"query": "fintech neobank payments", "limit": 15},
    ),
    DataSourceConfig(
        name="bluesky_startups_latam",
        source_type="api",
        url="https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params={"query": "startup LATAM venture capital", "limit": 15},
    ),

    # --- RSS/Newsletters (6 high-signal sources) ---
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
        name="a16z_blog",
        source_type="rss",
        url="https://a16z.com/feed/",
    ),
    DataSourceConfig(
        name="fintech_takes",
        source_type="rss",
        url="https://newsletter.fintechtakes.com/feed",
    ),

    # --- YouTube (3 sources) ---
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

    # --- LinkedIn (1 source, disabled) ---
    DataSourceConfig(
        name="linkedin_fintech_ai",
        source_type="api",
        url="https://linkedin-data-api.p.rapidapi.com/search-posts",
        api_key_env="RAPIDAPI_KEY",
        enabled=False,
        params={"query": "fintech AI banking LATAM", "limit": 25},
    ),

    # --- Podcasts (4 LATAM-focused) ---
    DataSourceConfig(
        name="podcast_a16z",
        source_type="rss",
        url="https://a16z.simplecast.com/rss",
        params={"max_items": 5},
    ),
    DataSourceConfig(
        name="podcast_latitud",
        source_type="rss",
        url="https://anchor.fm/s/5e8d2e20/podcast/rss",
        params={"max_items": 5},
    ),
    DataSourceConfig(
        name="podcast_cafe_com_startups",
        source_type="rss",
        url="https://anchor.fm/s/2c2c2b64/podcast/rss",
        params={"max_items": 5},
    ),
    DataSourceConfig(
        name="podcast_hipsters_tech",
        source_type="rss",
        url="https://hipsters.tech/feed/podcast/",
        params={"max_items": 5},
    ),

    # --- Web scrapers (2 sources) ---
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

    # --- GitHub Trending (1 source) ---
    DataSourceConfig(
        name="github_trending_signals",
        source_type="api",
        url="https://api.github.com/search/repositories",
        params={"sort": "stars", "order": "desc", "window": "weekly"},
    ),

    # --- Hacker News (2 sources) ---
    DataSourceConfig(
        name="hn_ai",
        source_type="rss",
        url="https://hnrss.org/newest?q=AI+LLM+agents",
        params={"points": 20},
    ),
    DataSourceConfig(
        name="hn_fintech",
        source_type="rss",
        url="https://hnrss.org/newest?q=fintech+payments+banking",
        params={"points": 20},
    ),
]

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

VOZES_PERSONA = AgentPersona(
    display_name="Marina Santos",
    role_title="Analista de Vozes do Ecossistema",
    nationality="Brasileira",
    bio_short="Jornalista de dados que monitora vozes e sinais emergentes no ecossistema LATAM",
    avatar_filename="marina-santos.jpg",
)

# ---------------------------------------------------------------------------
# Agent config
# ---------------------------------------------------------------------------

VOZES_CONFIG = AgentConfig(
    agent_name="vozes",
    agent_category=AgentCategory.DATA,
    version="0.1.0",
    description="Social media voice monitoring, classification, and authority scoring for LATAM tech",
    data_sources=VOZES_SOURCES,
    schedule_cron="0 8 * * 1",  # Monday 8am UTC, BEFORE pulso at 9am
    output_content_type="DATA_REPORT",
    min_confidence_to_publish=0.2,
    max_items_per_run=2000,
    persona=VOZES_PERSONA,
)
