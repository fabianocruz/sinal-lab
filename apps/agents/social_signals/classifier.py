"""Theme classification and entity extraction for social signals.

Classifies social posts into the thematic taxonomy (AI, Fintech, AI in Banking)
and extracts named entities (companies, people, products, technologies).

The batch classifier (classify_posts_batch) is the primary entry point:
it uses fast keyword-only classification for all posts, then enriches
only the top N posts (by engagement/authority) with LLM-powered entity
extraction and sentiment analysis. This avoids 274+ LLM calls per run.

Individual LLM functions (classify_theme, extract_entities, compute_sentiment)
are preserved for cases where per-post LLM processing is explicitly needed.
"""

import logging
import math
import re
from typing import Dict, List, Optional, Tuple

from apps.agents.base.llm import LLMClient
from apps.agents.social_signals.config import SIGNAL_TAXONOMY
from apps.agents.social_signals.models import EntityMention, ProcessedSignal, SocialPost

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword maps for fallback classification (when LLM is unavailable)
# ---------------------------------------------------------------------------

_THEME_KEYWORDS: Dict[str, List[str]] = {
    "AI in Banking": [
        "banking ai", "bank ai", "compliance ai", "kyc auto", "aml",
        "underwriting", "credit scoring", "fraud detection", "core banking",
        "model risk", "regtech", "insurtech", "anti-money",
    ],
    "Fintech": [
        "fintech", "neobank", "payment", "lending", "credit",
        "open banking", "embedded finance", "baas", "pix", "stablecoin",
        "defi", "crypto", "wealthtech", "bnpl", "cross-border",
    ],
    "AI": [
        "ai agent", "llm", "large language", "gpt", "claude", "gemini",
        "machine learning", "deep learning", "neural", "transformer",
        "open source ai", "multimodal", "rag", "fine-tun", "inference",
        "ai safety", "alignment", "foundation model",
    ],
}

_COMMERCIAL_KEYWORDS = [
    "raised", "funding", "series a", "series b", "series c", "seed round",
    "ipo", "acquisition", "acquired", "launch", "hiring", "job opening",
    "revenue", "arr", "mrr", "valuation", "pre-ipo",
]


def classify_theme(text: str, llm_client: Optional[LLMClient] = None) -> Tuple[str, str]:
    """Classify a post into (theme, sub_theme) from the taxonomy.

    Tries LLM classification first, falls back to keyword matching.

    Args:
        text: Post text to classify.
        llm_client: Optional LLM client for high-quality classification.

    Returns:
        Tuple of (theme, sub_theme). Returns ("", "") if no match.
    """
    if llm_client and llm_client.is_available:
        result = _classify_with_llm(text, llm_client)
        if result[0]:
            return result

    return _classify_with_keywords(text)


def _classify_with_llm(text: str, client: LLMClient) -> Tuple[str, str]:
    """Classify using LLM with structured output."""
    themes_list = ", ".join(SIGNAL_TAXONOMY.keys())
    subtemas_flat = []
    for theme, data in SIGNAL_TAXONOMY.items():
        for sub in data["subtemas"]:
            subtemas_flat.append(f"{theme}/{sub}")

    prompt = (
        f"Classify this social media post into ONE theme and sub-theme.\n\n"
        f"Themes: {themes_list}\n"
        f"Sub-themes: {', '.join(subtemas_flat[:30])}\n\n"
        f"Post: {text[:500]}\n\n"
        f"Reply with ONLY: theme|sub_theme\n"
        f"If no match, reply: none|none"
    )

    result = client.generate(
        user_prompt=prompt,
        system_prompt="You are a fintech/AI topic classifier. Reply only with theme|sub_theme.",
        max_tokens=50,
        temperature=0.0,
    )

    if not result:
        return ("", "")

    parts = result.strip().split("|", 1)
    if len(parts) == 2 and parts[0].strip().lower() != "none":
        theme = parts[0].strip()
        sub = parts[1].strip()
        if theme in SIGNAL_TAXONOMY:
            return (theme, sub)

    return ("", "")


