"""Relevance scoring for SINTESE agent.

Scores collected feed items by relevance to the Sinal.lab audience
(technical founders, CTOs, senior engineers in LATAM). Considers:
- Topic relevance (AI, startups, funding, infrastructure, etc.)
- Recency (prefer items from the last 7 days)
- Source authority (established sources score higher)
- LATAM relevance (Portuguese content, LATAM keywords)
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from apps.agents.sintese.collector import FeedItem
from packages.editorial.guidelines import EDITORIAL_TERRITORIES

logger = logging.getLogger(__name__)

# Topic keywords with relevance weights (higher = more relevant)
TOPIC_KEYWORDS: dict[str, float] = {
    # AI & ML (high relevance)
    "inteligencia artificial": 1.0, "machine learning": 0.9, "llm": 0.9,
    "gpt": 0.8, "claude": 0.8, "deep learning": 0.8, "ai agent": 0.9,
    "generative ai": 0.9, "ia generativa": 1.0, "nlp": 0.7,

    # Startups & VC (high relevance)
    "startup": 0.9, "venture capital": 0.9, "investimento": 0.8,
    "funding": 0.8, "serie a": 0.9, "serie b": 0.9,
    "seed": 0.7, "pre-seed": 0.7, "unicornio": 0.9, "ipo": 0.8,
    "aquisicao": 0.8, "acquisition": 0.7, "fundraising": 0.8,

    # LATAM fintech (topic-specific — pure geographic terms like "brasil",
    # "sao paulo" are handled by score_latam_relevance, NOT here)
    "latam": 0.9, "america latina": 0.9, "fintech brasil": 1.0,
    "pix": 0.8, "open finance": 0.8, "drex": 0.8, "nubank": 0.7,

    # Tech infrastructure (medium relevance)
    "kubernetes": 0.6, "docker": 0.5, "aws": 0.5, "cloud": 0.5,
    "microservices": 0.5, "devops": 0.5, "open source": 0.6,
    "api": 0.4, "database": 0.4, "python": 0.5, "typescript": 0.5,
    "react": 0.4, "next.js": 0.5, "fastapi": 0.5, "rust": 0.5,

    # Fintech (medium-high relevance)
    "fintech": 0.8, "pagamento": 0.6, "credito": 0.6, "banco digital": 0.7,
    "blockchain": 0.5, "crypto": 0.4, "defi": 0.4,

    # Verticals (medium relevance)
    "healthtech": 0.6, "edtech": 0.6, "agritech": 0.7, "agtech": 0.7,
    "proptech": 0.5, "legaltech": 0.5, "climate tech": 0.7,
    "saas": 0.6, "b2b": 0.5, "marketplace": 0.5,
}

# Source authority scores (0-1, higher = more established/reliable)
SOURCE_AUTHORITY: dict[str, float] = {
    # Global Tech
    "techcrunch": 0.9, "techcrunch_latam": 0.95,
    "arstechnica": 0.85, "theverge": 0.8,
    "mit_tech_review": 0.9,
    "restofworld": 0.9,
    "hackernews_best": 0.8, "lobsters": 0.7,
    # LATAM Startup & VC
    "startse": 0.85, "neofeed": 0.85,
    "contxto": 0.85, "distrito": 0.8,
    "pipeline_valor": 0.85,
    "startupi": 0.7, "abstartups": 0.7,
    "latamlist": 0.75, "blocknews": 0.70,
    # Brazilian Tech Media
    "convergenciadigital": 0.65, "baguete": 0.60,
    "infomoney": 0.55,  # lowered — too much general finance noise
    # AI & ML
    "theaibeat": 0.80, "deeplearning_ai": 0.85,
    # Developer & Infrastructure
    "github_blog": 0.8, "vercel_blog": 0.7,
    "netlify_blog": 0.65, "cloudflare_blog": 0.75,
    "devto": 0.55,
    # Fintech
    "fintechfutures": 0.75,
    # Newsletters
    "tldrnewsletter": 0.70, "bytebytego": 0.75,
}

DEFAULT_SOURCE_AUTHORITY = 0.5

# Minimum topic relevance to be considered for the newsletter.
# Items below this threshold are filtered out regardless of recency,
# authority, or LATAM score. Prevents non-editorial content (cars,
# consumer gadgets, sports, lifestyle) from appearing.
MIN_TOPIC_SCORE = 0.10

# Cache for compiled regex patterns used by _keyword_in_text
_KEYWORD_RE_CACHE: dict[str, re.Pattern] = {}


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Check if keyword appears as whole word(s) in text.

    Uses regex word boundaries to prevent false positives from
    substring matches (e.g., "ai" matching in "custaria",
    "inter" matching in "internet", "api" matching in "capital").
    """
    pattern = _KEYWORD_RE_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
        _KEYWORD_RE_CACHE[keyword] = pattern
    return bool(pattern.search(text))


