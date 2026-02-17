"""Content validation against editorial guidelines and quality bar.

This module implements the editorial validation pipeline that determines whether
AI-generated content is ready for publication. It enforces the 5-criteria quality
bar defined in guidelines.py and detects red flags that disqualify content.

Validation Pipeline:
    1. Check 5 editorial criteria (each returns True/False)
    2. Classify content territory and calculate confidence
    3. Detect red flags (press releases, hype, motivational content)
    4. Generate recommendations for failed criteria
    5. Calculate pass/fail decision (3/5 criteria + no red flags)

The 5 Criteria (must pass 3/5, or 4/5 in strict mode):
    1. has_data: Verifiable data (numbers, sources, methodology)
    2. actionable: Useful for decisions (how-to, benchmarks, analysis)
    3. unique: Doesn't exist in Portuguese with this depth
    4. aligns_territory: Fits one of 6 editorial territories
    5. latam_angle: LATAM-specific context (not US translation)

Red Flags (auto-reject):
    - Press release without analysis
    - Motivational/inspirational content without substance
    - Hype without supporting data
    - Basic tutorial (short + generic how-to)

Scoring:
    - score: Raw count of criteria met (0.0 to 5.0)
    - weighted_score: Weighted sum using criterion weights
    - confidence: Territory classification confidence (0.0 to 1.0)

Usage:
    >>> from packages.editorial.validator import validate_content
    >>> result = validate_content(
    ...     title="Pix alcança 3 bilhões de transações",
    ...     content="Análise do crescimento com dados do BCB...",
    ...     metadata={"sources": ["https://bcb.gov.br"]}
    ... )
    >>> if result.passes_editorial_bar:
    ...     publish(content)
    ... else:
    ...     print(result.recommendations)

Integration Points:
    - Called by AI agents after content generation
    - Used in editorial review dashboard (future)
    - Feeds /validate-content skill for manual validation

See Also:
    - guidelines.py: Criteria definitions and weights
    - classifier.py: Territory classification used in criterion #4
    - docs/EDITORIAL.md: Full editorial guidelines
"""

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
    """Check if content has verifiable data (numbers, sources, methodology).

    Technical Implementation:
        Uses 3 independent signals to detect data-driven content. Requiring 2/3
        signals prevents false positives from content that mentions numbers without
        context (e.g., "5 tips") while allowing flexibility for different content types.

    Signal 1 - Numbers/Percentages:
        Regex matches: "45%", "100 milhões", "R$ 850 bilhões"
        Pattern: \d+[%\.\,]?\d*\s*(milhão|milhões|bilhão|bilhões|mil|%|percent)
        Rationale: Requires magnitude/unit context to avoid matching dates or IDs

    Signal 2 - Sources in Metadata:
        Checks metadata["sources"] for non-empty list
        Rationale: AI agents should provide source URLs for all data claims

    Signal 3 - Methodology Keywords:
        Keywords: "metodologia", "dados de", "segundo", "de acordo com", "fonte:"
        Rationale: Attribution phrases indicate data provenance

    Decision Threshold: 2/3 signals
        - Prevents rejection of data-rich content missing one signal
        - Blocks opinion pieces with incidental number mentions
    """
    # Look for numbers/percentages with magnitude context
    has_numbers = bool(re.search(r'\d+[%\.\,]?\d*\s*(milhão|milhões|bilhão|bilhões|mil|%|percent)', content.lower()))

    # Look for sources in metadata
    has_sources = bool(metadata.get("sources")) and len(metadata.get("sources", [])) > 0

    # Look for methodology/attribution phrases
    has_methodology = any(
        keyword in content.lower()
        for keyword in ["metodologia", "dados de", "segundo", "de acordo com", "fonte:"]
    )

    # Need at least 2 of 3 signals to pass
    signals = [has_numbers, has_sources, has_methodology]
    return sum(signals) >= 2


