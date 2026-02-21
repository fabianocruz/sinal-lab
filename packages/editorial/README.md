# Editorial Module

> Automated content validation and territory classification for Sinal.ai AI agents

## Overview

The editorial module implements Sinal.ai's editorial guidelines as executable code, enabling AI agents to automatically validate their outputs against quality standards before publication. It enforces the **5-criteria quality bar** and **6 editorial territories** defined in [docs/EDITORIAL.md](../../docs/EDITORIAL.md).

**Core Capabilities:**
- ✅ **Content Validation**: Checks if AI-generated content passes 3/5 editorial criteria
- 🏷️ **Territory Classification**: Assigns content to 1 of 6 editorial territories (Fintech, AI, Cripto, Engenharia, Venture, Green/AgriTech)
- 🚩 **Red Flag Detection**: Identifies disqualifying patterns (press releases, hype, motivational content)
- 💡 **Recommendations**: Provides actionable feedback for rejected content

---

## Quick Start

### Installation

The module is part of the monorepo. No separate installation needed.

```bash
# From project root
cd packages/editorial
```

### Basic Usage

```python
from packages.editorial import validate_content, classify_territory

# Example 1: Validate content
result = validate_content(
    title="Pix alcança 3 bilhões de transações mensais — análise do crescimento",
    content="""
    O Pix atingiu 3 bilhões de transações mensais em janeiro de 2026,
    representando um crescimento de 45% em relação ao mesmo período de 2025,
    segundo dados do Banco Central do Brasil.

    [... análise detalhada com dados, fontes, contexto LATAM ...]
    """,
    metadata={
        "sources": ["https://www.bcb.gov.br/pix"],
        "agent": "MERCADO",
    }
)

# Check if content passes editorial bar
if result.passes_editorial_bar:
    print("✅ APROVADO PARA PUBLICAÇÃO")
    print(f"Score: {result.score}/5.0")
    print(f"Território: {result.territory_classification.primary_territory}")
else:
    print("❌ REPROVADO")
    print("Recomendações:")
    for rec in result.recommendations:
        print(f"  - {rec}")

# Example 2: Classify territory only
classification = classify_territory(
    title="Como usar GPT-4 para detecção de fraude em pagamentos",
    content="Análise técnica de ML para fraud detection..."
)

print(f"Território: {classification.primary_territory}")  # "ai"
print(f"Confiança: {classification.confidence:.2f}")       # 0.87
print(f"Secundários: {classification.secondary_territories}")  # ["fintech"]
```

### Running Examples

```bash
# From project root
python3 -m packages.editorial.example_usage
```

Output:
```
======================================================================
EXEMPLO 1: Conteúdo Fintech de Alta Qualidade
======================================================================

✅ PASSA | Score: 4.0/5.0 (3.70 weighted) | Critérios: 4/5 | Território: fintech

Critérios atendidos:
  ✅ has_data
  ✅ actionable
  ❌ unique
  ✅ aligns_territory
  ✅ latam_angle

APROVADO PARA PUBLICAÇÃO
```

---

## Architecture

### Module Structure

```
packages/editorial/
├── __init__.py              # Public API exports
├── guidelines.py            # Editorial territories & criteria definitions
├── classifier.py            # Territory classification logic
├── validator.py             # Content validation pipeline
├── example_usage.py         # Usage examples
├── README.md               # This file
└── tests/
    ├── test_guidelines.py   # Tests for guidelines constants
    ├── test_classifier.py   # Tests for territory classification
    └── test_validator.py    # Tests for content validation
```

### Core Components

#### 1. **guidelines.py** — Definitions
Defines the editorial framework constants:
- `EDITORIAL_TERRITORIES`: 6 territories with weights, keywords, agents
- `FILTER_CRITERIA`: 5 quality criteria with weights
- `FILTER_QUESTION`: The ultimate quality test
- `EDITORIAL_RED_FLAGS`: Disqualifying patterns
- Helper functions: `get_territory_keywords()`, `get_territory_weight()`, etc.

#### 2. **classifier.py** — Territory Classification
Classifies content into editorial territories using keyword matching:
- **Input**: Title + content + metadata
- **Algorithm**: Count keyword matches per territory, normalize by content length
- **Output**: `TerritoryClassification` with primary territory, confidence, secondaries

**Key Features:**
- Title weighted 2x (counted twice)
- Case-insensitive word-boundary matching
- Confidence score normalized by content length
- Secondary territories (≥30% of primary score)
- Regulatory content flag

#### 3. **validator.py** — Content Validation
Validates content against the 5-criteria quality bar:
- **Input**: Title + content + metadata
- **Process**: Check 5 criteria, detect red flags, generate recommendations
- **Output**: `ContentValidationResult` with pass/fail, scores, recommendations