def _build_editorial_keyword_set() -> set[str]:
    """Extract all keywords from editorial territories as a flat set.

    These keywords supplement TOPIC_KEYWORDS to ensure items that match
    editorial guidelines are scored even if they don't match the scorer's
    own keyword list.
    """
    keywords: set[str] = set()
    for territory in EDITORIAL_TERRITORIES.values():
        for kw in territory.get("keywords", []):
            keywords.add(kw.lower())
    return keywords


EDITORIAL_KEYWORD_SET: set[str] = _build_editorial_keyword_set()


def score_topic_relevance(item: FeedItem) -> float:
    """Score an item's topic relevance based on keyword matching.

    Searches title, summary, and tags against two keyword sources:
    1. TOPIC_KEYWORDS — scorer's own weighted keywords
    2. EDITORIAL_KEYWORD_SET — keywords from editorial territories

    Items must match at least one keyword from either source to receive
    a non-zero score. This prevents non-editorial content (consumer
    gadgets, sports, cars, lifestyle) from entering the newsletter.

    Returns 0.0-1.0.
    """
    text = " ".join([
        item.title.lower(),
        (item.summary or "").lower(),
        " ".join(item.tags),
    ])

    max_score = 0.0
    match_count = 0

    # Check scorer's own weighted keywords (word-boundary matching
    # prevents "ai" matching in "custaria", "api" in "capital", etc.)
    for keyword, weight in TOPIC_KEYWORDS.items():
        if _keyword_in_text(keyword, text):
            max_score = max(max_score, weight)
            match_count += 1

    # Check editorial territory keywords (flat weight 0.5 for matches
    # not already covered by TOPIC_KEYWORDS)
    editorial_matches = sum(1 for kw in EDITORIAL_KEYWORD_SET if _keyword_in_text(kw, text))
    if editorial_matches > 0 and max_score == 0.0:
        # Item matches editorial guidelines but not scorer keywords —
        # give it a baseline score so it's not filtered out
        max_score = 0.5
    match_count += editorial_matches

    # Bonus for multiple keyword matches (capped)
    multi_match_bonus = min(match_count * 0.02, 0.1)

    return min(max_score + multi_match_bonus, 1.0)


def score_recency(item: FeedItem, reference_time: Optional[datetime] = None) -> float:
    """Score an item's recency. Prefers items from the last 7 days.

    Returns 1.0 for items published today, decaying to 0.1 for items
    older than 14 days.
    """
    if not item.published_at:
        return 0.3  # Unknown date gets a neutral score

    now = reference_time or datetime.now(timezone.utc)
    age = now - item.published_at

    if age.days < 0:
        return 0.9  # Future dates (timezone issues) treated as recent

    if age.days <= 1:
        return 1.0
    elif age.days <= 3:
        return 0.9
    elif age.days <= 7:
        return 0.7
    elif age.days <= 14:
        return 0.4
    else:
        return 0.1