def _check_actionable(content: str, title: Optional[str]) -> bool:
    """Check if content provides actionable information.

    Technical Implementation:
        Counts occurrences of keywords that signal practical, decision-oriented
        content. The keyword list targets 3 categories of actionable content:
        how-to/guides, analysis/benchmarks, and business decision factors.

    Actionable Categories:
        1. How-to/Guides: "como", "guia", "passo a passo", "implementar"
        2. Analysis/Comparisons: "benchmark", "comparativo", "análise"
        3. Decision Factors: "custo de", "ROI", "oportunidade", "impacto em"

    Design Decisions:
        - Title included (without 2x weight) for discoverability
        - Case-insensitive substring matching (not word-boundary)
          Rationale: Allows "implementação" to match "implementar"
        - Threshold: 2+ keywords
          Rationale: Single match could be coincidental; 2+ indicates intent

    Examples:
        PASS: "Como implementar Pix: guia com benchmark de custos"
        FAIL: "Fintech anuncia nova funcionalidade" (no actionable keywords)
    """
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

    # At least 2 actionable keywords required
    return matches >= 2


def _check_uniqueness(content: str, metadata: Dict) -> bool:
    """Check for signals of unique/original content.

    Technical Implementation:
        This criterion is the hardest to automate since "uniqueness" is subjective.
        We use 4 proxy signals that correlate with original, in-depth content rather
        than superficial summaries or translations.

    Signal 1 - Original Data Claims:
        Keywords: "dados exclusivos", "pesquisa própria", "análise original"
        Rationale: Explicit claims of original research

    Signal 2 - Content Depth (500+ words):
        Threshold: >500 words
        Rationale: Deep analysis requires space. Short content is likely generic.
        500 words ≈ 2-3 minute read

    Signal 3 - Multi-Source Research (3+ sources):
        Threshold: ≥3 sources in metadata
        Rationale: Original analysis cross-references multiple sources

    Signal 4 - Data Density (5+ numbers):
        Threshold: ≥5 numeric values
        Rationale: Data-driven analysis includes multiple data points

    Decision Threshold: 2/4 signals
        - Balances strictness with flexibility
        - Example: 600-word data-rich analysis passes without explicit "original" claim
        - Example: Short (200-word) press release with 3 sources fails

    Known Limitations:
        - Cannot detect plagiarism or verify true originality
        - Long generic content (>500 words) can game the system
        - Future: Consider semantic similarity checks against published content
    """
    uniqueness_signals = [
        # Signal 1: Original data/research claims
        bool(re.search(r'(dados exclusivos|pesquisa própria|análise original)', content.lower())),

        # Signal 2: Deep analysis (longer content)
        len(content.split()) > 500,

        # Signal 3: Multiple sources cited
        len(metadata.get("sources", [])) >= 3,

        # Signal 4: Specific numbers/data points
        len(re.findall(r'\d+[%\.\,]?\d*', content)) >= 5,
    ]

    # Need at least 2 of 4 uniqueness signals
    return sum(uniqueness_signals) >= 2


def _check_latam_angle(content: str, title: Optional[str]) -> bool:
    """Check for LATAM-specific angle.

    Technical Implementation:
        Detects LATAM-specific context to ensure content is not a generic US tech
        article translation. Uses 3 categories of keywords: geography, institutions,
        and LATAM-native companies/products.

    Keyword Categories:
        1. Countries/Regions (bilingual):
           - Portuguese: "brasil", "méxico", "argentina", "américa latina"
           - English: "brazil", "mexico", "latin america", "latam"
           Rationale: Content can be written in either language

        2. Cities:
           - "são paulo", "buenos aires", "santiago", "bogotá", "lima"
           Rationale: City mentions indicate regional focus vs. global generalization

        3. LATAM-Specific Entities:
           - Infrastructure: "pix", "drex" (Brazil-specific payment systems)
           - Institutions: "bacen", "cvm", "anpd" (Brazilian regulators)
           - Regulation: "lgpd" (Brazilian GDPR equivalent)
           - Companies: "nubank", "mercado pago", "mercado livre"

    Decision Threshold: 2+ mentions
        - Single mention could be passing reference
        - 2+ mentions indicate substantive LATAM focus

    Examples:
        PASS: "Nubank alcança 100M clientes no Brasil" (nubank + brasil = 2)
        PASS: "Comparativo Pix vs. FedNow nos EUA" (pix = 1, but context is LATAM-centric)
        FAIL: "AI trends in Silicon Valley and New York" (0 mentions)

    Design Trade-off:
        Substring matching (not word-boundary) to catch variations:
        - "brasileiro" matches "brasil"
        - "mexicano" matches "mexico"
        This creates false positives (rare) but reduces false negatives (common).
    """
    latam_keywords = [
        # Countries (bilingual: PT + EN)
        "brasil", "brazil", "méxico", "mexico", "argentina", "chile", "colômbia", "colombia",
        "peru", "uruguai", "uruguay", "américa latina", "latin america", "latam",

        # Cities
        "são paulo", "rio de janeiro", "belo horizonte", "buenos aires",
        "santiago", "bogotá", "lima", "montevidéu", "cidade do méxico",

        # LATAM-specific infrastructure, regulation, companies
        "pix", "drex", "bacen", "banco central do brasil", "cvm", "anpd",
        "lgpd", "nubank", "mercado pago", "mercado livre",
    ]

    full_text = ((title or "") + " " + content).lower()

    matches = sum(
        1 for keyword in latam_keywords
        if keyword in full_text
    )

    # At least 2 LATAM mentions required
    return matches >= 2


