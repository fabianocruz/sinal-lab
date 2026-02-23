"""Editorial guidelines and territories definition.

This module defines the editorial framework for Sinal.ai's AI-generated content,
implementing the guidelines from docs/EDITORIAL.md - Linha Editorial v2.

Key Components:
    - EDITORIAL_TERRITORIES: 4 content territories with weights, keywords, and agents
    - FILTER_CRITERIA: 5 quality criteria for content validation
    - FILTER_QUESTION: The ultimate quality test for publication decisions
    - EDITORIAL_RED_FLAGS: Patterns that disqualify content from publication
    - REGULATORY_KEYWORDS: Cross-cutting regulatory content markers

Editorial Territories (with weights):
    1. AI & Infraestrutura Inteligente (35%) - Pilar zero: agentic AI, LLMs, AI aplicada, infra, governance
    2. Fintech & Infraestrutura Financeira LATAM (30%) - Open Finance, Pix, stablecoins, embedded finance
    3. Engenharia & Plataforma (20%) - Arquitetura, cloud, DevOps, seguranca
    4. Venture Capital & Ecossistema (15%) - Deal flow, investor intelligence, M&A, ecosystem

The 5 Filter Criteria (content must pass 3/5):
    1. Tem dados verificáveis - Numbers, sources, methodology
    2. É útil para decisões - Actionable information for CTOs/founders
    3. Não existe em português com essa profundidade - Unique, original analysis
    4. Se alinha com um dos 4 territórios - Within editorial scope
    5. Tem ângulo LATAM específico - Not a US content translation

Usage:
    >>> from packages.editorial.guidelines import get_territory_keywords
    >>> keywords = get_territory_keywords("fintech")
    >>> print(keywords[:3])
    ['open finance', 'open banking', 'portabilidade']

    >>> from packages.editorial.guidelines import FILTER_CRITERIA
    >>> print(FILTER_CRITERIA["has_data"]["weight"])
    1.0

See Also:
    - classifier.py: Uses EDITORIAL_TERRITORIES for territory classification
    - validator.py: Uses FILTER_CRITERIA for content validation
    - docs/EDITORIAL.md: Full editorial guidelines document
"""

from typing import Dict, List, Any


# 4 Territórios Editoriais + 1 Meta-Território (Regulação)
EDITORIAL_TERRITORIES: Dict[str, Dict[str, Any]] = {
    "ai": {
        "name": "AI & Infraestrutura Inteligente",
        "weight": 0.35,
        "data_source_agents": ["RADAR", "CÓDIGO"],
        "keywords": [
            # Agentic AI & Autonomous Systems (1A)
            "agentic ai", "ai agents", "autonomous systems",
            "agentic commerce", "agentic payments", "agent-to-agent",
            # LLMs, Foundation Models & Open Source (1B)
            "artificial intelligence", "machine learning", "ai", "ml",
            "llm", "gpt", "claude", "deep learning",
            "foundation model", "fine-tuning", "rag", "open source ai",
            "llama", "mistral", "deepseek",
            # AI Aplicada a Verticais LATAM (1C)
            "fraud detection", "credit scoring", "underwriting",
            "aml", "kyc", "ai fintech", "ai healthtech", "ai agritech",
            "ai legaltech", "ai climate",
            # Generative AI para Produtos & Serviços (1D)
            "generative ai", "gen ai", "chatbot", "co-pilot",
            "ai assistant", "document generation",
            # Infraestrutura de AI (1E)
            "mlops", "inference", "model deployment",
            "ai infrastructure", "gpu", "vector database",
            # AI Governance & Regulação LATAM (1F)
            "ai governance", "ai ethics", "bias", "ai regulation",
        ],
        "filter_questions": [
            "Mostra AI em produção, não apenas conceito?",
            "Tem dados de impacto (custo, performance, ROI)?",
            "É aplicado a problema real LATAM ou tem lente LATAM (custo, latência, português)?",
        ],
        "sub_territories": [
            "agentic_ai",
            "llms_foundation_models",
            "ai_verticais_latam",
            "gen_ai_produtos",
            "infra_ai",
            "ai_governance",
        ],
    },
    "fintech": {
        "name": "Fintech & Infraestrutura Financeira LATAM",
        "weight": 0.30,
        "data_source_agents": ["MERCADO", "FUNDING"],
        "keywords": [
            # Open Finance & Portabilidade (2A)
            "open finance", "open banking", "portabilidade", "apis bancárias",
            # Pagamentos Instantâneos & Real-Time Rails (2B)
            "pix", "pagamento instantâneo", "codi", "spei", "drex",
            "cbdc", "moeda digital",
            # Embedded Finance & Novos Rails (2C — absorbs cripto)
            "embedded finance", "banking as a service", "baas", "dock", "zoop",
            "stablecoin", "usdc", "usdt", "dai",
            "tokenização", "rwa", "real world assets",
            "blockchain", "ethereum", "solana",
            "defi", "decentralized finance",
            # Neobanks & Digital Banks
            "nubank", "neobank", "banco digital", "mercado pago", "c6", "inter",
            # Remessas & Cross-Border (2D)
            "remessas", "cross-border", "remittance",
            # Convergência Competitiva (2E)
            "inclusão financeira", "sub-bancarizado", "scoring alternativo",
            "super app", "fintech",
        ],
        "filter_questions": [
            "Tem dados de volume, adoção ou custos?",
            "É específico para LATAM (não tradução de conteúdo US)?",
            "Vai além de press release (análise + dados reais)?",
        ],
        "sub_territories": [
            "open_finance",
            "pagamentos_instantaneos",
            "embedded_finance",
            "remessas_crossborder",
            "convergencia_competitiva",
        ],
    },
    "engenharia": {
        "name": "Engenharia & Plataforma",
        "weight": 0.20,
        "data_source_agents": ["CÓDIGO"],
        "keywords": [
            # Arquitetura de Startups LATAM (3A)
            "arquitetura", "microservices", "monolith", "stack",
            # Cloud & Infra no Brasil/LATAM (3B)
            "aws", "gcp", "azure", "cloud", "kubernetes", "docker",
            "latência",
            # DevOps, SRE & Observabilidade (3C)
            "devops", "sre", "observability", "monitoring",
            "deployment", "incident response",
            # Segurança, LGPD & Compliance Técnico (3D)
            "lgpd", "security", "compliance", "mtls",
        ],
        "filter_questions": [
            "É técnico + prático (não apenas conceitual)?",
            "Tem dados, benchmarks ou código concreto?",
            "É útil para CTOs/senior engineers tomarem decisões?",
        ],
        "sub_territories": [
            "arquitetura_startups",
            "cloud_infra",
            "devops_sre",
            "seguranca_lgpd",
        ],
    },
    "venture": {
        "name": "Venture Capital & Ecossistema",
        "weight": 0.15,
        "data_source_agents": ["FUNDING", "INDEX"],
        "keywords": [
            # Deal Flow & Funding Tracker (4A)
            "funding", "investment", "venture capital", "vc",
            "seed", "series a", "series b", "round",
            "investor", "fundo", "capital",
            # Investor Intelligence (4B)
            "co-investor", "follow-on", "portfolio",
            # Ecosystem Mapping (4C — absorbs green_agritech)
            "ecosystem", "startup", "unicórnio",
            "agritech", "agro", "agricultura", "foodtech",
            "climate tech", "esg", "sustentabilidade",
            "crédito de carbono", "carbon credit",
            "edtech", "healthtech", "proptech",
            # M&A, IPOs & Exits (4D)
            "m&a", "acquisition", "exit", "ipo",
        ],
        "filter_questions": [
            "Tem dados verificáveis (valor, investidores, data)?",
            "Vai além de press release (análise, contexto, tendência)?",
            "É relevante para entender o ecossistema LATAM?",
        ],
        "sub_territories": [
            "deal_flow",
            "investor_intelligence",
            "ecosystem_mapping",
            "ma_exits",
        ],
    },
}

