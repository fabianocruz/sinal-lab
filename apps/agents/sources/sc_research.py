"""Social Communities Research (sc-research) integration.

Wraps the sc-research CLI tool to fetch social media signals from
Reddit, X/Twitter, LinkedIn, and other platforms. Runs as a subprocess
and parses structured JSON output.

Requires: npm install -g sc-research

Architecture:
    social_signals/collector.py
    └── sc_research.py  <- this module
        └── sc-research CLI (subprocess)
"""

import hashlib
import json
import logging
import subprocess
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


@dataclass
class ScResearchResult:
    """A single result from sc-research."""

    title: str
    url: str
    text: str
    platform: str
    author: str = ""
    published_at: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()


def is_available() -> bool:
    """Check if sc-research CLI is installed."""
    return shutil.which("sc-research") is not None


def research_topic(
    query: str,
    platforms: Optional[List[str]] = None,
    max_results: int = 25,
    timeout: int = 60,
) -> List[ScResearchResult]:
    """Run sc-research to fetch social signals for a topic.

    Args:
        query: Search query (e.g., "AI agents fintech").
        platforms: Optional list of platforms to search (reddit, twitter, linkedin).
        max_results: Maximum results to return.
        timeout: Subprocess timeout in seconds.

    Returns:
        List of ScResearchResult. Empty list on any failure.
    """
    if not is_available():
        logger.warning("sc-research CLI not installed (npm install -g sc-research)")
        return []

    try:
        cmd = [
            "sc-research", "research",
            "--query", query,
            "--format", "json",
            "--max-results", str(max_results),
        ]

        if platforms:
            cmd.extend(["--platforms", ",".join(platforms)])

        logger.info("Running sc-research: %s", " ".join(cmd))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/tmp",
        )

        if result.returncode != 0:
            logger.warning(
                "sc-research exited with code %d: %s",
                result.returncode,
                result.stderr[:200] if result.stderr else "no stderr",
            )
            # Try to parse stdout anyway (some tools output data even on non-zero exit)
            if not result.stdout.strip():
                return []

        return _parse_output(result.stdout, query)

    except subprocess.TimeoutExpired:
        logger.warning("sc-research timed out after %ds for query: %s", timeout, query)
        return []
    except FileNotFoundError:
        logger.warning("sc-research binary not found")
        return []
    except Exception as e:
        logger.warning("sc-research unexpected error: %s", e)
        return []


def _parse_output(stdout: str, query: str) -> List[ScResearchResult]:
    """Parse sc-research JSON output into ScResearchResult list."""
    results = []

    # Try parsing as JSON array or JSON lines
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("results", data.get("items", data.get("data", [data])))
        else:
            return []
    except json.JSONDecodeError:
        # Try JSON lines
        items = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    for item in items:
        if not isinstance(item, dict):
            continue

        url = item.get("url") or item.get("link") or item.get("permalink") or ""
        if not url:
            continue

        text = item.get("text") or item.get("content") or item.get("body") or item.get("title") or ""
        title = item.get("title") or text[:100]
        platform = _detect_platform(url, item)
        author = item.get("author") or item.get("username") or item.get("user") or ""
        published = item.get("published_at") or item.get("created_at") or item.get("date") or None

        metrics = {}
        for key in ["likes", "upvotes", "score", "comments", "replies", "retweets", "shares", "views"]:
            if key in item and item[key] is not None:
                try:
                    metrics[key] = int(item[key])
                except (ValueError, TypeError):
                    pass

        results.append(ScResearchResult(
            title=title,
            url=url,
            text=text,
            platform=platform,
            author=str(author),
            published_at=published,
            metrics=metrics,
        ))

    logger.info("sc-research parsed %d results for query '%s'", len(results), query)
    return results


def _detect_platform(url: str, item: dict) -> str:
    """Detect platform from URL or item metadata."""
    platform = item.get("platform") or item.get("source") or ""
    if platform:
        return platform.lower()

    url_lower = url.lower()
    if "reddit.com" in url_lower:
        return "reddit"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    elif "linkedin.com" in url_lower:
        return "linkedin"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    elif "facebook.com" in url_lower:
        return "facebook"
    elif "bsky.app" in url_lower:
        return "bluesky"
    elif "news.ycombinator.com" in url_lower:
        return "hackernews"
    else:
        return "web"


def collect_from_sc_research(
    queries: List[str],
    provenance: ProvenanceTracker,
    platforms: Optional[List[str]] = None,
    max_per_query: int = 25,
) -> List[ScResearchResult]:
    """Collect social signals using sc-research for multiple queries.

    Args:
        queries: List of search queries.
        provenance: Provenance tracker.
        platforms: Optional platform filter.
        max_per_query: Max results per query.

    Returns:
        Combined list of results from all queries.
    """
    if not is_available():
        logger.info("sc-research not available, skipping")
        return []

    all_results: List[ScResearchResult] = []
    seen_hashes = set()

    for query in queries:
        results = research_topic(query, platforms=platforms, max_results=max_per_query)

        for r in results:
            if r.content_hash in seen_hashes:
                continue
            seen_hashes.add(r.content_hash)
            all_results.append(r)

            provenance.track(
                source_url=r.url,
                source_name=f"sc_research_{r.platform}",
                extraction_method="api",
            )

    logger.info("sc-research: collected %d unique results from %d queries", len(all_results), len(queries))
    return all_results