**5 Criteria** (must pass 3/5, or 4/5 in strict mode):
1. **has_data**: Verifiable data (numbers, sources, methodology)
2. **actionable**: Useful for decisions (how-to, benchmarks, analysis)
3. **unique**: Doesn't exist in Portuguese with this depth
4. **aligns_territory**: Fits one of 6 editorial territories
5. **latam_angle**: LATAM-specific context (not US translation)

**Red Flags** (auto-reject):
- Press release without analysis
- Motivational/inspirational content
- Hype without data
- Basic tutorial (short + generic)

---

## Integration with AI Agents

### Current Agent Workflow (Pre-Editorial)

```
AI Agent (SINTESE, RADAR, CODIGO, FUNDING, MERCADO)
  ↓
1. Collect data from sources
  ↓
2. Process & analyze
  ↓
3. Score confidence (DQ + AC)
  ↓
4. Generate output (Markdown)
  ↓
5. Save to file → PUBLISHED (no validation)
```

### Enhanced Workflow (With Editorial Validation)

```
AI Agent
  ↓
1. Collect data from sources
  ↓
2. Process & analyze
  ↓
3. Score confidence (DQ + AC)
  ↓
4. Generate output (Markdown)
  ↓
5. **EDITORIAL VALIDATION** ← NEW STEP
   │
   ├─ PASS → Save & Publish
   │
   └─ FAIL → Log for human review
              OR Auto-revise (future)
```

### Implementation Guide

#### Step 1: Import Editorial Module

Add to your agent's `pipeline.py` or `output.py`:

```python
from packages.editorial import validate_content, classify_territory
```

#### Step 2: Validate Before Saving

```python
def generate_output(self, signals: List[Signal]) -> str:
    """Generate Markdown output from processed signals."""

    # Generate content as before
    title = self._generate_title(signals)
    content = self._generate_content(signals)
    metadata = {
        "sources": [s.source_url for s in signals],
        "agent": self.config.agent_name,
        "confidence_dq": self._calculate_dq_score(),
        "confidence_ac": self._calculate_ac_score(),
    }

    # NEW: Validate against editorial guidelines
    validation_result = validate_content(
        title=title,
        content=content,
        metadata=metadata,
        strict_mode=False  # or True for higher bar
    )

    # NEW: Handle validation result
    if validation_result.passes_editorial_bar:
        logger.info(f"✅ Content PASSED editorial validation (score: {validation_result.score}/5.0)")
        # Continue with normal flow (save, publish)
        return self._format_markdown(title, content, metadata)
    else:
        logger.warning(f"❌ Content FAILED editorial validation (score: {validation_result.score}/5.0)")
        logger.warning(f"Red flags: {validation_result.red_flags}")
        logger.warning(f"Recommendations: {validation_result.recommendations}")

        # Option A: Block publication
        raise EditorialValidationError(
            f"Content failed editorial bar: {validation_result.red_flags}"
        )

        # Option B: Save for human review
        self._save_for_review(title, content, validation_result)
        return None

        # Option C: Auto-revise and retry (future enhancement)
        # revised_content = self._revise_based_on_recommendations(
        #     content, validation_result.recommendations
        # )
        # return self._retry_validation(title, revised_content, metadata)
```

#### Step 3: Update Agent System Prompts

Add editorial guidelines to agent system prompts in `apps/agents/{name}/config.py`:

```python
SYSTEM_PROMPT = """
You are the RADAR agent for Sinal.ai, tracking tech trends in LATAM.

EDITORIAL GUIDELINES:
Your outputs must pass 3 of 5 editorial criteria:
1. Tem dados verificáveis (numbers, sources, methodology)
2. É útil para decisões (actionable for CTOs/founders)
3. Não existe em português com essa profundidade (unique/original)
4. Se alinha com um dos 6 territórios (Fintech, AI, Cripto, Engenharia, Venture, GreenTech)
5. Tem ângulo LATAM específico (not US translation)

AVOID RED FLAGS:
- Press releases without analysis
- Motivational/inspirational content
- Hype without data ("revolucionário", "game changer" without numbers)
- Basic tutorials (too short, too generic)

Focus on: data-driven analysis, LATAM context, actionable insights, original research.
"""
```

#### Step 4: Territory-Specific Guidelines

Each agent can focus on their primary territories:

| Agent     | Primary Territories   | Weight |
|-----------|-----------------------|--------|
| MERCADO   | Fintech (40%)         | High   |
| RADAR     | AI (20%)              | High   |
| CODIGO    | Engenharia (20%)      | High   |
| FUNDING   | Venture (15%)         | Medium |
| SINTESE   | All territories       | N/A    |

