"""Relevance scoring for SINTESE agent.

Scores collected feed items by relevance to the Sinal.lab audience
(technical founders, CTOs, senior engineers in LATAM). Considers:
- Topic relevance (AI, startups, funding, infrastructure, etc.)
- Recency (prefer items from the last 7 days)
- Source authority (established sources score higher)
- LATAM relevance (Portuguese content, LATAM keywords)
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from apps.agents.sintese.collector import FeedItem

# Topic keywords with relevance weights (higher = more relevant)
TOPIC_KEYWORDS: dict[str, float] = {
    # AI & ML (high relevance)
    "inteligencia artificial": 1.0, "machine learning": 0.9, "llm": 0.9,
    "gpt": 0.8, "claude": 0.8, "deep learning": 0.8, "ai agent": 0.9,
    "generative ai": 0.9, "ia generativa": 1.0, "nlp": 0.7,

    # Startups & VC (high relevance)
    "startup": 0.9, "venture capital": 0.9, "investimento": 0.8,
    "rodada": 0.9, "funding": 0.8, "serie a": 0.9, "serie b": 0.9,
    "seed": 0.7, "pre-seed": 0.7, "unicornio": 0.9, "ipo": 0.8,
    "aquisicao": 0.8, "acquisition": 0.7, "fundraising": 0.8,

    # LATAM specific (high relevance)
    "brasil": 0.8, "brazil": 0.7, "latam": 0.9, "america latina": 0.9,
    "sao paulo": 0.7, "florianopolis": 0.7, "fintech brasil": 1.0,
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
    "techcrunch": 0.9, "techcrunch_latam": 0.95,
    "arstechnica": 0.85, "theverge": 0.8,
    "mit_tech_review": 0.9,
    "restofworld": 0.9,
    "hackernews_best": 0.8, "lobsters": 0.7,
    "startse": 0.85, "neofeed": 0.85,
    "contxto": 0.85, "distrito": 0.8,
    "infomoney": 0.8, "pipeline_valor": 0.85,
    "github_blog": 0.8, "vercel_blog": 0.7,
    "startupi": 0.7, "abstartups": 0.7,
    "latamlist": 0.75,
}

DEFAULT_SOURCE_AUTHORITY = 0.5


def score_topic_relevance(item: FeedItem) -> float:
    """Score an item's topic relevance based on keyword matching.

    Searches title, summary, and tags for known topic keywords.
    Returns 0.0-1.0.
    """
    text = " ".join([
        item.title.lower(),
        (item.summary or "").lower(),
        " ".join(item.tags),
    ])

    max_score = 0.0
    match_count = 0

    for keyword, weight in TOPIC_KEYWORDS.items():
        if keyword in text:
            max_score = max(max_score, weight)
            match_count += 1

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
    location_matches = sum(1 for loc in latam_locations if loc in text)
    score += min(location_matches * 0.15, 0.4)

    # LATAM company mentions
    latam_companies = [
        "nubank", "mercadolibre", "mercado livre", "rappi", "ifood",
        "creditas", "loft", "vtex", "stone", "pagseguro", "totvs",
        "magazineluiza", "inter", "neon", "c6bank", "kavak",
    ]
    company_matches = sum(1 for c in latam_companies if c in text)
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
) -> list[ScoredItem]:
    """Score all collected items and return them sorted by composite score.

    Args:
        items: List of collected FeedItems.
        reference_time: Optional reference time for recency scoring (defaults to now).

    Returns:
        List of ScoredItems sorted by composite_score descending.
    """
    scored: list[ScoredItem] = []

    for item in items:
        scored_item = ScoredItem(
            item=item,
            topic_score=score_topic_relevance(item),
            recency_score=score_recency(item, reference_time),
            authority_score=score_source_authority(item),
            latam_score=score_latam_relevance(item),
        )
        scored.append(scored_item)

    scored.sort(key=lambda x: x.composite_score, reverse=True)

    return scored
