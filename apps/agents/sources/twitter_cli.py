"""Twitter collection via twitter-cli (cookie-based, no API key needed).

Uses the twitter-cli tool to search and fetch tweets via browser cookies,
bypassing the Twitter API credit limits. Falls back to the official API
if twitter-cli is not installed.

Requires: pip install twitter-cli
Auth: automatic via browser cookies (Chrome/Firefox/Safari)

Usage:
    from apps.agents.sources.twitter_cli import fetch_tweets_cli

    tweets = fetch_tweets_cli(query="AI fintech LATAM", max_results=20)
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Path to twitter-cli binary
TWITTER_CLI = os.environ.get(
    "TWITTER_CLI_PATH",
    "/Users/fabianocruz/Library/Python/3.9/bin/twitter",
)


@dataclass
class CLITweet:
    """A tweet fetched via twitter-cli."""

    id: str
    text: str
    author_handle: str
    author_display_name: str
    url: str
    created_at: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    media_urls: List[str] = field(default_factory=list)
    lang: str = ""


def _parse_tweet(raw: Dict) -> Optional[CLITweet]:
    """Parse a raw JSON tweet from twitter-cli."""
    try:
        author = raw.get("author", {})
        metrics = raw.get("metrics", {})
        tweet_id = raw.get("id", "")
        handle = author.get("screenName", "")

        media_urls = []
        for m in raw.get("media", []):
            if m.get("url"):
                media_urls.append(m["url"])

        return CLITweet(
            id=str(tweet_id),
            text=raw.get("text", ""),
            author_handle=handle,
            author_display_name=author.get("name", ""),
            url=f"https://x.com/{handle}/status/{tweet_id}" if handle else "",
            created_at=raw.get("createdAt"),
            metrics={
                "likes": metrics.get("likes", 0),
                "retweets": metrics.get("retweets", 0),
                "replies": metrics.get("replies", 0),
                "views": metrics.get("views", 0),
                "bookmarks": metrics.get("bookmarks", 0),
            },
            media_urls=media_urls,
            lang=raw.get("lang", ""),
        )
    except Exception as e:
        logger.debug("Failed to parse tweet: %s", e)
        return None


def fetch_tweets_cli(
    query: str,
    max_results: int = 20,
    lang: Optional[str] = None,
    since: Optional[str] = None,
    exclude_retweets: bool = True,
    min_likes: int = 0,
) -> List[CLITweet]:
    """Search tweets using twitter-cli (cookie-based, no API key).

    Args:
        query: Search keywords.
        max_results: Maximum tweets to fetch.
        lang: Language filter (e.g., "en", "pt").
        since: Date filter (YYYY-MM-DD).
        exclude_retweets: Skip retweets.
        min_likes: Minimum likes filter.

    Returns:
        List of CLITweet objects.
    """
    cmd = [TWITTER_CLI, "search", query, "-n", str(max_results), "--json"]

    if lang:
        cmd.extend(["--lang", lang])
    if since:
        cmd.extend(["--since", since])
    if exclude_retweets:
        cmd.extend(["--exclude", "retweets"])
    if min_likes > 0:
        cmd.extend(["--min-likes", str(min_likes)])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.warning("twitter-cli search failed: %s", result.stderr[:200])
            return []

        data = json.loads(result.stdout)
        if not data.get("ok"):
            logger.warning("twitter-cli returned not-ok: %s", result.stdout[:200])
            return []

        raw_tweets = data.get("data", [])
        tweets = []
        for raw in raw_tweets:
            tweet = _parse_tweet(raw)
            if tweet:
                tweets.append(tweet)

        logger.info("twitter-cli: %d tweets for query '%s'", len(tweets), query[:40])
        return tweets

    except FileNotFoundError:
        logger.warning("twitter-cli not installed at %s", TWITTER_CLI)
        return []
    except subprocess.TimeoutExpired:
        logger.warning("twitter-cli search timed out for query '%s'", query[:40])
        return []
    except json.JSONDecodeError:
        logger.warning("twitter-cli returned invalid JSON")
        return []
    except Exception as e:
        logger.error("twitter-cli error: %s", e)
        return []


def fetch_user_tweets_cli(
    handle: str,
    max_results: int = 10,
) -> List[CLITweet]:
    """Fetch recent tweets from a specific user via twitter-cli.

    Args:
        handle: Twitter handle (without @).
        max_results: Max tweets to fetch.

    Returns:
        List of CLITweet objects.
    """
    cmd = [TWITTER_CLI, "tweets", handle, "-n", str(max_results), "--json"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.debug("twitter-cli tweets failed for @%s: %s", handle, result.stderr[:100])
            return []

        data = json.loads(result.stdout)
        raw_tweets = data.get("data", [])
        tweets = [_parse_tweet(raw) for raw in raw_tweets]
        return [t for t in tweets if t is not None]

    except Exception as e:
        logger.debug("twitter-cli user tweets error for @%s: %s", handle, e)
        return []


def is_available() -> bool:
    """Check if twitter-cli is installed and working."""
    try:
        result = subprocess.run(
            [TWITTER_CLI, "--version"], capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False