Example agent-specific validation:

```python
# In MERCADO agent
validation_result = validate_content(content, metadata, strict_mode=False)

# Check if classified as expected territory
if validation_result.territory_classification.primary_territory != "fintech":
    logger.warning(
        f"MERCADO content classified as {validation_result.territory_classification.primary_territory}, "
        f"expected fintech. Review keyword usage."
    )
```

---

## API Reference

### `validate_content()`

Validate content against editorial guidelines.

```python
def validate_content(
    content: str,
    metadata: Optional[Dict] = None,
    title: Optional[str] = None,
    strict_mode: bool = False,
) -> ContentValidationResult
```

**Parameters:**
- `content` (str): Full text content to validate
- `metadata` (dict, optional): Metadata dict (sources, agent, confidence scores)
- `title` (str, optional): Content title (if available)
- `strict_mode` (bool): If True, requires 4/5 criteria instead of 3/5

**Returns:**
- `ContentValidationResult` with:
  - `passes_editorial_bar` (bool): True if content is publishable
  - `criteria_met` (dict): Which criteria passed (has_data, actionable, etc.)
  - `score` (float): Raw score 0.0-5.0 (count of criteria met)
  - `weighted_score` (float): Weighted score using criterion weights
  - `territory_classification` (TerritoryClassification): Territory info
  - `red_flags` (list): Detected red flags (empty = no flags)
  - `recommendations` (list): How to improve rejected content

**Example:**
```python
result = validate_content(
    title="Pix alcança 3B transações",
    content="Análise detalhada com dados...",
    metadata={"sources": ["https://bcb.gov.br"]},
    strict_mode=False
)

if result.passes_editorial_bar:
    publish(content)
```

---

### `classify_territory()`

Classify content into editorial territories.

```python
def classify_territory(
    content: str,
    title: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> TerritoryClassification
```

**Parameters:**
- `content` (str): Full text content to classify
- `title` (str, optional): Content title (weighted 2x in classification)
- `metadata` (dict, optional): Metadata dict (can include agent hint)

**Returns:**
- `TerritoryClassification` with:
  - `primary_territory` (str): Main territory ("fintech", "ai", "cripto", etc.)
  - `confidence` (float): Classification confidence 0.0-1.0
  - `secondary_territories` (list): Other matching territories (≥30% of primary)
  - `is_regulatory` (bool): If content is regulatory (meta-territory)
  - `keyword_matches` (dict): Match counts per territory

**Example:**
```python
classification = classify_territory(
    title="Pix vs FedNow comparison",
    content="Analysis of instant payment systems..."
)

print(classification.primary_territory)  # "fintech"
print(classification.confidence)         # 0.92
print(classification.secondary_territories)  # ["engenharia"]
```

---

## Testing

### Running Tests

```bash
# From project root
python3 -m pytest packages/editorial/tests/ -v
```

### Test Coverage

**87 tests, 100% passing:**
- `test_guidelines.py`: 23 tests (territory definitions, criteria, helpers)
- `test_classifier.py`: 29 tests (territory classification, edge cases)
- `test_validator.py`: 35 tests (validation logic, criteria, red flags)

**Coverage:**
- All core functions: 100%
- Helper functions: 100%
- Edge cases: Extensive

### Writing Tests for Agent Integration

Example test for agent with editorial validation:

```python
def test_radar_agent_respects_editorial_bar():
    """Test that RADAR agent outputs pass editorial validation."""
    agent = RadarAgent()

    # Run agent
    result = agent.run(week=1, persist=False)

    # Validate output
    validation = validate_content(
        title=result.title,
        content=result.content,
        metadata=result.metadata
    )

    # Assert passes editorial bar
    assert validation.passes_editorial_bar is True
    assert validation.score >= 3.0
    assert validation.territory_classification.primary_territory in ["ai", "fintech", "engenharia"]
    assert len(validation.red_flags) == 0
```

---

## Configuration

### Adjusting Territory Weights

Edit `packages/editorial/guidelines.py`:

```python
EDITORIAL_TERRITORIES = {
    "fintech": {
        "weight": 0.40,  # 40% of editorial focus
        # ...
    },
    "ai": {
        "weight": 0.20,  # 20% of editorial focus
        # ...
    },
    # ...
}
```

**Note:** Weights represent relative editorial priorities, not strict probabilities. They can sum to >1.0 to indicate coverage overlap.

### Adjusting Criteria Thresholds

Edit helper functions in `packages/editorial/validator.py`:

