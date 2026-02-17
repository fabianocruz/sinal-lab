"""Content validation against editorial guidelines."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re

from packages.editorial.guidelines import FILTER_CRITERIA, FILTER_QUESTION, EDITORIAL_RED_FLAGS
from packages.editorial.classifier import classify_territory, TerritoryClassification


@dataclass
class ContentValidationResult:
    """Result of editorial validation."""

    passes_editorial_bar: bool
    criteria_met: Dict[str, bool]  # criterion_key -> passed
    score: float  # 0.0 to 5.0 (one point per criterion)
    weighted_score: float  # Weighted by criterion importance
    territory_classification: Optional[TerritoryClassification]
    red_flags: List[str]
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "passes_editorial_bar": self.passes_editorial_bar,
            "criteria_met": self.criteria_met,
            "score": self.score,
            "weighted_score": self.weighted_score,
            "territory_classification": self.territory_classification.to_dict() if self.territory_classification else None,
            "red_flags": self.red_flags,
            "recommendations": self.recommendations,
        }

    def summary(self) -> str:
        """Human-readable summary of validation."""
        status = "✅ PASSA" if self.passes_editorial_bar else "❌ NÃO PASSA"
        met_count = sum(self.criteria_met.values())
        return (
            f"{status} | Score: {self.score}/5.0 ({self.weighted_score:.2f} weighted) | "
            f"Critérios: {met_count}/5 | "
            f"Território: {self.territory_classification.primary_territory if self.territory_classification else 'unknown'}"
        )


def validate_content(
    content: str,
    metadata: Optional[Dict] = None,
    title: Optional[str] = None,
    strict_mode: bool = False,
) -> ContentValidationResult:
    """Validate content against editorial guidelines.

    Checks the 5 editorial criteria:
    1. Tem dados verificáveis
    2. É útil para decisões (actionable)
    3. Não existe em português com essa profundidade
    4. Se alinha com um dos 6 territórios
    5. Tem ângulo LATAM específico

    Content must pass at least 3 criteria (or 4 in strict mode).

    Args:
        content: Full text content to validate
        metadata: Optional metadata dict (can include sources, tags, etc.)
        title: Optional title
        strict_mode: If True, requires 4/5 criteria instead of 3/5

    Returns:
        ContentValidationResult with pass/fail and detailed scoring

    Example:
        >>> result = validate_content(
        ...     title="Nubank alcança 100M de clientes",
        ...     content="O Nubank atingiu 100 milhões de clientes...",
        ...     metadata={"sources": ["https://nubank.com.br/..."]}
        ... )
        >>> result.passes_editorial_bar
        True
        >>> result.score
        4.0
    """
    metadata = metadata or {}
    criteria_results: Dict[str, bool] = {}
    red_flags: List[str] = []
    recommendations: List[str] = []

    # Criterion 1: Tem dados verificáveis
    has_data = _check_has_data(content, metadata)
    criteria_results["has_data"] = has_data
    if not has_data:
        recommendations.append(
            "Adicione dados quantitativos (números, percentagens, valores) com fontes"
        )

    # Criterion 2: É útil para decisões (actionable)
    is_actionable = _check_actionable(content, title)
    criteria_results["actionable"] = is_actionable
    if not is_actionable:
        recommendations.append(
            "Foque em informação acionável: o que o leitor pode fazer com isso?"
        )

    # Criterion 3: Não existe em português com essa profundidade
    # (This is subjective - we approximate with uniqueness signals)
    is_unique = _check_uniqueness(content, metadata)
    criteria_results["unique"] = is_unique
    if not is_unique:
        recommendations.append(
            "Vá além do óbvio: análise original, dados exclusivos, ou ângulo diferenciado"
        )

    # Criterion 4: Se alinha com um dos 6 territórios
    territory_classification = classify_territory(content, title, metadata)
    aligns_territory = (
        territory_classification.primary_territory != "unknown"
        and territory_classification.confidence > 0.3
    )
    criteria_results["aligns_territory"] = aligns_territory
    if not aligns_territory:
        recommendations.append(
            f"Reforce keywords dos territórios prioritários: Fintech (40%), AI (20%), Engenharia (20%)"
        )

    # Criterion 5: Tem ângulo LATAM específico
    has_latam_angle = _check_latam_angle(content, title)
    criteria_results["latam_angle"] = has_latam_angle
    if not has_latam_angle:
        recommendations.append(
            "Adicione contexto LATAM: dados regionais, comparativos entre países, casos brasileiros"
        )

    # Check for red flags
    detected_red_flags = _detect_red_flags(content, title)
    red_flags.extend(detected_red_flags)

    # Calculate scores
    criteria_met_count = sum(criteria_results.values())
    score = float(criteria_met_count)  # 0.0 to 5.0

    # Weighted score (using weights from FILTER_CRITERIA)
    weighted_score = float(sum(
        FILTER_CRITERIA[key]["weight"]
        for key, passed in criteria_results.items()
        if passed
    ))

    # Pass threshold: 3/5 criteria (or 4/5 in strict mode)
    required_criteria = 4 if strict_mode else 3
    passes_editorial_bar = (
        criteria_met_count >= required_criteria
        and len(red_flags) == 0  # No red flags allowed
    )

    return ContentValidationResult(
        passes_editorial_bar=passes_editorial_bar,
        criteria_met=criteria_results,
        score=score,
        weighted_score=weighted_score,
        territory_classification=territory_classification,
        red_flags=red_flags,
        recommendations=recommendations,
    )


# Helper functions for each criterion

def _check_has_data(content: str, metadata: Dict) -> bool:
    """Check if content has verifiable data (numbers, sources, methodology)."""
    # Look for numbers/percentages
    has_numbers = bool(re.search(r'\d+[%\.\,]?\d*\s*(milhão|milhões|bilhão|bilhões|mil|%|percent)', content.lower()))

    # Look for sources in metadata
    has_sources = bool(metadata.get("sources")) and len(metadata.get("sources", [])) > 0

    # Look for methodology mentions
    has_methodology = any(
        keyword in content.lower()
        for keyword in ["metodologia", "dados de", "segundo", "de acordo com", "fonte:"]
    )

    # Need at least 2 of 3 signals
    signals = [has_numbers, has_sources, has_methodology]
    return sum(signals) >= 2


def _check_actionable(content: str, title: Optional[str]) -> bool:
    """Check if content provides actionable information."""
    actionable_keywords = [
        "como", "guia", "passo a passo", "implementar", "construir",
        "benchmark", "comparativo", "análise", "dados mostram",
        "oportunidade", "impacto em", "custo de", "ROI",
        "checklist", "playbook", "framework",
    ]

    full_text = (title or "") + " " + content
    matches = sum(
        1 for keyword in actionable_keywords
        if keyword in full_text.lower()
    )

    # At least 2 actionable keywords
    return matches >= 2


def _check_uniqueness(content: str, metadata: Dict) -> bool:
    """Check for signals of unique/original content."""
    uniqueness_signals = [
        # Original data/research
        bool(re.search(r'(dados exclusivos|pesquisa própria|análise original)', content.lower())),

        # Deep analysis (longer content)
        len(content.split()) > 500,

        # Multiple sources cited
        len(metadata.get("sources", [])) >= 3,

        # Specific numbers/data points
        len(re.findall(r'\d+[%\.\,]?\d*', content)) >= 5,
    ]

    # Need at least 2 uniqueness signals
    return sum(uniqueness_signals) >= 2


def _check_latam_angle(content: str, title: Optional[str]) -> bool:
    """Check for LATAM-specific angle."""
    latam_keywords = [
        # Countries
        "brasil", "brazil", "méxico", "mexico", "argentina", "chile", "colômbia", "colombia",
        "peru", "uruguai", "uruguay", "américa latina", "latin america", "latam",

        # Cities
        "são paulo", "rio de janeiro", "belo horizonte", "buenos aires",
        "santiago", "bogotá", "lima", "montevidéu", "cidade do méxico",

        # LATAM-specific
        "pix", "drex", "bacen", "banco central do brasil", "cvm", "anpd",
        "lgpd", "nubank", "mercado pago", "mercado livre",
    ]

    full_text = ((title or "") + " " + content).lower()

    matches = sum(
        1 for keyword in latam_keywords
        if keyword in full_text
    )

    # At least 2 LATAM mentions
    return matches >= 2


def _detect_red_flags(content: str, title: Optional[str]) -> List[str]:
    """Detect editorial red flags."""
    detected = []
    full_text = ((title or "") + " " + content).lower()

    # Press release patterns
    if re.search(r'(press release|comunicado à imprensa|anuncia hoje|tem o prazer de)', full_text):
        detected.append("Parece press release sem análise")

    # Motivational/inspirational
    motivational_keywords = ["inspire", "sonho", "acredite", "você consegue", "motivação"]
    if sum(1 for kw in motivational_keywords if kw in full_text) >= 2:
        detected.append("Conteúdo motivacional/inspiracional")

    # Hype sem substância
    hype_keywords = ["revolucionário", "game changer", "disruptivo", "vai mudar tudo"]
    if sum(1 for kw in hype_keywords if kw in full_text) >= 2 and len(re.findall(r'\d+', content)) < 3:
        detected.append("Hype sem dados de suporte")

    # Tutorial básico (very short + how-to)
    if "como" in full_text and len(content.split()) < 300:
        detected.append("Possível tutorial básico (conteúdo curto)")

    return detected
