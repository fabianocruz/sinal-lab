"""Layer 4: VIES — Bias Detection.

Scans content for systematic biases that could undermine credibility:
    1. Geographic bias — disproportionate coverage of Sao Paulo
    2. Sector bias — over-representation of a single sector
    3. Source bias — over-reliance on a small number of data sources
    4. Recency bias — all items from last 24h, missing medium-term trends

Warning-level flags only — does not block publication,
but logged for transparency and monthly aggregate reporting.
"""

import logging
import re
from typing import Any

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.models import (
    BiasMetrics,
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)

LAYER_NAME = "vies"

# Thresholds
GEO_DOMINANCE_THRESHOLD = 0.60  # Single city > 60% = flag
SECTOR_DOMINANCE_THRESHOLD = 0.50  # Single sector > 50% = flag
SOURCE_DOMINANCE_THRESHOLD = 0.40  # Single source > 40% = flag

# Geographic keywords (city/region -> canonical name)
GEO_KEYWORDS: dict = {
    "sao paulo": "Sao Paulo",
    "são paulo": "Sao Paulo",
    "sp": "Sao Paulo",
    "rio de janeiro": "Rio de Janeiro",
    "rio": "Rio de Janeiro",
    "florianopolis": "Florianopolis",
    "florianópolis": "Florianopolis",
    "belo horizonte": "Belo Horizonte",
    "curitiba": "Curitiba",
    "porto alegre": "Porto Alegre",
    "recife": "Recife",
    "campinas": "Campinas",
    "brasilia": "Brasilia",
    "brasília": "Brasilia",
    "mexico city": "Mexico City",
    "ciudad de mexico": "Mexico City",
    "bogota": "Bogota",
    "bogotá": "Bogota",
    "buenos aires": "Buenos Aires",
    "santiago": "Santiago",
    "lima": "Lima",
    "medellin": "Medellin",
    "medellín": "Medellin",
    "montevideo": "Montevideo",
}

# Sector keywords -> canonical sector
SECTOR_KEYWORDS: dict = {
    "fintech": "Fintech",
    "pagamento": "Fintech",
    "banco digital": "Fintech",
    "pix": "Fintech",
    "credito": "Fintech",
    "crédito": "Fintech",
    "open finance": "Fintech",
    "artificial intelligence": "AI/ML",
    "inteligencia artificial": "AI/ML",
    "inteligência artificial": "AI/ML",
    "machine learning": "AI/ML",
    "deep learning": "AI/ML",
    "llm": "AI/ML",
    "gpt": "AI/ML",
    "saas": "SaaS",
    "software as a service": "SaaS",
    "agritech": "Agritech",
    "agtech": "Agritech",
    "healthtech": "Healthtech",
    "health tech": "Healthtech",
    "edtech": "Edtech",
    "education tech": "Edtech",
    "logtech": "Logistics",
    "logistica": "Logistics",
    "logística": "Logistics",
    "e-commerce": "E-commerce",
    "ecommerce": "E-commerce",
    "marketplace": "E-commerce",
    "climate tech": "Climate",
    "cleantech": "Climate",
    "energia renovavel": "Climate",
    "cybersecurity": "Security",
    "seguranca": "Security",
    "segurança": "Security",
    "proptech": "Proptech",
    "real estate tech": "Proptech",
}