```python
def _check_has_data(content: str, metadata: Dict) -> bool:
    # ... existing code ...

    # Adjust threshold here:
    signals = [has_numbers, has_sources, has_methodology]
    return sum(signals) >= 2  # Change to >= 3 for stricter validation
```

### Adding New Keywords

Edit keyword lists in `packages/editorial/guidelines.py`:

```python
EDITORIAL_TERRITORIES = {
    "fintech": {
        "keywords": [
            "pix", "open finance", "nubank",
            # ADD NEW KEYWORDS HERE:
            "pix cobrança", "open insurance", "inter",
        ],
    },
}
```

**After changes:**
1. Run tests: `pytest packages/editorial/tests/`
2. Update documentation if behavior changes
3. Commit with descriptive message: `feat(editorial): add new fintech keywords`

---

## Roadmap

### Phase 1: Foundation ✅ (Current)
- [x] Core validation logic
- [x] Territory classification
- [x] Red flag detection
- [x] Comprehensive test suite
- [x] Documentation

### Phase 2: Agent Integration (Next)
- [ ] Integrate with SINTESE agent
- [ ] Integrate with RADAR agent
- [ ] Integrate with CODIGO agent
- [ ] Integrate with FUNDING agent
- [ ] Integrate with MERCADO agent
- [ ] Update agent system prompts

### Phase 3: Feedback Loop (Future)
- [ ] Editorial dashboard for human review
- [ ] Rejection analytics (which criteria fail most)
- [ ] Auto-revision based on recommendations
- [ ] A/B testing different thresholds

### Phase 4: Advanced Features (Future)
- [ ] Semantic similarity checks (plagiarism detection)
- [ ] Reader engagement prediction
- [ ] Multi-language support (Spanish)
- [ ] Real-time validation API endpoint

---

## Troubleshooting

### Common Issues

#### Content always fails `unique` criterion

**Symptoms:**
```python
result.criteria_met["unique"] == False
```

**Causes:**
1. Content too short (<500 words)
2. <3 sources in metadata
3. <5 numbers in content
4. No "dados exclusivos", "pesquisa própria", or "análise original" mentions

**Solution:**
- Increase content depth (aim for 600+ words)
- Add more sources to metadata (3+ URLs)
- Include more data points (5+ numbers with context)
- Explicitly state original research: "análise original de dados exclusivos..."

---

#### Content classified as `unknown` territory

**Symptoms:**
```python
result.territory_classification.primary_territory == "unknown"
```

**Causes:**
- Too few territory keywords in content
- Content too generic or unrelated to 6 territories

**Solution:**
- Add territory-specific keywords (see `guidelines.py` for lists)
- Focus content on one of 6 territories
- Use title to signal territory (title weighted 2x)

Example:
```python
# BAD: Generic title
title = "Nova startup levanta investimento"

# GOOD: Territory-specific title
title = "Fintech levanta Series A para expandir Pix B2B"
```

---

#### False positive red flags

**Symptoms:**
```python
"Possível tutorial básico" in result.red_flags
# But content is actually in-depth analysis
```

**Causes:**
- Content has "como" keyword AND <300 words

**Solution:**
- Increase content length (300+ words)
- OR avoid "como" in title if content is short
- OR adjust threshold in `_detect_red_flags()` (see Configuration)

---

## Contributing

### Adding a New Criterion

1. Define in `guidelines.py`:
```python
FILTER_CRITERIA = {
    # ... existing criteria ...
    "new_criterion": {
        "name": "Descrição do critério",
        "description": "Explicação detalhada",
        "weight": 1.0,
    },
}
```

2. Implement check in `validator.py`:
```python
def _check_new_criterion(content: str, metadata: Dict) -> bool:
    """Check for new criterion.

    Technical Implementation:
        [Detailed explanation of logic...]
    """
    # Implementation here
    return True  # or False
```

3. Add to validation pipeline:
```python
def validate_content(...):
    # ...

    # Criterion N: New criterion
    new_criterion = _check_new_criterion(content, metadata)
    criteria_results["new_criterion"] = new_criterion
    if not new_criterion:
        recommendations.append("Como melhorar este critério")

    # ...
```

4. Write tests in `tests/test_validator.py`
5. Update this README with examples

---

## License

Part of Sinal.ai monorepo. Internal use only.

---

## Support

- **Issues**: Create issue in main repo with `[editorial]` prefix
- **Questions**: Ask in #tech-platform Slack channel
- **Documentation**: See [docs/EDITORIAL.md](../../docs/EDITORIAL.md) for full guidelines

---

**Last Updated**: 2026-02-17
**Version**: 1.0.0
**Maintainers**: @platform-team