def _classify_with_keywords(text: str) -> Tuple[str, str]:
    """Fallback classification using keyword matching."""
    text_lower = text.lower()

    best_theme = ""
    best_score = 0

    # Check most specific first (AI in Banking > Fintech > AI)
    for theme in ["AI in Banking", "Fintech", "AI"]:
        keywords = _THEME_KEYWORDS.get(theme, [])
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_theme = theme

    if not best_theme:
        return ("", "")

    # Try to match sub-theme
    sub_theme = _match_sub_theme(text_lower, best_theme)
    return (best_theme, sub_theme)


def _match_sub_theme(text_lower: str, theme: str) -> str:
    """Match the most relevant sub-theme within a theme."""
    subtemas = SIGNAL_TAXONOMY.get(theme, {}).get("subtemas", [])
    for sub in subtemas:
        if sub.lower() in text_lower:
            return sub
    return ""


def extract_entities(text: str, llm_client: Optional[LLMClient] = None) -> List[EntityMention]:
    """Extract named entities from post text.

    Uses LLM when available, falls back to regex patterns.

    Args:
        text: Post text.
        llm_client: Optional LLM client.

    Returns:
        List of EntityMention objects.
    """
    if llm_client and llm_client.is_available:
        entities = _extract_with_llm(text, llm_client)
        if entities:
            return entities

    return _extract_with_regex(text)


def _extract_with_llm(text: str, client: LLMClient) -> List[EntityMention]:
    """Extract entities using LLM."""
    prompt = (
        f"Extract named entities from this text. Return one per line as: name|type\n"
        f"Types: company, person, product, technology, regulation\n"
        f"Max 5 entities. Only clear, specific names.\n\n"
        f"Text: {text[:500]}\n\n"
        f"Entities:"
    )

    result = client.generate(
        user_prompt=prompt,
        system_prompt="You extract named entities. Reply only with name|type lines.",
        max_tokens=200,
        temperature=0.0,
    )

    if not result:
        return []

    entities = []
    for line in result.strip().split("\n"):
        parts = line.strip().split("|", 1)
        if len(parts) == 2 and parts[0].strip():
            entities.append(EntityMention(
                name=parts[0].strip(),
                entity_type=parts[1].strip().lower(),
                confidence=0.7,
            ))
    return entities[:5]


def _extract_with_regex(text: str) -> List[EntityMention]:
    """Fallback entity extraction using regex patterns."""
    entities = []

    # Detect @mentions as potential people/companies
    mentions = re.findall(r"@(\w+)", text)
    for mention in mentions[:3]:
        entities.append(EntityMention(
            name=mention,
            entity_type="person",
            confidence=0.3,
        ))

    # Detect $TICKER patterns as companies
    tickers = re.findall(r"\$([A-Z]{2,5})\b", text)
    for ticker in tickers[:3]:
        entities.append(EntityMention(
            name=ticker,
            entity_type="company",
            confidence=0.5,
        ))

    return entities


def compute_sentiment(text: str, llm_client: Optional[LLMClient] = None) -> float:
    """Compute sentiment score for a post.

    Args:
        text: Post text.
        llm_client: Optional LLM client.

    Returns:
        Float from -1 (very negative) to 1 (very positive). 0 = neutral.
    """
    if llm_client and llm_client.is_available:
        prompt = (
            f"Rate the sentiment of this text on a scale from -1.0 (very negative) "
            f"to 1.0 (very positive). 0.0 is neutral.\n\n"
            f"Text: {text[:300]}\n\n"
            f"Reply with ONLY the number (e.g., 0.3):"
        )
        result = llm_client.generate(
            user_prompt=prompt,
            system_prompt="You are a sentiment analyzer. Reply only with a number.",
            max_tokens=10,
            temperature=0.0,
        )
        if result:
            try:
                score = float(result.strip())
                return max(-1.0, min(1.0, score))
            except ValueError:
                pass

    return 0.0  # Neutral fallback