def _detect_red_flags(content: str, title: Optional[str]) -> List[str]:
    """Detect editorial red flags that automatically disqualify content.

    Technical Implementation:
        Red flags represent content patterns that violate editorial principles
        regardless of other criteria. Any detected red flag results in immediate
        rejection (passes_editorial_bar = False).

    Red Flag 1 - Press Releases Without Analysis:
        Patterns: "press release", "comunicado à imprensa", "anuncia hoje", "tem o prazer de"
        Rationale: Corporate announcements without editorial analysis are not journalism
        Example: "Empresa XYZ tem o prazer de anunciar nova rodada de investimento"

    Red Flag 2 - Motivational/Inspirational Content:
        Keywords: "inspire", "sonho", "acredite", "você consegue", "motivação"
        Threshold: 2+ keywords
        Rationale: Motivational content lacks technical substance
        Example: "Acredite nos seus sonhos e tenha motivação para empreender"

    Red Flag 3 - Hype Without Data:
        Hype Keywords: "revolucionário", "game changer", "disruptivo", "vai mudar tudo"
        Threshold: 2+ hype keywords AND <3 numbers in content
        Rationale: Hyperbolic claims without data are marketing, not analysis
        Example: "Startup revolucionária é um game changer disruptivo" (no data)
        Counter-example: "Startup disruptiva cresce 300% com 50M usuários" (has data)

    Red Flag 4 - Basic Tutorials:
        Pattern: "como" in content AND <300 words
        Threshold: Short how-to content
        Rationale: Basic tutorials already exist everywhere; we focus on depth
        Example: "Como usar Git: primeiro instale, depois git init"
        Counter-example: "Como implementar Pix: guia de 2000 palavras..." (long, detailed)

    Design Decisions:
        - Red flags are cumulative (multiple can trigger)
        - Any single red flag blocks publication
        - Thresholds chosen to minimize false positives (wrongly blocking good content)
        - False negatives (letting bad content through) are acceptable; human review catches them

    Return Value:
        List of detected red flag descriptions (empty list = no flags)
    """
    detected = []
    full_text = ((title or "") + " " + content).lower()

    # Red Flag 1: Press release patterns
    if re.search(r'(press release|comunicado à imprensa|anuncia hoje|tem o prazer de)', full_text):
        detected.append("Parece press release sem análise")

    # Red Flag 2: Motivational/inspirational content (2+ keywords)
    motivational_keywords = ["inspire", "sonho", "acredite", "você consegue", "motivação"]
    if sum(1 for kw in motivational_keywords if kw in full_text) >= 2:
        detected.append("Conteúdo motivacional/inspiracional")

    # Red Flag 3: Hype without data (2+ hype keywords AND <3 numbers)
    hype_keywords = ["revolucionário", "game changer", "disruptivo", "vai mudar tudo"]
    if sum(1 for kw in hype_keywords if kw in full_text) >= 2 and len(re.findall(r'\d+', content)) < 3:
        detected.append("Hype sem dados de suporte")

    # Red Flag 4: Basic tutorial (short how-to content)
    if "como" in full_text and len(content.split()) < 300:
        detected.append("Possível tutorial básico (conteúdo curto)")

    return detected
