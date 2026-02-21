"""Shared ProductHunt GraphQL source for agent collectors.

Fetches top posts from the ProductHunt GraphQL API v2 using a
developer token for authentication.

Falls back gracefully (returns []) when the token is missing, the API
returns an error, or the response is malformed.

Usage:
    from apps.agents.sources.producthunt import fetch_producthunt_posts

    posts = fetch_producthunt_posts(source_config, client, limit=20)
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

PRODUCTHUNT_API_URL = "https://api.producthunt.com/v2/api/graphql"

POSTS_QUERY = """\
query GetPosts($limit: Int, $postedAfter: DateTime) {
  posts(first: $limit, postedAfter: $postedAfter, order: VOTES) {
    edges {
      node {
        id
        name
        tagline
        url
        website
        description
        votesCount
        commentsCount
        createdAt
        topics {
          edges {
            node {
              name
            }
          }
        }
        makers {
          name
        }
        thumbnail {
          url
        }
      }
    }
  }
}
"""


@dataclass
class ProductHuntPost:
    """A single ProductHunt post from the GraphQL API.

    Cross-source dedup: hashes the website URL when present so the same
    product discovered via HN, GitHub, *and* ProductHunt is recognised
    as one item.  Falls back to the ProductHunt post URL when no
    website link exists.
    """

    name: str
    tagline: str
    url: str
    source_name: str
    website: Optional[str] = None
    description: Optional[str] = None
    votes_count: int = 0
    comments_count: int = 0
    created_at: Optional[datetime] = None
    topics: List[str] = field(default_factory=list)
    makers: List[str] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            hash_key = self.website if self.website else self.url
            self.content_hash = hashlib.md5(hash_key.encode()).hexdigest()


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string into a timezone-aware datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _extract_topics(topics_data: Optional[Dict[str, Any]]) -> List[str]:
    """Extract topic names from Relay-style edges/node structure."""
    if not topics_data:
        return []
    edges = topics_data.get("edges", [])
    return [
        edge["node"]["name"]
        for edge in edges
        if edge.get("node", {}).get("name")
    ]


def _extract_makers(makers_data: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Extract maker names from the makers list."""
    if not makers_data:
        return []
    return [
        maker["name"]
        for maker in makers_data
        if maker.get("name")
    ]


def _extract_thumbnail_url(
    thumbnail_data: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Extract thumbnail URL from the thumbnail object."""
    if not thumbnail_data:
        return None
    return thumbnail_data.get("url")


def fetch_producthunt_posts(
    source: DataSourceConfig,
    client: httpx.Client,
    limit: int = 20,
    posted_after: Optional[str] = None,
) -> List[ProductHuntPost]:
    """Fetch top posts from the ProductHunt GraphQL API.

    Args:
        source: DataSourceConfig with endpoint URL and provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        limit: Maximum number of posts to fetch (default 20).
        posted_after: ISO date string to filter posts after (e.g. "2026-02-10").

    Returns:
        List of ProductHuntPost. Empty list when the token is missing,
        on HTTP/timeout errors, or when the response is malformed.
    """
    token = os.getenv("PRODUCTHUNT_TOKEN")
    if not token:
        logger.warning(
            "PRODUCTHUNT_TOKEN not set, skipping ProductHunt posts for %s",
            source.name,
        )
        return []

    headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    variables: Dict[str, Any] = {"limit": limit}
    if posted_after:
        variables["postedAfter"] = posted_after

    json_body: Dict[str, Any] = {
        "query": POSTS_QUERY,
        "variables": variables,
    }

    try:
        response = client.post(
            PRODUCTHUNT_API_URL,
            headers=headers,
            json=json_body,
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(
            "ProductHunt API error for %s: %s", source.name, exc
        )
        return []

    try:
        data = response.json()
    except Exception as exc:
        logger.warning(
            "ProductHunt JSON decode error for %s: %s", source.name, exc
        )
        return []

    try:
        edges = data["data"]["posts"]["edges"]
    except (KeyError, TypeError) as exc:
        logger.warning(
            "ProductHunt malformed response for %s: %s", source.name, exc
        )
        return []

    posts: List[ProductHuntPost] = []
    for edge in edges:
        node = edge.get("node", {})

        # name and tagline are required fields
        name = node.get("name")
        tagline = node.get("tagline")
        url = node.get("url")

        if not name or not tagline or not url:
            logger.debug(
                "Skipping ProductHunt post with missing required fields"
            )
            continue

        posts.append(
            ProductHuntPost(
                name=name,
                tagline=tagline,
                url=url,
                source_name=source.name,
                website=node.get("website"),
                description=node.get("description"),
                votes_count=node.get("votesCount", 0),
                comments_count=node.get("commentsCount", 0),
                created_at=_parse_timestamp(node.get("createdAt")),
                topics=_extract_topics(node.get("topics")),
                makers=_extract_makers(node.get("makers")),
                thumbnail_url=_extract_thumbnail_url(node.get("thumbnail")),
            )
        )

    logger.info(
        "Fetched %d ProductHunt posts from %s", len(posts), source.name
    )
    return posts