def run_vies(agent_output: AgentOutput) -> LayerResult:
    """Execute the VIES (bias detection) layer.

    Analyzes content for systematic biases across 4 dimensions.
    All flags are warning-level (does not block publication).

    Returns:
        LayerResult with bias metrics and warning flags.
    """
    flags: list[ReviewFlag] = []
    metadata: dict[str, Any] = {}

    body = agent_output.body_md or ""
    body_lower = body.lower()

    # --- Check 1: Geographic bias ---
    geo_dist = _compute_geographic_distribution(body_lower)
    metadata["geographic_distribution"] = geo_dist

    if geo_dist:
        total_mentions = sum(geo_dist.values())
        for city, count in geo_dist.items():
            ratio = count / total_mentions
            if ratio > GEO_DOMINANCE_THRESHOLD:
                flags.append(ReviewFlag(
                    severity=FlagSeverity.WARNING,
                    category=FlagCategory.BIAS,
                    message=f"Geographic bias: {city} represents {ratio:.0%} of location mentions ({count}/{total_mentions})",
                    layer=LAYER_NAME,
                    detail=f"Threshold: {GEO_DOMINANCE_THRESHOLD:.0%}. Consider diversifying geographic coverage.",
                ))

    # --- Check 2: Sector bias ---
    sector_dist = _compute_sector_distribution(body_lower)
    metadata["sector_distribution"] = sector_dist

    if sector_dist:
        total_mentions = sum(sector_dist.values())
        for sector, count in sector_dist.items():
            ratio = count / total_mentions
            if ratio > SECTOR_DOMINANCE_THRESHOLD:
                flags.append(ReviewFlag(
                    severity=FlagSeverity.WARNING,
                    category=FlagCategory.BIAS,
                    message=f"Sector bias: {sector} represents {ratio:.0%} of sector mentions ({count}/{total_mentions})",
                    layer=LAYER_NAME,
                    detail=f"Threshold: {SECTOR_DOMINANCE_THRESHOLD:.0%}. Consider covering other verticals.",
                ))

    # --- Check 3: Source bias ---
    source_dist = _compute_source_distribution(agent_output.sources)
    metadata["source_distribution"] = source_dist

    if source_dist:
        total_sources = sum(source_dist.values())
        for domain, count in source_dist.items():
            ratio = count / total_sources
            if ratio > SOURCE_DOMINANCE_THRESHOLD:
                flags.append(ReviewFlag(
                    severity=FlagSeverity.WARNING,
                    category=FlagCategory.BIAS,
                    message=f"Source bias: {domain} represents {ratio:.0%} of sources ({count}/{total_sources})",
                    layer=LAYER_NAME,
                    detail=f"Threshold: {SOURCE_DOMINANCE_THRESHOLD:.0%}. Diversify data sources.",
                ))

    # --- Check 4: Recency bias ---
    recency_flags = _check_recency_bias(body_lower)
    flags.extend(recency_flags)

    # Build bias metrics
    bias_metrics = BiasMetrics(
        geographic_distribution=geo_dist,
        sector_distribution=sector_dist,
        source_distribution=source_dist,
    )
    metadata["bias_metrics"] = bias_metrics.to_dict()

    # Grade: bias layer uses only warnings, grade reflects severity
    grade = _compute_grade(flags)

    logger.info(
        "[%s] Vies layer: grade=%s, geo_locations=%d, sectors=%d, flags=%d",
        LAYER_NAME,
        grade,
        len(geo_dist),
        len(sector_dist),
        len(flags),
    )

    return LayerResult(
        layer_name=LAYER_NAME,
        passed=True,  # Bias layer never blocks
        grade=grade,
        flags=flags,
        metadata=metadata,
    )


def _compute_geographic_distribution(text: str) -> dict:
    """Count geographic mentions in the text."""
    distribution: dict = {}
    for keyword, canonical in GEO_KEYWORDS.items():
        count = len(re.findall(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE))
        if count > 0:
            distribution[canonical] = distribution.get(canonical, 0) + count
    return distribution


def _compute_sector_distribution(text: str) -> dict:
    """Count sector keyword mentions in the text."""
    distribution: dict = {}
    for keyword, canonical in SECTOR_KEYWORDS.items():
        count = len(re.findall(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE))
        if count > 0:
            distribution[canonical] = distribution.get(canonical, 0) + count
    return distribution


def _compute_source_distribution(sources: list) -> dict:
    """Count sources by domain."""
    distribution: dict = {}
    for source in sources:
        if not source:
            continue
        # Extract domain from URL
        domain = source
        if "://" in source:
            domain = source.split("://", 1)[1].split("/", 1)[0]
        domain = domain.lower().strip()
        distribution[domain] = distribution.get(domain, 0) + 1
    return distribution


def _check_recency_bias(text: str) -> list:
    """Check if content is overly focused on very recent events."""
    flags: list = []

    # Detect "today", "hoje", "just now", "agora" patterns
    recency_words = ["today", "hoje", "just now", "agora mesmo", "breaking", "just announced"]
    recency_count = 0
    for word in recency_words:
        recency_count += len(re.findall(re.escape(word), text, re.IGNORECASE))

    if recency_count > 5:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.BIAS,
            message=f"Recency bias: {recency_count} urgency/recency markers detected — content may over-weight very recent events",
            layer=LAYER_NAME,
        ))

    return flags


def _compute_grade(flags: list) -> str:
    """Compute bias grade.

    A: No bias flags
    B: 1-2 bias warnings (minor imbalance)
    C: 3+ bias warnings (notable imbalance)
    """
    warning_count = sum(1 for f in flags if f.severity == FlagSeverity.WARNING)
    if warning_count == 0:
        return "A"
    if warning_count <= 2:
        return "B"
    return "C"
