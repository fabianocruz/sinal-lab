"""NLP-lite classifier for RADAR agent.

Classifies trend signals by topic, computes momentum scores,
and tags signals with relevance categories for the LATAM tech audience.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from apps.agents.radar.collector import TrendSignal

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
        """Weighted composite: topic relevance 30%, momentum 40%, LATAM 30%."""
        return round(
            self.topic_confidence * 0.30
            + self.momentum_score * 0.40
            + self.latam_relevance * 0.30,
            4,
        )


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
    """Classify and score all signals, returning sorted by composite score."""
    classified: list[ClassifiedSignal] = []

    for signal in signals:
        topics, primary_topic, topic_confidence = classify_topics(signal)
        momentum = compute_momentum(signal, reference_time)
        latam = compute_latam_relevance(signal)

        classified.append(ClassifiedSignal(
            signal=signal,
            topics=topics,
            primary_topic=primary_topic,
            topic_confidence=topic_confidence,
            momentum_score=momentum,
            latam_relevance=latam,
        ))

    classified.sort(key=lambda x: x.composite_score, reverse=True)
    return classified