def is_commercial(text: str) -> bool:
    """Check if post contains commercial signals (funding, launches, hiring)."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _COMMERCIAL_KEYWORDS)


def classify_post(
    post: SocialPost,
    llm_client: Optional[LLMClient] = None,
) -> ProcessedSignal:
    """Fully classify a social post into a ProcessedSignal.

    Runs theme classification, entity extraction, sentiment analysis,
    and commercial signal detection. Uses LLM for all steps when available.

    NOTE: For batch processing, prefer classify_posts_batch() which uses
    keyword-only classification for all posts and LLM only for the top N.

    Args:
        post: Raw SocialPost from collector.
        llm_client: Optional LLM client for high-quality processing.

    Returns:
        ProcessedSignal with all classifications populated.
    """
    theme, sub_theme = classify_theme(post.text, llm_client)
    entities = extract_entities(post.text, llm_client)
    sentiment = compute_sentiment(post.text, llm_client)
    commercial = is_commercial(post.text)

    authority = _compute_authority(post)

    return ProcessedSignal(
        post=post,
        theme=theme,
        sub_theme=sub_theme,
        entities=entities,
        sentiment=sentiment,
        authority_score=authority,
        is_commercial=commercial,
    )


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


def _compute_engagement_rank(post: SocialPost) -> float:
    """Compute a single engagement number for ranking posts.

    Combines likes, replies (2x weight), reposts (3x weight), and score.
    Used to select the top N posts for LLM enrichment.

    Args:
        post: Raw SocialPost with metrics dict.

    Returns:
        Float engagement score (not normalized).
    """
    metrics = post.metrics or {}
    return (
        metrics.get("likes", 0)
        + metrics.get("replies", 0) * 2
        + metrics.get("reposts", 0) * 3
        + metrics.get("score", 0)
        + metrics.get("comments", 0) * 2
    )


def classify_posts_batch(
    posts: List[SocialPost],
    llm_client: Optional[LLMClient] = None,
    top_n_for_llm: int = 20,
) -> List[ProcessedSignal]:
    """Efficiently classify a batch of posts using keyword-first strategy.

    Strategy:
        1. ALL posts: keyword-only theme classification (fast, no LLM)
        2. ALL posts: regex entity extraction + keyword commercial detection
        3. TOP N posts (by engagement + authority): LLM entity extraction
        4. TOP N posts: LLM sentiment analysis

    This reduces LLM calls from N (all posts) to at most 2*top_n_for_llm
    (entity extraction + sentiment for the most important posts only).

    Args:
        posts: Raw SocialPost items from collector.
        llm_client: Optional LLM client for enriching top posts.
        top_n_for_llm: Number of top posts to enrich with LLM (default 20).

    Returns:
        List of ProcessedSignal with all classifications populated.
    """
    if not posts:
        return []

    # Step 1: Keyword-only classification for ALL posts (fast)
    signals: List[ProcessedSignal] = []
    for post in posts:
        theme, sub_theme = _classify_with_keywords(post.text)
        entities = _extract_with_regex(post.text)
        commercial = is_commercial(post.text)
        authority = _compute_authority(post)

        signal = ProcessedSignal(
            post=post,
            theme=theme,
            sub_theme=sub_theme,
            entities=entities,
            sentiment=0.0,  # Neutral default, enriched for top N below
            authority_score=authority,
            is_commercial=commercial,
        )
        signals.append(signal)

    logger.info(
        "Batch classified %d posts with keywords (%d themed)",
        len(signals),
        sum(1 for s in signals if s.theme),
    )

    # Step 2: Identify top N posts for LLM enrichment
    if not llm_client or not llm_client.is_available or top_n_for_llm <= 0:
        return signals

    # Rank by engagement + authority to find the most important posts
    ranked = sorted(
        enumerate(signals),
        key=lambda idx_sig: (
            _compute_engagement_rank(idx_sig[1].post)
            + idx_sig[1].authority_score * 1000
        ),
        reverse=True,
    )

    top_indices = set(idx for idx, _ in ranked[:top_n_for_llm])

    # Step 3: Enrich top N with LLM entity extraction and sentiment
    enriched_count = 0
    for idx in top_indices:
        signal = signals[idx]

        # LLM entity extraction (replaces regex entities if successful)
        llm_entities = _extract_with_llm(signal.post.text, llm_client)
        if llm_entities:
            signal.entities = llm_entities

        # LLM sentiment analysis (replaces 0.0 default)
        signal.sentiment = compute_sentiment(signal.post.text, llm_client)

        enriched_count += 1

    logger.info(
        "LLM-enriched top %d posts (entity extraction + sentiment)",
        enriched_count,
    )

    return signals
