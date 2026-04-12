"""Reddit collection via public JSON API (no auth needed).

Fetches posts from subreddit /hot.json endpoints. No API key,
no OAuth, no rate limit issues. Just needs a User-Agent header.

Usage:
    from apps.agents.sources.reddit_json import fetch_subreddit_posts
    posts = fetch_subreddit_posts("fintech", limit=25)
"""

import json
import logging
import random
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlencode

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

# Reddit blocks Python HTTP clients (httpx, requests) by TLS fingerprint.
# Using curl subprocess bypasses this — curl's TLS handshake is accepted.
_CURL_BIN = shutil.which("curl") or "curl"

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


def _reddit_get(url: str, params: dict) -> Optional[dict]:
    """GET from Reddit JSON API using curl to bypass TLS fingerprinting."""
    qs = urlencode(params)
    full_url = f"{url}?{qs}" if qs else url
    ua = random.choice(_USER_AGENTS)

    try:
        result = subprocess.run(
            [_CURL_BIN, "-s", "-H", f"User-Agent: {ua}", full_url],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            logger.warning("Reddit curl failed for %s (exit %d)", url[:60], result.returncode)
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("Reddit curl timed out for %s", url[:60])
        return None
    except json.JSONDecodeError:
        logger.warning("Reddit returned non-JSON for %s", url[:60])
        return None
    except Exception as e:
        logger.warning("Reddit fetch failed %s: %s", url[:60], e)
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
