"""Multi-source collector for the Social Signals Intelligence agent.

Fetches posts from Twitter/X, Reddit, Bluesky, RSS newsletter feeds,
monitored account timelines, and web-scraped newsletter archives.
Each platform source is normalized into SocialPost for unified processing.

Platform-specific collectors handle authentication, pagination, and error
recovery. The collect_all() function orchestrates all sources and deduplicates
by content_hash before returning.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.social_signals.models import SocialPost
from apps.agents.sources.dedup import deduplicate_by_hash
from apps.agents.sources.http import create_http_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Polymarket relevance filter — only keep markets related to our themes
# ---------------------------------------------------------------------------

POLYMARKET_KEYWORDS: list[str] = [
    "ai", "artificial intelligence", "machine learning", "llm", "gpt",
    "crypto", "bitcoin", "ethereum", "solana", "stablecoin", "defi",
    "fintech", "banking", "payments", "neobank",
    "startup", "ipo", "funding", "venture", "regulation",
    "fed", "interest rate", "inflation", "central bank",
    "tech", "software", "saas", "cloud",
    "semiconductor", "chip", "nvidia", "openai", "anthropic",
]


def _is_relevant_polymarket(title: str, description: str) -> bool:
    """Return True if a Polymarket market matches our topic keywords.

    We search both title and description (lowercased) for any keyword.
    This filters out sports, entertainment, politics-only markets, etc.
    """
    text_lower = (title + " " + description).lower()
    return any(kw in text_lower for kw in POLYMARKET_KEYWORDS)


# ---------------------------------------------------------------------------
# Normalizers: platform-specific -> SocialPost
# ---------------------------------------------------------------------------


def normalize_twitter_post(post: "TwitterPost") -> SocialPost:
    """Convert a TwitterPost to a unified SocialPost.

    Maps Twitter-specific engagement metrics (likes, replies, retweets,
    quotes, impressions) into the generic metrics dict.

    Args:
        post: A TwitterPost from the shared Twitter source connector.

    Returns:
        SocialPost with platform="twitter".
    """
    from apps.agents.sources.twitter import TwitterPost  # noqa: F811

    return SocialPost(
        text=post.text,
        url=post.url,
        platform="twitter",
        author_handle=post.author_handle or "",
        author_display_name=post.author_display_name or "",
        author_followers=post.author_followers,
        published_at=post.created_at,
        external_url=post.external_url,
        image_url=post.image_url,
        source_name=post.source_name,
        metrics={
            "likes": post.like_count,
            "replies": post.reply_count,
            "reposts": post.retweet_count,
            "quotes": post.quote_count,
            "impressions": post.impression_count,
        },
        content_hash=post.content_hash,
    )


def normalize_reddit_post(post: "RedditPost") -> SocialPost:
    """Convert a RedditPost to a unified SocialPost.

    Reddit posts use the title + selftext as the text field since Reddit
    is title-driven. The permalink is stored as the canonical URL while
    the external_url holds the link target for link posts.

    Args:
        post: A RedditPost from the shared Reddit source connector.

    Returns:
        SocialPost with platform="reddit".
    """
    from apps.agents.sources.reddit import RedditPost  # noqa: F811

    # Combine title and body for richer text classification
    text = post.title
    if post.selftext:
        text = f"{post.title}\n\n{post.selftext[:500]}"

    # For link posts, the URL is external; for self posts, use permalink
    canonical_url = f"https://reddit.com{post.permalink}" if post.permalink else post.url
    external_url = post.url if "reddit.com" not in post.url else None

    return SocialPost(
        text=text,
        url=canonical_url,
        platform="reddit",
        author_handle=post.author or "",
        author_display_name=post.author or "",
        author_followers=0,  # Reddit API doesn't expose follower count in listings
        published_at=post.created_utc,
        external_url=external_url,
        image_url=post.image_url,
        source_name=post.source_name,
        metrics={
            "score": post.score,
            "comments": post.num_comments,
        },
        content_hash=post.content_hash,
    )


def normalize_bluesky_post(post: "BlueskyPost") -> SocialPost:
    """Convert a BlueskyPost to a unified SocialPost.

    Bluesky engagement metrics (likes, replies, reposts) map directly
    to the generic metrics dict.

    Args:
        post: A BlueskyPost from the shared Bluesky source connector.

    Returns:
        SocialPost with platform="bluesky".
    """
    from apps.agents.sources.bluesky import BlueskyPost  # noqa: F811

    return SocialPost(
        text=post.text,
        url=post.url,
        platform="bluesky",
        author_handle=post.author_handle or "",
        author_display_name=post.author_display_name or "",
        author_followers=0,  # Bluesky public API doesn't expose follower count
        published_at=post.created_at,
        external_url=post.external_url,
        image_url=post.image_url,
        source_name=post.source_name,
        metrics={
            "likes": post.like_count,
            "replies": post.reply_count,
            "reposts": post.repost_count,
        },
        content_hash=post.content_hash,
    )


def normalize_rss_item(item: "RSSItem") -> SocialPost:
    """Convert an RSSItem (newsletter/blog) to a unified SocialPost.

    RSS items from newsletters and blogs serve as signal sources for
    narrative tracking. The title + summary become the text for classification.

    Args:
        item: An RSSItem from the shared RSS source connector.

    Returns:
        SocialPost with platform="rss".
    """
    from apps.agents.sources.rss import RSSItem  # noqa: F811

    text = item.title
    if item.summary:
        text = f"{item.title}\n\n{item.summary[:500]}"

    return SocialPost(
        text=text,
        url=item.url,
        platform="rss",
        author_handle=item.author or "",
        author_display_name=item.author or "",
        author_followers=0,
        published_at=item.published_at,
        external_url=None,
        image_url=item.image_url,
        source_name=item.source_name,
        metrics={},
        content_hash=item.content_hash,
    )


def normalize_youtube_item(item: dict) -> SocialPost:
    """Convert a YouTube comment/video dict from Monid to a unified SocialPost.

    Monid YouTube scrapers return dicts with varying keys depending on
    the specific Apify actor. We handle the common field names.

    Args:
        item: Dict from fetch_youtube_comments().

    Returns:
        SocialPost with platform="youtube".
    """
    # Build text from available fields
    text_parts = []
    if item.get("videoTitle"):
        text_parts.append(item["videoTitle"])
    if item.get("text") or item.get("comment"):
        text_parts.append((item.get("text") or item.get("comment", ""))[:500])
    if item.get("description"):
        text_parts.append(item["description"][:300])

    text = "\n\n".join(text_parts) if text_parts else ""

    url = item.get("videoUrl") or item.get("url") or ""
    author = item.get("author") or item.get("channelName") or ""

    return SocialPost(
        text=text,
        url=url,
        platform="youtube",
        author_handle=author,
        author_display_name=author,
        author_followers=item.get("subscriberCount", 0) or 0,
        source_name="monid_youtube",
        metrics={
            "likes": item.get("likes", 0) or 0,
            "views": item.get("viewCount", 0) or item.get("views", 0) or 0,
            "comments": item.get("commentCount", 0) or item.get("replyCount", 0) or 0,
        },
    )


def normalize_youtube_video(video: "YouTubeVideo") -> SocialPost:
    """Convert a YouTubeVideo (native API) to a unified SocialPost.

    Maps YouTube video fields and engagement metrics into the generic
    SocialPost structure for unified processing.

    Args:
        video: A YouTubeVideo from the shared YouTube source connector.

    Returns:
        SocialPost with platform="youtube".
    """
    from apps.agents.sources.youtube import YouTubeVideo  # noqa: F811

    text = video.title
    if video.description:
        text = f"{video.title}\n\n{video.description[:500]}"

    return SocialPost(
        text=text,
        url=video.url,
        platform="youtube",
        author_handle=video.channel_title,
        author_display_name=video.channel_title,
        author_followers=video.subscriber_count,
        published_at=video.published_at,
        image_url=video.thumbnail_url,
        source_name="youtube_api",
        metrics={
            "likes": video.like_count,
            "views": video.view_count,
            "comments": video.comment_count,
        },
        content_hash=video.content_hash,
    )


def normalize_web_scraped_article(article: dict) -> SocialPost:
    """Convert a web-scraped article dict to a unified SocialPost.

    Articles from scrape_newsletter_archive() are dicts with keys:
    title, url, published_at, summary, source_name, content_hash.

    Args:
        article: Dict from scrape_newsletter_archive().

    Returns:
        SocialPost with platform="web".
    """
    text = article.get("title", "")
    summary = article.get("summary")
    if summary:
        text = f"{text}\n\n{summary[:500]}"

    return SocialPost(
        text=text,
        url=article.get("url", ""),
        platform="web",
        author_handle="",
        author_display_name="",
        author_followers=0,
        published_at=article.get("published_at"),
        external_url=None,
        image_url=None,
        source_name=article.get("source_name", ""),
        metrics={},
        content_hash=article.get("content_hash", ""),
    )


# ---------------------------------------------------------------------------
# Per-platform collectors
# ---------------------------------------------------------------------------


def collect_from_twitter(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    client: "httpx.Client",
    agent_name: str = "social_signals",
    run_id: str = "",
) -> List[SocialPost]:
    """Collect posts from all Twitter/X data source configs.

    Each source config should have a 'query' and optional 'max_results'
    in its params dict.

    Args:
        sources: Twitter DataSourceConfig items (name contains "twitter").
        provenance: Provenance tracker for recording source attribution.
        client: Shared httpx.Client for API requests.
        agent_name: Agent name for provenance tracking.
        run_id: Current run ID for provenance tracking.

    Returns:
        List of normalized SocialPost items from Twitter.
    """
    from apps.agents.sources.twitter import fetch_twitter_search

    posts: List[SocialPost] = []

    for source in sources:
        if not source.enabled:
            continue

        query = source.params.get("query", "")
        max_results = source.params.get("max_results", 100)

        twitter_posts = fetch_twitter_search(
            source, client, query=query, max_results=max_results,
        )

        for tp in twitter_posts:
            posts.append(normalize_twitter_post(tp))
            provenance.track(
                source_url=tp.url,
                source_name=source.name,
                extraction_method="api",
                confidence=0.6,
                collector_agent=agent_name,
                collector_run_id=run_id,
            )

    logger.info("Twitter: collected %d posts from %d sources", len(posts), len(sources))
    return posts


def collect_from_reddit(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    client: "httpx.Client",
    agent_name: str = "social_signals",
    run_id: str = "",
) -> List[SocialPost]:
    """Collect posts from all Reddit data source configs.

    Each source config should have 'subreddit', 'sort', and 'limit'
    in its params dict.

    Args:
        sources: Reddit DataSourceConfig items (name contains "reddit").
        provenance: Provenance tracker for recording source attribution.
        client: Shared httpx.Client for API requests.
        agent_name: Agent name for provenance tracking.
        run_id: Current run ID for provenance tracking.

    Returns:
        List of normalized SocialPost items from Reddit.
    """
    from apps.agents.sources.reddit import fetch_subreddit_posts

    posts: List[SocialPost] = []

    for source in sources:
        if not source.enabled:
            continue

        subreddit = source.params.get("subreddit", "")
        sort = source.params.get("sort", "hot")
        limit = source.params.get("limit", 25)

        reddit_posts = fetch_subreddit_posts(
            source, client, subreddit=subreddit, sort=sort, limit=limit,
        )

        for rp in reddit_posts:
            posts.append(normalize_reddit_post(rp))
            url = f"https://reddit.com{rp.permalink}" if rp.permalink else rp.url
            provenance.track(
                source_url=url,
                source_name=source.name,
                extraction_method="api",
                confidence=0.5,
                collector_agent=agent_name,
                collector_run_id=run_id,
            )

    logger.info("Reddit: collected %d posts from %d sources", len(posts), len(sources))
    return posts


def collect_from_bluesky(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    client: "httpx.Client",
    agent_name: str = "social_signals",
    run_id: str = "",
) -> List[SocialPost]:
    """Collect posts from all Bluesky data source configs.

    Each source config should have 'query' and optional 'limit' in
    its params dict.

    Args:
        sources: Bluesky DataSourceConfig items (name contains "bluesky").
        provenance: Provenance tracker for recording source attribution.
        client: Shared httpx.Client for API requests.
        agent_name: Agent name for provenance tracking.
        run_id: Current run ID for provenance tracking.

    Returns:
        List of normalized SocialPost items from Bluesky.
    """
    from apps.agents.sources.bluesky import fetch_bluesky_search

    posts: List[SocialPost] = []

    for source in sources:
        if not source.enabled:
            continue

        query = source.params.get("query", "")
        limit = source.params.get("limit", 25)

        bsky_posts = fetch_bluesky_search(
            source, client, query=query, limit=limit,
        )

        for bp in bsky_posts:
            posts.append(normalize_bluesky_post(bp))
            provenance.track(
                source_url=bp.url,
                source_name=source.name,
                extraction_method="api",
                confidence=0.5,
                collector_agent=agent_name,
                collector_run_id=run_id,
            )

    logger.info("Bluesky: collected %d posts from %d sources", len(posts), len(sources))
    return posts


def collect_from_rss(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    client: "httpx.Client",
    agent_name: str = "social_signals",
    run_id: str = "",
) -> List[SocialPost]:
    """Collect items from all RSS/newsletter data source configs.

    Uses the shared RSS feed parser to fetch and normalize newsletter
    and blog content into SocialPost for theme classification.

    Args:
        sources: RSS DataSourceConfig items (source_type="rss").
        provenance: Provenance tracker for recording source attribution.
        client: Shared httpx.Client for HTTP requests.
        agent_name: Agent name for provenance tracking.
        run_id: Current run ID for provenance tracking.

    Returns:
        List of normalized SocialPost items from RSS feeds.
    """
    from apps.agents.sources.rss import fetch_rss_feed

    posts: List[SocialPost] = []

    for source in sources:
        if not source.enabled:
            continue

        rss_items = fetch_rss_feed(source, client)

        for item in rss_items:
            posts.append(normalize_rss_item(item))
            provenance.track(
                source_url=item.url,
                source_name=source.name,
                extraction_method="rss",
                confidence=0.7,
                collector_agent=agent_name,
                collector_run_id=run_id,
            )

    logger.info("RSS: collected %d items from %d sources", len(posts), len(sources))
    return posts


def collect_from_web_scraper(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    client: "httpx.Client",
    agent_name: str = "social_signals",
    run_id: str = "",
) -> List[SocialPost]:
    """Collect articles from web-scraped newsletter archive pages.

    Uses the shared web scraper to fetch archive listings and extract
    article entries. Each article is normalized to SocialPost with
    platform="web".

    Args:
        sources: Web scraper DataSourceConfig items (source_type="scraper").
        provenance: Provenance tracker for recording source attribution.
        client: Shared httpx.Client for HTTP requests.
        agent_name: Agent name for provenance tracking.
        run_id: Current run ID for provenance tracking.

    Returns:
        List of normalized SocialPost items from web-scraped archives.
    """
    from apps.agents.sources.web_scraper import scrape_newsletter_archive

    posts: List[SocialPost] = []

    for source in sources:
        if not source.enabled:
            continue

        articles = scrape_newsletter_archive(source, client)

        for article in articles:
            posts.append(normalize_web_scraped_article(article))
            provenance.track(
                source_url=article.get("url"),
                source_name=source.name,
                extraction_method="scraper",
                confidence=0.4,  # Lower confidence: scraped content
                collector_agent=agent_name,
                collector_run_id=run_id,
            )

    logger.info("Web scraper: collected %d articles from %d sources", len(posts), len(sources))
    return posts


def collect_from_youtube(
    provenance: ProvenanceTracker,
    queries: Optional[List[str]] = None,
    max_per_query: int = 25,
) -> List[SocialPost]:
    """Collect YouTube videos via native Data API v3 or Monid fallback.

    Tries the native YouTube Data API v3 first when YOUTUBE_API_KEY is
    configured. Falls back to Monid YouTube scraper when MONID_API_KEY
    is set but YOUTUBE_API_KEY is not. Returns empty if neither is available.

    Args:
        provenance: Provenance tracker for recording source attribution.
        queries: Search queries. Defaults to AI/fintech/banking queries.
        max_per_query: Max results per query.

    Returns:
        List of normalized SocialPost items from YouTube.
    """
    if queries is None:
        queries = [
            "AI agents fintech",
            "banking technology LATAM",
        ]

    # Strategy 1: Native YouTube Data API v3
    try:
        import os
        if os.getenv("YOUTUBE_API_KEY"):
            from apps.agents.sources.youtube import fetch_youtube_videos

            all_posts: List[SocialPost] = []
            for query in queries:
                videos = fetch_youtube_videos(
                    query, max_results=max_per_query,
                )
                for video in videos:
                    post = normalize_youtube_video(video)
                    if post.text and post.url:
                        all_posts.append(post)
                        provenance.track(
                            source_url=video.url,
                            source_name="youtube_api",
                            extraction_method="api",
                            confidence=0.7,
                            collector_agent="social_signals",
                        )

            logger.info(
                "YouTube API: collected %d posts from %d queries",
                len(all_posts), len(queries),
            )
            return all_posts
    except Exception as e:
        logger.warning("YouTube native API failed, trying Monid fallback: %s", e)

    # Strategy 2: Monid YouTube scraper (fallback)
    try:
        from apps.agents.sources.monid import is_available, fetch_youtube_comments
        if not is_available():
            logger.debug(
                "Neither YOUTUBE_API_KEY nor MONID_API_KEY set, "
                "skipping YouTube collection"
            )
            return []

        all_posts = []
        for query in queries:
            items = fetch_youtube_comments(query, max_results=max_per_query, provenance=provenance)
            for item in items:
                post = normalize_youtube_item(item)
                if post.text and post.url:
                    all_posts.append(post)

        logger.info("YouTube/Monid: collected %d posts from %d queries", len(all_posts), len(queries))
        return all_posts
    except Exception as e:
        logger.warning("YouTube/Monid collection failed (non-fatal): %s", e)
        return []


def collect_from_tiktok(
    provenance: ProvenanceTracker,
    queries: Optional[List[str]] = None,
    max_per_query: int = 25,
) -> List[SocialPost]:
    """Collect TikTok videos via Monid API (discovered endpoint).

    Only runs when MONID_API_KEY is set and a suitable TikTok endpoint
    is discovered. If no endpoint exists, logs and returns empty.

    Args:
        provenance: Provenance tracker for recording source attribution.
        queries: Search queries for TikTok discovery.
        max_per_query: Max results per query.

    Returns:
        List of normalized SocialPost items from TikTok. Empty list if
        no TikTok scraper is available.
    """
    try:
        from apps.agents.sources.monid import is_available, discover, run_endpoint
        if not is_available():
            logger.debug("MONID_API_KEY not set, skipping TikTok collection")
            return []

        # Discover available TikTok endpoints
        endpoints = discover("tiktok scraper fintech", limit=3)
        if not endpoints:
            logger.info("No TikTok scraper endpoints found via Monid discover")
            return []

        # Use the first available endpoint
        ep = endpoints[0]
        provider = ep.get("provider", "apify")
        endpoint_path = ep.get("endpoint", "")
        if not endpoint_path:
            logger.warning("TikTok endpoint discovered but no path: %s", ep)
            return []

        logger.info("TikTok: using discovered endpoint %s/%s", provider, endpoint_path)

        if queries is None:
            queries = [
                "AI fintech banking",
                "startup technology LATAM",
            ]

        all_posts: List[SocialPost] = []
        for query in queries:
            result = run_endpoint(
                provider=provider,
                endpoint=endpoint_path,
                input_data={"searchTerms": [query], "maxResults": max_per_query},
            )
            if not result:
                continue

            items = result.get("output", result.get("items", result.get("data", [])))
            if not isinstance(items, list):
                continue

            for item in items:
                text = item.get("text") or item.get("description") or item.get("title") or ""
                url = item.get("webVideoUrl") or item.get("url") or ""
                if not text or not url:
                    continue

                post = SocialPost(
                    text=text[:500],
                    url=url,
                    platform="tiktok",
                    author_handle=item.get("authorMeta", {}).get("name", "") if isinstance(item.get("authorMeta"), dict) else str(item.get("author", "")),
                    author_display_name=item.get("authorMeta", {}).get("nickName", "") if isinstance(item.get("authorMeta"), dict) else "",
                    source_name="monid_tiktok",
                    metrics={
                        "likes": item.get("diggCount", 0) or item.get("likes", 0) or 0,
                        "views": item.get("playCount", 0) or item.get("views", 0) or 0,
                        "shares": item.get("shareCount", 0) or item.get("shares", 0) or 0,
                        "comments": item.get("commentCount", 0) or item.get("comments", 0) or 0,
                    },
                )
                all_posts.append(post)
                if provenance:
                    provenance.track(
                        source_url=url,
                        source_name="monid_tiktok",
                        extraction_method="api",
                    )

        logger.info("TikTok/Monid: collected %d posts from %d queries", len(all_posts), len(queries))
        return all_posts
    except Exception as e:
        logger.warning("TikTok/Monid collection failed (non-fatal): %s", e)
        return []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def collect_all(
    sources: List[DataSourceConfig],
    provenance: ProvenanceTracker,
    agent_name: str = "social_signals",
    run_id: str = "",
    db_session: Optional[Session] = None,
) -> List[SocialPost]:
    """Orchestrate collection from all platform sources and deduplicate.

    Routes each DataSourceConfig to the appropriate platform collector
    based on source name and type, then deduplicates the combined results
    by content_hash (first-seen wins).

    When a db_session is provided, also collects from monitored account
    timelines stored in the database.

    Args:
        sources: All DataSourceConfig items from SOCIAL_SIGNALS_CONFIG.
        provenance: Provenance tracker for the current run.
        agent_name: Agent name for provenance records.
        run_id: Current run ID for provenance records.
        db_session: Optional SQLAlchemy session for monitored account
            collection. If None, account collection is skipped.

    Returns:
        Deduplicated list of SocialPost across all platforms.
    """
    twitter_sources = [s for s in sources if "twitter" in s.name]
    reddit_sources = [s for s in sources if "reddit" in s.name]
    bluesky_sources = [s for s in sources if "bluesky" in s.name]
    rss_sources = [s for s in sources if s.source_type == "rss"]
    scraper_sources = [s for s in sources if s.source_type == "scraper"]

    all_posts: List[SocialPost] = []

    with create_http_client() as client:
        if twitter_sources:
            all_posts.extend(collect_from_twitter(
                twitter_sources, provenance, client, agent_name, run_id,
            ))

        if reddit_sources:
            all_posts.extend(collect_from_reddit(
                reddit_sources, provenance, client, agent_name, run_id,
            ))

        if bluesky_sources:
            all_posts.extend(collect_from_bluesky(
                bluesky_sources, provenance, client, agent_name, run_id,
            ))

        if rss_sources:
            all_posts.extend(collect_from_rss(
                rss_sources, provenance, client, agent_name, run_id,
            ))

        if scraper_sources:
            all_posts.extend(collect_from_web_scraper(
                scraper_sources, provenance, client, agent_name, run_id,
            ))

        # LinkedIn via Monid (paid, cost-aware)
        try:
            linkedin_posts = collect_from_monid_linkedin(provenance)
            all_posts.extend(linkedin_posts)
        except Exception as e:
            logger.warning("LinkedIn/Monid collection failed (non-fatal): %s", e)

        # YouTube via Monid (paid, cost-aware)
        try:
            youtube_posts = collect_from_youtube(provenance)
            all_posts.extend(youtube_posts)
        except Exception as e:
            logger.warning("YouTube/Monid collection failed (non-fatal): %s", e)

        # TikTok via Monid discover (paid, only if endpoint found)
        try:
            tiktok_posts = collect_from_tiktok(provenance)
            all_posts.extend(tiktok_posts)
        except Exception as e:
            logger.warning("TikTok/Monid collection failed (non-fatal): %s", e)

        # Polymarket: prediction market signals (filtered to relevant topics)
        try:
            from apps.agents.sources.polymarket import collect_polymarket_signals
            pm_markets = collect_polymarket_signals(provenance, limit=30)
            pm_added = 0
            for m in pm_markets:
                if not _is_relevant_polymarket(m.title, m.description):
                    continue
                pct = f"{m.outcome_yes*100:.0f}%"
                all_posts.append(SocialPost(
                    text=f"[Polymarket {pct} YES] {m.title}. {m.description[:200]}",
                    url=m.url,
                    platform="polymarket",
                    source_name="polymarket",
                    metrics={"volume_usd": m.volume_usd, "liquidity_usd": m.liquidity_usd, "outcome_yes": m.outcome_yes},
                    content_hash=m.content_hash,
                ))
                pm_added += 1
            logger.info(
                "Polymarket: %d relevant markets out of %d fetched",
                pm_added, len(pm_markets),
            )
        except Exception as e:
            logger.warning("Polymarket collection failed (non-fatal): %s", e)

        # sc-research: social media research via CLI tool
        try:
            from apps.agents.sources.sc_research import collect_from_sc_research, is_available as sc_available
            if sc_available():
                sc_queries = [
                    "AI agents fintech banking",
                    "LLM startup LATAM venture capital",
                    "neobank payments infrastructure",
                ]
                sc_results = collect_from_sc_research(sc_queries, provenance, max_per_query=15)
                for r in sc_results:
                    all_posts.append(SocialPost(
                        text=r.text,
                        url=r.url,
                        platform=r.platform,
                        author_handle=r.author,
                        published_at=None,
                        source_name=f"sc_research_{r.platform}",
                        metrics=r.metrics,
                        content_hash=r.content_hash,
                    ))
                logger.info("sc-research: collected %d posts", len(sc_results))
            else:
                logger.debug("sc-research not installed, skipping")
        except Exception as e:
            logger.warning("sc-research collection failed (non-fatal): %s", e)

        # Monitored account timelines (requires database session)
        if db_session is not None:
            try:
                from apps.agents.social_signals.account_collector import (
                    collect_from_monitored_accounts,
                )
                account_posts = collect_from_monitored_accounts(
                    db_session, provenance, client, agent_name, run_id,
                )
                all_posts.extend(account_posts)
            except Exception as e:
                logger.warning(
                    "Monitored account collection failed (non-fatal): %s", e,
                )

    unique_posts = deduplicate_by_hash(all_posts, hash_fn=lambda p: p.content_hash)

    enabled_count = len([s for s in sources if s.enabled])
    logger.info(
        "Social Signals collected %d unique posts from %d enabled sources "
        "(before dedup: %d, includes monitored accounts)",
        len(unique_posts),
        enabled_count,
        len(all_posts),
    )

    return unique_posts


def collect_from_monid_linkedin(
    provenance: ProvenanceTracker,
    queries: Optional[List[str]] = None,
    max_per_query: int = 10,
) -> List[SocialPost]:
    """Collect LinkedIn posts via Monid API (paid, ~$0.018/post).

    Only runs when MONID_API_KEY is set. Cost-aware: small batches.
    """
    try:
        from apps.agents.sources.monid import is_available, fetch_linkedin_posts
        if not is_available():
            return []

        if queries is None:
            queries = [
                "AI agents fintech banking",
                "startup LATAM venture capital",
            ]

        all_posts: List[SocialPost] = []
        for query in queries:
            items = fetch_linkedin_posts(query, max_results=max_per_query, provenance=provenance)
            for item in items:
                post = SocialPost(
                    text=item.get("text") or item.get("content") or "",
                    url=item.get("url") or item.get("postUrl") or "",
                    platform="linkedin",
                    author_handle=item.get("author", {}).get("handle", "") if isinstance(item.get("author"), dict) else str(item.get("author", "")),
                    author_display_name=item.get("author", {}).get("name", "") if isinstance(item.get("author"), dict) else "",
                    source_name="monid_linkedin",
                    metrics={
                        "likes": item.get("likes", 0),
                        "comments": item.get("comments", 0),
                        "shares": item.get("shares", 0),
                    },
                )
                if post.text and post.url:
                    all_posts.append(post)

        logger.info("Monid LinkedIn: collected %d posts from %d queries", len(all_posts), len(queries))
        return all_posts
    except Exception as e:
        logger.warning("Monid LinkedIn collection failed (non-fatal): %s", e)
        return []