def score_source_authority(item: FeedItem) -> float:
    """Score based on the source's established authority."""
    return SOURCE_AUTHORITY.get(item.source_name, DEFAULT_SOURCE_AUTHORITY)


def score_latam_relevance(item: FeedItem) -> float:
    """Score how relevant this item is to the LATAM tech ecosystem.

    Higher scores for Portuguese content, LATAM-specific topics,
    and mentions of LATAM companies/cities.
    """
    text = " ".join([
        item.title.lower(),
        (item.summary or "").lower(),
    ])

    score = 0.0

    # Portuguese language signals
    pt_signals = [
        "de", "para", "com", "que", "em", "por", "uma", "dos", "das",
        "nao", "mais", "como", "sobre", "tecnologia", "empresa",
    ]
    pt_matches = sum(1 for word in pt_signals if f" {word} " in f" {text} ")
    if pt_matches >= 3:
        score += 0.4  # Likely Portuguese content

    # LATAM location mentions
    latam_locations = [
        "brasil", "brazil", "sao paulo", "rio de janeiro", "florianopolis",
        "recife", "belo horizonte", "curitiba", "porto alegre", "campinas",
        "mexico", "buenos aires", "bogota", "santiago", "lima", "medellin",
        "latam", "america latina", "latin america", "south america",
    ]
    location_matches = sum(1 for loc in latam_locations if _keyword_in_text(loc, text))
    score += min(location_matches * 0.15, 0.4)

    # LATAM company mentions
    latam_companies = [
        "nubank", "mercadolibre", "mercado livre", "rappi", "ifood",
        "creditas", "loft", "vtex", "stone", "pagseguro", "totvs",
        "magazineluiza", "inter", "neon", "c6bank", "kavak",
    ]
    company_matches = sum(1 for c in latam_companies if _keyword_in_text(c, text))
    score += min(company_matches * 0.1, 0.3)

    return min(score, 1.0)


@dataclass
class ScoredItem:
    """A feed item with computed relevance scores."""

    item: FeedItem
    topic_score: float
    recency_score: float
    authority_score: float
    latam_score: float

    @property
    def composite_score(self) -> float:
        """Weighted composite relevance score.

        Weights: topic 35%, recency 25%, authority 15%, LATAM 25%
        """
        return round(
            self.topic_score * 0.35
            + self.recency_score * 0.25
            + self.authority_score * 0.15
            + self.latam_score * 0.25,
            4,
        )


def score_items(
    items: list[FeedItem],
    reference_time: Optional[datetime] = None,
    min_topic_score: float = MIN_TOPIC_SCORE,
) -> list[ScoredItem]:
    """Score all collected items and return them sorted by composite score.

    Items with topic_score below min_topic_score are filtered out. This
    prevents content with zero editorial relevance (consumer gadgets,
    sports, cars, lifestyle) from entering the newsletter even if they
    score high on recency or LATAM signals.

    Args:
        items: List of collected FeedItems.
        reference_time: Optional reference time for recency scoring (defaults to now).
        min_topic_score: Minimum topic relevance to include (default MIN_TOPIC_SCORE).

    Returns:
        List of ScoredItems sorted by composite_score descending,
        filtered by min_topic_score.
    """
    scored: list[ScoredItem] = []
    filtered_count = 0

    for item in items:
        topic = score_topic_relevance(item)

        if topic < min_topic_score:
            filtered_count += 1
            continue

        scored_item = ScoredItem(
            item=item,
            topic_score=topic,
            recency_score=score_recency(item, reference_time),
            authority_score=score_source_authority(item),
            latam_score=score_latam_relevance(item),
        )
        scored.append(scored_item)

    if filtered_count > 0:
        logger.info(
            "Filtered %d/%d items below min_topic_score=%.2f",
            filtered_count, len(items), min_topic_score,
        )

    scored.sort(key=lambda x: x.composite_score, reverse=True)

    return scored