# Meta-território: Regulação (transversal — sempre como contexto, nunca isolado)
REGULATORY_KEYWORDS = [
    "regulação", "regulamento", "lei", "marco legal",
    "bacen", "banco central", "cvm", "anpd",
    "lgpd", "compliance", "sandbox regulatório",
]

# Os 5 critérios da régua editorial
# Conteúdo deve passar em pelo menos 3 dos 5
FILTER_CRITERIA = {
    "has_data": {
        "name": "Tem dados verificáveis",
        "description": "Números, fontes, metodologia citada",
        "weight": 1.0,
    },
    "actionable": {
        "name": "É útil para decisões",
        "description": "Informação acionável para CTO/fundador técnico de fintech/AI no Brasil",
        "weight": 1.0,
    },
    "unique": {
        "name": "Não existe em português com essa profundidade",
        "description": "Estamos criando, não replicando",
        "weight": 1.0,
    },
    "aligns_territory": {
        "name": "Se alinha com um dos 4 territórios",
        "description": "Dentro do escopo editorial",
        "weight": 0.8,
    },
    "latam_angle": {
        "name": "Tem ângulo LATAM específico",
        "description": "Não é tradução de conteúdo US",
        "weight": 0.9,
    },
}

# A pergunta-filtro definitiva
FILTER_QUESTION = (
    "Um CTO de fintech em São Paulo com 10 anos de experiência "
    "pararia de trabalhar para ler isto?"
)

# Red flags - o que NÃO entra
EDITORIAL_RED_FLAGS = [
    "reescrita de press release sem análise",
    "opinião sem dados de suporte",
    "motivational content",
    "cobertura de eventos como jornalismo social",
    "hype sem substância",
    "tutorial básico que existe em qualquer lugar",
    "'O futuro do X' sem dados sobre o presente do X",
]


def get_territory_weight(territory_key: str) -> float:
    """Get editorial weight for a territory (0.0 to 1.0)."""
    return EDITORIAL_TERRITORIES.get(territory_key, {}).get("weight", 0.0)


def get_data_source_agents_for_territory(territory_key: str) -> List[str]:
    """Get list of data-source agents that feed a territory."""
    return EDITORIAL_TERRITORIES.get(territory_key, {}).get("data_source_agents", [])


def get_territory_keywords(territory_key: str) -> List[str]:
    """Get keyword list for territory classification."""
    return EDITORIAL_TERRITORIES.get(territory_key, {}).get("keywords", [])
