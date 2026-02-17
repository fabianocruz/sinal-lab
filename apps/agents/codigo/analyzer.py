"""Analyzer for CODIGO agent.

Analyzes developer ecosystem signals: language/framework adoption velocity,
library momentum, community growth, and technology trend indicators.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from apps.agents.codigo.collector import DevSignal

# Language ecosystem weights (popularity + growth signal)
LANGUAGE_WEIGHTS: dict[str, float] = {
    "python": 0.9, "typescript": 0.9, "javascript": 0.8,
    "rust": 0.85, "go": 0.8, "zig": 0.7,
    "kotlin": 0.6, "swift": 0.5, "java": 0.5,
    "c++": 0.5, "c#": 0.5, "ruby": 0.4,
    "elixir": 0.6, "dart": 0.5, "scala": 0.4,
}

DEFAULT_LANGUAGE_WEIGHT = 0.3

# Category keywords for dev signal classification
DEV_CATEGORIES: dict[str, list[str]] = {
    "ai_frameworks": [
        "llm", "machine learning", "deep learning", "transformer",
        "langchain", "llamaindex", "openai", "anthropic", "huggingface",
        "pytorch", "tensorflow", "jax", "onnx", "mlops",
    ],
    "web_frameworks": [
        "next.js", "react", "vue", "svelte", "astro", "remix",
        "htmx", "tailwind", "django", "fastapi", "express",
        "nuxt", "angular", "solid", "qwik",
    ],
    "developer_tools": [
        "cli", "linter", "formatter", "debugger", "profiler",
        "package manager", "build tool", "bundler", "compiler",
        "editor", "terminal", "shell",
    ],
    "infrastructure": [
        "docker", "kubernetes", "terraform", "ansible", "helm",
        "ci/cd", "github actions", "deployment", "serverless",
        "edge", "cdn", "proxy", "load balancer",
    ],
    "databases": [
        "database", "sql", "nosql", "redis", "postgres", "sqlite",
        "mongodb", "vector database", "graph database", "orm",
        "migration", "query builder",
    ],
    "security": [
        "auth", "security", "encryption", "vulnerability",
        "oauth", "jwt", "identity", "secrets",
    ],
}


@dataclass
class AnalyzedSignal:
    """A developer ecosystem signal with analysis scores."""

    signal: DevSignal
    category: str
    language_weight: float
    momentum_score: float
    community_score: float
    adoption_indicator: str  # rising, stable, declining, new

    @property
    def composite_score(self) -> float:
        """Weighted composite: language 20%, momentum 40%, community 40%."""
        return round(
            self.language_weight * 0.20
            + self.momentum_score * 0.40
            + self.community_score * 0.40,
            4,
        )


def categorize_signal(signal: DevSignal) -> str:
    """Assign a category to a dev signal based on content matching."""
    text = " ".join([
        signal.title.lower(),
        (signal.summary or "").lower(),
        " ".join(signal.tags),
    ])

    best_category = "general"
    best_count = 0

    for category, keywords in DEV_CATEGORIES.items():
        matches = sum(1 for kw in keywords if kw in text)
        if matches > best_count:
            best_count = matches
            best_category = category

    return best_category


def compute_language_weight(signal: DevSignal) -> float:
    """Score based on the signal's programming language relevance."""
    lang = (signal.language or "").lower()
    if lang:
        return LANGUAGE_WEIGHTS.get(lang, DEFAULT_LANGUAGE_WEIGHT)

    # Try to detect from tags
    for tag in signal.tags:
        weight = LANGUAGE_WEIGHTS.get(tag.lower(), 0)
        if weight > 0:
            return weight

    return DEFAULT_LANGUAGE_WEIGHT


def compute_momentum(
    signal: DevSignal,
    reference_time: Optional[datetime] = None,
) -> float:
    """Compute momentum from recency and engagement metrics."""
    now = reference_time or datetime.now(timezone.utc)

    # Recency component
    if signal.published_at:
        age_hours = max((now - signal.published_at).total_seconds() / 3600, 0)
        recency = 0.5 ** (age_hours / 72)  # 3-day half-life
    else:
        recency = 0.3

    # Engagement: GitHub stars
    stars = signal.metrics.get("stars", 0)
    if stars > 0:
        engagement = min(math.log10(stars + 1) / 5, 1.0)
    else:
        engagement = 0.0

    # Forks as secondary signal
    forks = signal.metrics.get("forks", 0)
    fork_signal = min(math.log10(forks + 1) / 4, 0.5) if forks > 0 else 0.0

    if engagement > 0:
        momentum = recency * 0.35 + engagement * 0.40 + fork_signal * 0.25
    else:
        momentum = recency * 0.8 + fork_signal * 0.2

    return round(min(momentum, 1.0), 4)


def compute_community_score(signal: DevSignal) -> float:
    """Score community activity and adoption signals."""
    score = 0.0

    stars = signal.metrics.get("stars", 0)
    forks = signal.metrics.get("forks", 0)
    issues = signal.metrics.get("open_issues", 0)
    watchers = signal.metrics.get("watchers", 0)

    if stars > 1000:
        score += 0.3
    elif stars > 100:
        score += 0.2
    elif stars > 10:
        score += 0.1

    if forks > 100:
        score += 0.2
    elif forks > 10:
        score += 0.1

    # Active issues indicate community engagement
    if issues > 50:
        score += 0.15
    elif issues > 10:
        score += 0.1

    if watchers > 100:
        score += 0.1

    # Packages and articles get a base community score
    if signal.signal_type in ("package", "article"):
        score = max(score, 0.3)

    return min(score, 1.0)


def determine_adoption(signal: DevSignal) -> str:
    """Determine the adoption trajectory of a signal."""
    stars = signal.metrics.get("stars", 0)
    forks = signal.metrics.get("forks", 0)

    if signal.signal_type == "package":
        return "stable"

    if stars > 10000:
        return "stable"
    elif stars > 1000:
        ratio = forks / max(stars, 1)
        if ratio > 0.15:
            return "rising"
        return "stable"
    elif stars > 50:
        return "rising"
    else:
        return "new"


def analyze_signals(
    signals: list[DevSignal],
    reference_time: Optional[datetime] = None,
) -> list[AnalyzedSignal]:
    """Analyze all signals and return sorted by composite score."""
    analyzed: list[AnalyzedSignal] = []

    for signal in signals:
        analyzed.append(AnalyzedSignal(
            signal=signal,
            category=categorize_signal(signal),
            language_weight=compute_language_weight(signal),
            momentum_score=compute_momentum(signal, reference_time),
            community_score=compute_community_score(signal),
            adoption_indicator=determine_adoption(signal),
        ))

    analyzed.sort(key=lambda x: x.composite_score, reverse=True)
    return analyzed
