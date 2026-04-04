"""Monitored account timeline collector for Social Signals agent.

Reads active accounts from the monitored_accounts table and fetches
recent posts from each account's timeline. Currently supports Twitter;
other platforms can be added as their source connectors gain timeline
support.

Rate-limited to 1 request per second between accounts, with a maximum
of 50 accounts per run. Accounts that fail are skipped (graceful
degradation). last_fetched_at is updated after each successful fetch.

Usage:
    from apps.agents.social_signals.account_collector import collect_from_monitored_accounts

    posts = collect_from_monitored_accounts(db_session, provenance)
"""

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.social_signals.models import SocialPost

logger = logging.getLogger(__name__)

# Rate limiting
SECONDS_BETWEEN_ACCOUNTS = 1.0
MAX_ACCOUNTS_PER_RUN = 50
TWEETS_PER_ACCOUNT = 10


def _normalize_twitter_timeline_post(
    post: "TwitterPost",
    account_handle: str,
    authority_score: float,
) -> SocialPost:
    """Convert a TwitterPost from a monitored account timeline to SocialPost.

    Similar to normalize_twitter_post in collector.py but includes the
    account's authority_score in metrics for downstream scoring.

    Args:
        post: A TwitterPost from fetch_twitter_user_timeline.
        account_handle: The monitored account handle for source attribution.
        authority_score: The account's authority score (0-1).

    Returns:
        SocialPost with platform="twitter" and authority metadata.
    """
    return SocialPost(
        text=post.text,
        url=post.url,
        platform="twitter",
        author_handle=post.author_handle or account_handle,
        author_display_name=post.author_display_name or account_handle,
        author_followers=post.author_followers,
        published_at=post.created_at,
        external_url=post.external_url,
        image_url=post.image_url,
        source_name=f"monitored_account:{account_handle}",
        metrics={
            "likes": post.like_count,
            "replies": post.reply_count,
            "reposts": post.retweet_count,
            "quotes": post.quote_count,
            "impressions": post.impression_count,
            "authority_score": authority_score,
        },
        content_hash=post.content_hash,
    )


def _fetch_twitter_account_timeline(
    client: httpx.Client,
    user_id: str,
    handle: str,
    source_name: str,
    max_results: int = TWEETS_PER_ACCOUNT,
) -> List["TwitterPost"]:
    """Fetch recent tweets from a single Twitter account.

    Wraps fetch_twitter_user_timeline with a synthetic DataSourceConfig
    for the monitored account.

    Args:
        client: Configured httpx.Client.
        user_id: Twitter numeric user ID (stored in metadata).
        handle: Twitter handle for logging.
        source_name: Source name for provenance.
        max_results: Max tweets to fetch per account.

    Returns:
        List of TwitterPost, empty on error.
    """
    from apps.agents.sources.twitter import fetch_twitter_user_timeline

    source = DataSourceConfig(
        name=source_name,
        source_type="api",
        url=f"https://api.twitter.com/2/users/{user_id}/tweets",
        api_key_env="X_BEARER_TOKEN",
    )

    return fetch_twitter_user_timeline(
        source, client, user_id=user_id, max_results=max_results,
    )


def collect_from_monitored_accounts(
    session: Session,
    provenance: ProvenanceTracker,
    client: httpx.Client,
    agent_name: str = "social_signals",
    run_id: str = "",
    max_accounts: int = MAX_ACCOUNTS_PER_RUN,
) -> List[SocialPost]:
    """Collect posts from monitored Twitter accounts.

    Reads active accounts from the monitored_accounts table (platform='twitter'),
    fetches their recent timelines, normalizes to SocialPost, and updates
    last_fetched_at. Accounts are processed oldest-fetched-first to prioritize
    stale data.

    Rate limited to 1 req/s between accounts. Accounts that fail are skipped
    with a warning log; the pipeline continues with remaining accounts.

    Args:
        session: SQLAlchemy database session.
        provenance: Provenance tracker for the current run.
        client: Shared httpx.Client for API requests.
        agent_name: Agent name for provenance records.
        run_id: Current run ID for provenance records.
        max_accounts: Maximum accounts to process per run (default 50).

    Returns:
        List of normalized SocialPost items from monitored account timelines.
    """
    from packages.database.models.monitored_account import MonitoredAccount

    # Query active Twitter accounts, oldest-fetched first
    stmt = (
        select(MonitoredAccount)
        .where(MonitoredAccount.platform == "twitter")
        .where(MonitoredAccount.is_active.is_(True))
        .order_by(MonitoredAccount.last_fetched_at.asc().nullsfirst())
        .limit(max_accounts)
    )

    accounts = session.execute(stmt).scalars().all()

    if not accounts:
        logger.info("No active Twitter monitored accounts found")
        return []

    logger.info(
        "Processing %d monitored Twitter accounts (max %d per run)",
        len(accounts), max_accounts,
    )

    all_posts: List[SocialPost] = []
    fetched_count = 0
    failed_count = 0

    for i, account in enumerate(accounts):
        handle = account.handle
        authority_score = account.authority_score or 0.5

        # Extract Twitter user ID from metadata
        metadata = account.metadata_ or {}
        user_id = metadata.get("twitter_user_id") or metadata.get("user_id")

        if not user_id:
            logger.warning(
                "Monitored account %s has no twitter_user_id in metadata, skipping",
                handle,
            )
            continue

        # Rate limit between accounts (skip delay on first account)
        if i > 0:
            time.sleep(SECONDS_BETWEEN_ACCOUNTS)

        try:
            source_name = f"monitored_account:{handle}"
            twitter_posts = _fetch_twitter_account_timeline(
                client,
                user_id=str(user_id),
                handle=handle,
                source_name=source_name,
            )

            for tp in twitter_posts:
                social_post = _normalize_twitter_timeline_post(
                    tp, handle, authority_score,
                )
                all_posts.append(social_post)
                provenance.track(
                    source_url=tp.url,
                    source_name=source_name,
                    extraction_method="api",
                    confidence=0.7,  # Higher confidence: curated account
                    collector_agent=agent_name,
                    collector_run_id=run_id,
                )

            # Update last_fetched_at on success
            session.execute(
                update(MonitoredAccount)
                .where(MonitoredAccount.id == account.id)
                .values(last_fetched_at=datetime.now(timezone.utc))
            )
            session.commit()
            fetched_count += 1

        except Exception as e:
            logger.warning(
                "Failed to fetch timeline for monitored account %s: %s",
                handle, e,
            )
            failed_count += 1
            # Roll back partial changes for this account, then continue
            session.rollback()
            continue

    logger.info(
        "Monitored accounts: collected %d posts from %d accounts "
        "(%d failed, %d skipped)",
        len(all_posts),
        fetched_count,
        failed_count,
        len(accounts) - fetched_count - failed_count,
    )

    return all_posts
