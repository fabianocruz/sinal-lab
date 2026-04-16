"""NLP-lite classifier for RADAR agent.

Classifies trend signals by topic, computes momentum scores,
and tags signals with relevance categories for the LATAM tech audience.

Includes content quality filtering to block spam, adult content,
corporate press releases, and low-editorial-quality signals.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from apps.agents.radar.collector import TrendSignal

logger = logging.getLogger(__name__)

# Blocked terms — signals containing ANY of these are rejected outright.
# Catches adult content, spam, and obviously off-topic material that
# can slip through Google Trends or community sources.
BLOCKED_TERMS: list[str] = [
    # Adult content / spam
    "xvidio", "x vidio", "xvideo", "x video", "xvid", "pornhub", "onlyfans", "chaturbate",
    "brazzers", "redtube", "xhamster", "youporn", "porn", "hentai",
    "nude", "nudes", "nsfw", "sex tape", "escort",
    # Gambling / betting
    "bet365", "apostas online", "cassino online", "slot machine",
    "jogo de azar", "roleta",
    # Celebrity / gossip
    "big brother", "novela", "reality show", "celebridade",
    "fofoca", "influenciador",
    # Sports (non-tech)
    "campeonato", "futebol", "copa do mundo", "olimpiada",
    "selecao brasileira",
]

# Negative keywords — if matched, topic confidence is zeroed.
# Catches corporate press releases, advertorials, and marketing content
# that may contain tech keywords but lack editorial value.
NEGATIVE_KEYWORDS: list[str] = [
    # Corporate press releases
    "diz ceo", "diz cto", "diz cfo", "diz cdo", "diz coo",
    "afirma ceo", "afirma cto", "afirma diretor",
    "triplica receita", "dobra receita", "receita anual",
    "triplica faturamento", "dobra faturamento",
    "resultado financeiro", "balanco trimestral",
    "conteudo patrocinado", "publieditorial", "branded content",
    # Self-promotion / community noise threads
    "weekly thread", "self-promo", "self-promotion", "shameless plug",
    "show hn:", "hiring thread", "who is hiring", "freelance thread",
    "monthly thread", "daily discussion", "megathread",
]

# Minimum topic confidence to include in report. Signals that only match
# on momentum (Google Trends) or LATAM relevance but have zero topic
# confidence are noise -- they contain geographic/language signals but
# no actual tech content.
MIN_TOPIC_CONFIDENCE = 0.10

# Minimum LATAM relevance to include low-confidence global signals.
# High-confidence global signals (e.g., major AI breakthrough) are kept
# regardless; this filters generic global noise with weak topic match.
MIN_LATAM_RELEVANCE = 0.10

# Topic taxonomy with keyword patterns
TOPIC_PATTERNS: dict[str, list[str]] = {
    "ai_ml": [
        "machine learning", "deep learning", "llm", "gpt", "claude",
        "transformer", "neural network", "ai agent", "generative ai",
        "ia generativa", "computer vision", "reinforcement learning",
        "fine-tuning", "rag", "vector database", "embeddings",
        "diffusion model", "multimodal", "foundation model",
    ],
    "infrastructure": [
        "kubernetes", "docker", "terraform", "aws", "gcp", "azure",
        "serverless", "edge computing", "cdn", "ci/cd", "devops",
        "microservices", "grpc", "graphql", "api gateway", "observability",
        "prometheus", "grafana", "istio", "service mesh",
    ],
    "developer_tools": [
        "ide", "code editor", "linter", "formatter", "debugger",
        "package manager", "build tool", "testing framework", "cli",
        "developer experience", "dx", "sdk", "api", "open source",
        "rust", "go", "zig", "bun", "deno", "typescript",
    ],
    "startup_ecosystem": [
        "startup", "venture capital", "funding", "ipo", "acquisition",
        "unicorn", "seed round", "series a", "series b", "accelerator",
        "incubator", "pivot", "product-market fit", "growth",
    ],
    "fintech": [
        "fintech", "payment", "neobank", "defi", "blockchain",
        "cryptocurrency", "bitcoin", "ethereum", "stablecoin",
        "open banking", "open finance", "pix", "cbdc", "drex",
        "insurtech", "lending", "credit",
        "web3", "smart contract", "solidity", "token", "wallet",
        "dex", "amm", "liquidity", "yield farming",
        "solana", "polygon", "layer 2", "rollup", "bridge", "tvl",
    ],
    "latam_tech": [
        "brasil", "brazil", "latam", "america latina", "latin america",
        "sao paulo", "mexico", "bogota", "buenos aires", "santiago",
        "nubank", "mercadolibre", "rappi", "ifood", "vtex", "totvs",
    ],
    "security": [
        "cybersecurity", "zero trust", "encryption", "vulnerability",
        "ransomware", "security breach", "authentication", "oauth",
        "identity", "sso", "zero-day", "penetration testing",
    ],
    "data_engineering": [
        "data pipeline", "etl", "data lake", "data warehouse",
        "streaming", "kafka", "spark", "dbt", "airflow", "snowflake",
        "databricks", "real-time analytics", "olap",
    ],
}

# Momentum decay: how quickly signals lose momentum
MOMENTUM_HALF_LIFE_DAYS = 3


@dataclass
class ClassifiedSignal:
    """A trend signal with topic classification and momentum score."""

    signal: TrendSignal
    topics: list[str]
    primary_topic: str
    topic_confidence: float
    momentum_score: float
    latam_relevance: float

    @property
    def composite_score(self) -> float:
        """Weighted composite: topic relevance 35%, momentum 30%, LATAM 35%.

        Momentum weight reduced from 0.40 to 0.30 to avoid recency bias
        dominating over topic quality and LATAM signal strength.
        """
        return round(
            self.topic_confidence * 0.35
            + self.momentum_score * 0.30
            + self.latam_relevance * 0.35,
            4,
        )


def _is_blocked(signal: TrendSignal) -> bool:
    """Check if a signal contains blocked terms (spam, adult content, etc.)."""
    text = " ".join([
        signal.title.lower(),
        (signal.summary or "").lower(),
        signal.url.lower(),
    ])
    for term in BLOCKED_TERMS:
        if term in text:
            return True
    return False


def _has_negative_keyword(signal: TrendSignal) -> bool:
    """Check if a signal matches negative keywords (press releases, etc.)."""
    text = " ".join([
        signal.title.lower(),
        (signal.summary or "").lower(),
    ])
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            return True
    return False


def classify_topics(signal: TrendSignal) -> tuple[list[str], str, float]:
    """Classify a signal into one or more topics.

    Returns (topics_list, primary_topic, confidence).
    """
    text = " ".join([
        signal.title.lower(),
        (signal.summary or "").lower(),
        " ".join(signal.tags),
    ])

    topic_scores: dict[str, float] = {}

    for topic, patterns in TOPIC_PATTERNS.items():
        matches = sum(1 for p in patterns if p in text)
        if matches > 0:
            topic_scores[topic] = min(matches * 0.15, 1.0)

    if not topic_scores:
        return ["uncategorized"], "uncategorized", 0.1

    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
    topics = [t[0] for t in sorted_topics if t[1] >= 0.1]
    primary_topic = sorted_topics[0][0]
    confidence = sorted_topics[0][1]

    return topics, primary_topic, confidence


def compute_momentum(
    signal: TrendSignal,
    reference_time: Optional[datetime] = None,
) -> float:
    """Compute momentum score based on recency and engagement metrics.

    More recent signals with higher engagement metrics get higher momentum.
    Uses exponential decay with a 3-day half-life.
    """
    now = reference_time or datetime.now(timezone.utc)

    # Recency component
    if signal.published_at:
        age_hours = max((now - signal.published_at).total_seconds() / 3600, 0)
        half_life_hours = MOMENTUM_HALF_LIFE_DAYS * 24
        recency = 0.5 ** (age_hours / half_life_hours)
    else:
        recency = 0.3  # Unknown date gets moderate score

    # Engagement component (from metrics)
    engagement = 0.0
    stars = signal.metrics.get("stars", 0)
    if stars > 0:
        # Log scale for GitHub stars
        import math
        engagement = min(math.log10(stars + 1) / 5, 1.0)

    # Source type weight
    source_weights = {
        "hn": 0.8,
        "github": 0.7,
        "arxiv": 0.6,
        "trends": 0.9,
        "community": 0.5,
    }
    source_weight = source_weights.get(signal.source_type, 0.5)

    # Composite momentum
    if engagement > 0:
        momentum = recency * 0.4 + engagement * 0.3 + source_weight * 0.3
    else:
        momentum = recency * 0.6 + source_weight * 0.4

    return round(min(momentum, 1.0), 4)


def compute_latam_relevance(signal: TrendSignal) -> float:
    """Score how relevant this signal is to LATAM tech."""
    text = " ".join([
        signal.title.lower(),
        (signal.summary or "").lower(),
    ])

    score = 0.0

    # Portuguese language indicators
    pt_signals = [
        "de", "para", "com", "que", "em", "por", "uma", "dos",
        "tecnologia", "empresa", "mercado", "investimento",
    ]
    pt_matches = sum(1 for w in pt_signals if f" {w} " in f" {text} ")
    if pt_matches >= 3:
        score += 0.4

    # LATAM geography
    latam_geo = [
        "brasil", "brazil", "sao paulo", "latam", "america latina",
        "latin america", "mexico", "bogota", "buenos aires", "santiago",
        "lima", "medellin", "florianopolis", "recife", "curitiba",
    ]
    geo_matches = sum(1 for g in latam_geo if g in text)
    score += min(geo_matches * 0.15, 0.4)

    # LATAM company names
    latam_cos = [
        "nubank", "mercadolibre", "rappi", "ifood", "creditas",
        "vtex", "stone", "pagseguro", "kavak", "clip",
    ]
    co_matches = sum(1 for c in latam_cos if c in text)
    score += min(co_matches * 0.1, 0.3)

    return min(score, 1.0)


def classify_signals(
    signals: list[TrendSignal],
    reference_time: Optional[datetime] = None,
) -> list[ClassifiedSignal]:
    """Classify and score all signals, returning sorted by composite score.

    Applies three filtering layers:
    1. Blocked terms — rejects spam, adult content, gambling
    2. Negative keywords — rejects press releases, advertorials
    3. Minimum topic confidence — rejects signals with no tech relevance
    """
    classified: list[ClassifiedSignal] = []
    blocked_count = 0
    negative_count = 0
    low_topic_count = 0

    for signal in signals:
        # Layer 1: blocked terms (spam, adult content)
        if _is_blocked(signal):
            blocked_count += 1
            continue

        # Layer 2: negative keywords (press releases, advertorials)
        if _has_negative_keyword(signal):
            negative_count += 1
            continue

        topics, primary_topic, topic_confidence = classify_topics(signal)

        # Layer 3: minimum topic confidence
        if topic_confidence < MIN_TOPIC_CONFIDENCE:
            low_topic_count += 1
            continue

        momentum = compute_momentum(signal, reference_time)
        latam = compute_latam_relevance(signal)

        # Layer 4: filter low-confidence global signals with no LATAM relevance.
        # High-confidence signals (major AI breakthroughs, etc.) pass regardless.
        if latam < MIN_LATAM_RELEVANCE and topic_confidence < 0.5:
            logger.debug(
                "Filtered global noise signal (latam=%.2f, topic=%.2f): %s",
                latam, topic_confidence, signal.title,
            )
            continue

        classified.append(ClassifiedSignal(
            signal=signal,
            topics=topics,
            primary_topic=primary_topic,
            topic_confidence=topic_confidence,
            momentum_score=momentum,
            latam_relevance=latam,
        ))

    if blocked_count > 0:
        logger.info("Blocked %d signals (spam/adult content)", blocked_count)
    if negative_count > 0:
        logger.info("Filtered %d signals (negative keywords)", negative_count)
    if low_topic_count > 0:
        logger.info("Filtered %d signals below min topic confidence", low_topic_count)

    classified.sort(key=lambda x: x.composite_score, reverse=True)
    return classified
