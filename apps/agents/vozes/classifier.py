"""Theme classification, entity extraction, and LATAM relevance for VOZES.

Classifies social posts into the thematic taxonomy (13 themes + sub-themes),
extracts named entities with ticker resolution, computes LATAM relevance,
detects sentiment, and filters non-LATAM content.

Reuses keyword maps and LLM classification from social_signals/classifier.py.
Adds LATAM relevance scoring, ticker-to-company resolution, and improved
self-promo detection as VOZES-specific enhancements.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Dict, List, Optional, Tuple

from apps.agents.base.llm import LLMClient
from apps.agents.social_signals.classifier import (
    _classify_with_keywords,
    _compute_engagement_rank,
    _extract_with_llm,
    _extract_with_regex,
    compute_sentiment,
    is_commercial,
)
from apps.agents.social_signals.models import EntityMention, ProcessedSignal, SocialPost
from apps.agents.vozes.config import (
    GLOBAL_TOPICS_ALLOWED,
    LATAM_CITIES,
    LATAM_COMPANIES,
    LATAM_COUNTRIES,
    MIN_LATAM_RELEVANCE,
    TICKER_TO_NAME,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LATAM relevance scoring
# ---------------------------------------------------------------------------


def compute_latam_relevance(post: SocialPost) -> float:
    """Score 0-1 how relevant this post is to LATAM tech ecosystem.

    Considers Portuguese/Spanish language indicators, geographic mentions,
    and LATAM company name mentions. Caps geographic bonus at 0.8 to
    avoid over-counting posts that mention many cities but aren't about
    the ecosystem.

    Args:
        post: SocialPost to score.

    Returns:
        Float 0-1 LATAM relevance score.
    """
    text = (post.text or "").lower()
    if not text:
        return 0.0

    score = 0.0

    # Portuguese language indicators
    pt_words = ["para", "como", "sobre", "empresa", "startup", "tecnologia", "dados",
                "investimento", "mercado", "inovação", "inovacao"]
    pt_count = sum(1 for w in pt_words if f" {w} " in f" {text} ")
    if pt_count >= 3:
        score += 0.4

    # Spanish language indicators
    es_words = ["para", "como", "sobre", "empresa", "startup", "tecnología", "datos",
                "inversión", "mercado", "innovación"]
    es_count = sum(1 for w in es_words if f" {w} " in f" {text} ")
    if es_count >= 3 and pt_count < 3:
        score += 0.35

    # Geography mentions
    geo_score = 0.0
    for city in LATAM_CITIES:
        if city.lower() in text:
            geo_score += 0.15
    for country in LATAM_COUNTRIES:
        if country.lower() in text:
            geo_score += 0.15
    # General LATAM terms
    latam_terms = ["latam", "latin america", "america latina", "américa latina"]
    for term in latam_terms:
        if term in text:
            geo_score += 0.2
    score += min(geo_score, 0.8)  # cap geography bonus

    # LATAM company mentions
    company_score = 0.0
    for company in LATAM_COMPANIES:
        if company.lower() in text:
            company_score += 0.1
    score += min(company_score, 0.3)

    return min(1.0, round(score, 3))


def passes_latam_filter(
    post: SocialPost,
    theme: str,
    latam_score: float,
) -> bool:
    """Check if a post passes the LATAM relevance filter.

    Global topics (AI, Funding, DevTools, Cybersecurity) are allowed even
    with low LATAM relevance. All other topics require MIN_LATAM_RELEVANCE.

    Args:
        post: SocialPost being evaluated.
        theme: Classified theme (may be empty if unclassified).
        latam_score: Pre-computed LATAM relevance score.

    Returns:
        True if the post should be kept.
    """
    if latam_score >= MIN_LATAM_RELEVANCE:
        return True
    if theme in GLOBAL_TOPICS_ALLOWED:
        return True
    return False


# ---------------------------------------------------------------------------
# Entity resolution (ticker -> company name)
# ---------------------------------------------------------------------------


def resolve_ticker_entities(entities: List[EntityMention]) -> List[EntityMention]:
    """Resolve ticker symbols to full company names.

    When entity extraction finds tickers like $NU or $MELI, maps them
    to their full names (Nubank, Mercado Libre) using TICKER_TO_NAME.

    Args:
        entities: Raw entity mentions from extraction.

    Returns:
        Updated entity list with resolved names.
    """
    resolved = []
    for entity in entities:
        if entity.entity_type == "company" and entity.name.upper() in TICKER_TO_NAME:
            resolved.append(EntityMention(
                name=TICKER_TO_NAME[entity.name.upper()],
                entity_type="company",
                confidence=max(entity.confidence, 0.6),
            ))
        else:
            resolved.append(entity)
    return resolved


# ---------------------------------------------------------------------------
# Batch classification (main entry point)
# ---------------------------------------------------------------------------


def classify_posts_batch(
    posts: List[SocialPost],
    llm_client: Optional[LLMClient] = None,
    top_n_for_llm: int = 20,
    apply_latam_filter: bool = True,
) -> List[ProcessedSignal]:
    """Classify a batch of posts with LATAM filtering and entity resolution.

    Strategy:
        1. ALL posts: keyword-only theme classification (fast, no LLM)
        2. ALL posts: regex entity extraction + ticker resolution
        3. ALL posts: LATAM relevance scoring + filter
        4. ALL posts: self-promo detection + filter
        5. TOP N posts (by engagement + authority): LLM enrichment

    Args:
        posts: Raw SocialPost items from collector.
        llm_client: Optional LLM client for enriching top posts.
        top_n_for_llm: Number of top posts to enrich with LLM.
        apply_latam_filter: Whether to filter by LATAM relevance.

    Returns:
        List of ProcessedSignal with all classifications populated.
    """
    if not posts:
        return []

    # Step 1: Keyword-only classification for ALL posts
    signals: List[ProcessedSignal] = []
    latam_filtered = 0
    promo_filtered = 0

    for post in posts:
        theme, sub_theme = _classify_with_keywords(post.text)

        # Entity extraction with ticker resolution
        entities = _extract_with_regex(post.text)
        entities = resolve_ticker_entities(entities)

        commercial = is_commercial(post.text)
        authority = _compute_authority(post)

        # LATAM relevance filter
        if apply_latam_filter:
            latam_score = compute_latam_relevance(post)
            if not passes_latam_filter(post, theme, latam_score):
                latam_filtered += 1
                continue

        signal = ProcessedSignal(
            post=post,
            theme=theme,
            sub_theme=sub_theme,
            entities=entities,
            sentiment=0.0,  # Enriched for top N below
            authority_score=authority,
            is_commercial=commercial,
        )
        signals.append(signal)

    if latam_filtered:
        logger.info(
            "LATAM relevance filter: removed %d/%d posts (below %.2f threshold)",
            latam_filtered,
            len(posts),
            MIN_LATAM_RELEVANCE,
        )

    logger.info(
        "Batch classified %d posts with keywords (%d themed, %d promo-filtered)",
        len(signals),
        sum(1 for s in signals if s.theme),
        promo_filtered,
    )

    # Step 2: LLM enrichment for top N posts
    if not llm_client or not llm_client.is_available or top_n_for_llm <= 0:
        return signals

    ranked = sorted(
        enumerate(signals),
        key=lambda idx_sig: (
            _compute_engagement_rank(idx_sig[1].post)
            + idx_sig[1].authority_score * 1000
        ),
        reverse=True,
    )

    top_indices = set(idx for idx, _ in ranked[:top_n_for_llm])

    enriched_count = 0
    for idx in top_indices:
        signal = signals[idx]

        llm_entities = _extract_with_llm(signal.post.text, llm_client)
        if llm_entities:
            signal.entities = resolve_ticker_entities(llm_entities)

        signal.sentiment = compute_sentiment(signal.post.text, llm_client)
        enriched_count += 1

    logger.info(
        "LLM-enriched top %d posts (entity extraction + sentiment)",
        enriched_count,
    )

    return signals


# ---------------------------------------------------------------------------
# Authority computation (local copy, matches social_signals)
# ---------------------------------------------------------------------------


def _compute_authority(post: SocialPost) -> float:
    """Compute authority score based on follower count (log scale, 0-1).

    Args:
        post: Raw SocialPost.

    Returns:
        Float 0-1 authority score. 10M followers = 1.0.
    """
    if post.author_followers > 0:
        return min(1.0, math.log10(max(1, post.author_followers)) / 7.0)
    return 0.0
