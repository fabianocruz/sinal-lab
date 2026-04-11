"""Reddit collection via public JSON API (no auth needed).

Fetches posts from subreddit /hot.json endpoints. No API key,
no OAuth, no rate limit issues. Just needs a User-Agent header.

Usage:
    from apps.agents.sources.reddit_json import fetch_subreddit_posts
    posts = fetch_subreddit_posts("fintech", limit=25)
"""

import logging
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

USER_AGENT = "SinalBot/1.0 (intelligence platform; contact@sinal.tech)"


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

    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            r = client.get(
                url,
                params={"limit": min(limit, 100)},
                headers={"User-Agent": USER_AGENT},
            )
            if r.status_code == 403:
                logger.warning("Reddit blocked r/%s (403)", subreddit)
                return []
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Reddit r/%s fetch failed: %s", subreddit, e)
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


def fetch_all_subreddits(
    subreddits: Optional[List[str]] = None,
    limit_per_sub: int = 15,
) -> List[RedditPost]:
    """Fetch from all configured subreddits.

    Args:
        subreddits: Override list. Defaults to SUBREDDITS.
        limit_per_sub: Max posts per subreddit.

    Returns:
        Combined list of posts.
    """
    subs = subreddits or SUBREDDITS
    all_posts = []

    for sub in subs:
        posts = fetch_subreddit_posts(sub, limit=limit_per_sub)
        all_posts.extend(posts)

    logger.info("Reddit total: %d posts from %d subreddits", len(all_posts), len(subs))
    return all_posts
