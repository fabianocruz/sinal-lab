"""Reddit collection via public JSON API (no auth needed).

Fetches posts from subreddit /hot.json endpoints. No API key,
no OAuth, no rate limit issues. Just needs a User-Agent header.

Usage:
    from apps.agents.sources.reddit_json import fetch_subreddit_posts
    posts = fetch_subreddit_posts("fintech", limit=25)
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "fintech",
    "MachineLearning",
    "artificial",
    "startups",
    "CryptoCurrency",
    "banking",
    "venturecapital",
    "SaaS",
]

# Reddit blocks generic bot UAs. Rotate browser-like UAs to avoid 403.
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
]


def _get_ua() -> str:
    return random.choice(_USER_AGENTS)


def _reddit_get(url: str, params: dict, max_retries: int = 2) -> Optional[dict]:
    """GET from Reddit JSON API with UA rotation and retry on 403/429."""
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                r = client.get(
                    url,
                    params=params,
                    headers={"User-Agent": _get_ua()},
                )
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (403, 429) and attempt < max_retries:
                    wait = 2 ** attempt + random.random()
                    logger.debug("Reddit %d, retrying in %.1fs (attempt %d)", r.status_code, wait, attempt + 1)
                    time.sleep(wait)
                    continue
                if r.status_code == 403:
                    logger.warning("Reddit blocked %s after %d attempts", url[:60], max_retries + 1)
                    return None
                r.raise_for_status()
                return r.json()
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            logger.warning("Reddit fetch failed %s: %s", url[:60], e)
            return None
    return None


@dataclass
class RedditPost:
    """A post from Reddit."""

    id: str
    title: str
    text: str
    url: str
    author: str
    subreddit: str
    score: int = 0
    num_comments: int = 0
    created_utc: float = 0
    permalink: str = ""


def fetch_subreddit_posts(
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
) -> List[RedditPost]:
    """Fetch posts from a subreddit via public JSON API.

    Args:
        subreddit: Subreddit name (without r/).
        sort: hot, new, top, rising.
        limit: Max posts (max 100).

    Returns:
        List of RedditPost objects.
    """
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    data = _reddit_get(url, {"limit": min(limit, 100)})
    if not data:
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        if d.get("stickied"):
            continue

        selftext = (d.get("selftext") or "")[:500]
        title = d.get("title", "")

        posts.append(RedditPost(
            id=d.get("id", ""),
            title=title,
            text=f"{title}. {selftext}".strip() if selftext else title,
            url=d.get("url", ""),
            author=d.get("author", ""),
            subreddit=subreddit,
            score=d.get("score", 0),
            num_comments=d.get("num_comments", 0),
            created_utc=d.get("created_utc", 0),
            permalink=f"https://www.reddit.com{d.get('permalink', '')}",
        ))

    logger.info("Reddit r/%s: %d posts", subreddit, len(posts))
    return posts


def search_reddit(
    query: str,
    sort: str = "relevance",
    time_filter: str = "week",
    limit: int = 25,
) -> List[RedditPost]:
    """Search Reddit across all subreddits via public JSON API.

    Args:
        query: Search query string.
        sort: relevance, hot, top, new, comments.
        time_filter: hour, day, week, month, year, all.
        limit: Max results (max 100).

    Returns:
        List of RedditPost objects matching the search.
    """
    url = "https://www.reddit.com/search.json"
    data = _reddit_get(url, {
        "q": query,
        "sort": sort,
        "t": time_filter,
        "limit": min(limit, 100),
    })
    if not data:
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        if d.get("stickied"):
            continue

        selftext = (d.get("selftext") or "")[:500]
        title = d.get("title", "")

        posts.append(RedditPost(
            id=d.get("id", ""),
            title=title,
            text=f"{title}. {selftext}".strip() if selftext else title,
            url=d.get("url", ""),
            author=d.get("author", ""),
            subreddit=d.get("subreddit", ""),
            score=d.get("score", 0),
            num_comments=d.get("num_comments", 0),
            created_utc=d.get("created_utc", 0),
            permalink=f"https://www.reddit.com{d.get('permalink', '')}",
        ))

    logger.info("Reddit search '%s': %d posts", query[:30], len(posts))
    return posts


def fetch_top_comments(
    permalink: str,
    limit: int = 5,
) -> List[str]:
    """Fetch top-level comments for a Reddit post.

    Args:
        permalink: Reddit post permalink (e.g. /r/fintech/comments/abc123/...).
        limit: Max comments to return.

    Returns:
        List of comment body strings.
    """
    url = f"https://www.reddit.com{permalink}.json"
    data = _reddit_get(url, {"limit": limit, "sort": "top"})

    if not data or not isinstance(data, list) or len(data) < 2:
        return []

    comments = []
    for child in data[1].get("data", {}).get("children", []):
        body = child.get("data", {}).get("body", "")
        if body and len(body) > 20:
            comments.append(body[:300])
        if len(comments) >= limit:
            break

    return comments


# Default search queries for signal discovery
SEARCH_QUERIES = [
    "AI agents fintech",
    "LLM startup funding",
    "neobank LATAM payments",
    "AI compliance banking",
    "open source AI tools",
]


def fetch_all_subreddits(
    subreddits: Optional[List[str]] = None,
    limit_per_sub: int = 15,
) -> List[RedditPost]:
    """Fetch from all configured subreddits + search queries.

    Combines hot posts from curated subreddits with cross-Reddit
    search results for broader signal discovery.

    Args:
        subreddits: Override list. Defaults to SUBREDDITS.
        limit_per_sub: Max posts per subreddit.

    Returns:
        Combined list of posts (deduplicated by id).
    """
    subs = subreddits or SUBREDDITS
    all_posts: List[RedditPost] = []
    seen_ids: set = set()

    # Hot posts from curated subreddits (with delay to avoid rate limit)
    for sub in subs:
        posts = fetch_subreddit_posts(sub, limit=limit_per_sub)
        for p in posts:
            if p.id not in seen_ids:
                all_posts.append(p)
                seen_ids.add(p.id)
        time.sleep(1)  # Respect Reddit rate limits

    # Cross-Reddit search for broader discovery
    for query in SEARCH_QUERIES:
        search_posts = search_reddit(query, limit=15)
        for p in search_posts:
            if p.id not in seen_ids:
                all_posts.append(p)
                seen_ids.add(p.id)
        time.sleep(1)

    # Enrich top posts with comments for richer text
    top_posts = sorted(all_posts, key=lambda p: p.score, reverse=True)
    enriched = 0
    for post in top_posts[:10]:
        if post.permalink and post.num_comments > 5:
            comments = fetch_top_comments(
                post.permalink.replace("https://www.reddit.com", ""),
                limit=3,
            )
            if comments:
                post.text = f"{post.text}\n\nTop comments:\n" + "\n---\n".join(comments)
                enriched += 1

    logger.info(
        "Reddit total: %d posts from %d subreddits + %d search queries (%d enriched with comments)",
        len(all_posts), len(subs), len(SEARCH_QUERIES), enriched,
    )
    return all_posts
