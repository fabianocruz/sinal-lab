"""Editorial guidelines and territories definition.

Based on docs/EDITORIAL.md - Linha Editorial Definitiva.
"""

from typing import Dict, List, Any


# 6 Territórios Editoriais + 1 Meta-Território
EDITORIAL_TERRITORIES: Dict[str, Dict[str, Any]] = {
    "fintech": {
        "name": "Fintech & Economia Digital LATAM",
        "weight": 0.40,
        "primary_agents": ["MERCADO", "FUNDING"],
        "keywords": [
            # Open Finance
            "open finance", "open banking", "portabilidade", "apis bancárias",
            # Pagamentos
            "pix", "pagamento instantâneo", "codi", "spei", "drex",
            # Neobanks
            "nubank", "neobank", "banco digital", "mercado pago", "c6", "inter",
            # Embedded Finance
            "embedded finance", "banking as a service", "baas", "dock", "zoop",
            # Remessas
            "remessas", "cross-border", "stablecoin", "remittance",
            # Inclusão
            "inclusão financeira", "sub-bancarizado", "scoring alternativo",
        ],
        "filter_questions": [
            "Tem dados de volume, adoção ou custos?",
            "É específico para LATAM (não tradução de conteúdo US)?",
            "Tem ângulo técnico ou de dados, não apenas produto announcement?",
        ],
        "sub_territories": [
            "open_finance",
            "pagamentos_instantaneos",
            "inclusao_financeira",
            "embedded_finance",
            "remessas",
            "convergencia_fintech_bancos",
        ],
    },
    "ai": {
        "name": "AI Aplicada & Infraestrutura",
        "weight": 0.20,
        "primary_agents": ["RADAR", "CÓDIGO"],
        "keywords": [
            "artificial intelligence", "machine learning", "ai", "ml",
            "fraud detection", "credit scoring", "llm", "gpt", "claude",
            "agentic ai", "ai agents", "autonomous systems",
            "ai governance", "lgpd", "bias", "ethics",
            "generative ai", "gen ai", "chatbot",
            "mlops", "inference", "model deployment",
        ],
        "filter_questions": [
            "Mostra AI em produção, não apenas conceito?",
            "Tem dados de impacto em métricas de negócio?",
            "É aplicado a problema real LATAM?",
        ],
        "sub_territories": [
            "ai_fintech",
            "agentic_ai",
            "ai_governance",
            "gen_ai_servicos",
            "infra_ai",
        ],
    },
    "cripto": {
        "name": "Cripto, Stablecoins & Ativos Digitais",
        "weight": 0.10,
        "primary_agents": ["MERCADO", "FUNDING"],
        "keywords": [
            "stablecoin", "usdc", "usdt", "dai",
            "drex", "cbdc", "moeda digital",
            "tokenização", "rwa", "real world assets",
            "defi", "decentralized finance",
            "blockchain", "ethereum", "solana",
        ],
        "filter_questions": [
            "Tem dados de volume ou comparativo com rails tradicionais?",
            "Inclui contexto regulatório LATAM?",
            "É sobre infraestrutura, não especulação de preço?",
        ],
        "sub_territories": [
            "stablecoins_infra",
            "cbdc_drex",
            "tokenizacao",
            "defi_tradfi",
        ],
    },
    "engenharia": {
        "name": "Engenharia, Arquitetura & Infraestrutura",
        "weight": 0.20,
        "primary_agents": ["CÓDIGO"],
        "keywords": [
            "arquitetura", "microservices", "monolith", "stack",
            "aws", "gcp", "azure", "cloud", "kubernetes", "docker",
            "devops", "sre", "observability", "monitoring",
            "lgpd", "security", "compliance", "mtls",
            "5g", "edge computing", "latência",
        ],
        "filter_questions": [
            "É técnico + prático (não apenas conceitual)?",
            "Tem dados ou benchmarks concretos?",
            "É útil para CTOs/senior engineers tomarem decisões?",
        ],
        "sub_territories": [
            "arquitetura_startups",
            "cloud_infra",
            "devops_sre",
            "seguranca_lgpd",
            "conectividade",
        ],
    },
    "venture": {
        "name": "Venture Capital & Funding LATAM",
        "weight": 0.10,
        "primary_agents": ["FUNDING", "INDEX"],
        "keywords": [
            "funding", "investment", "venture capital", "vc",
            "seed", "series a", "series b", "round",
            "investor", "fundo", "capital",
            "m&a", "acquisition", "exit", "ipo",
            "ecosystem", "startup", "unicórnio",
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
    "green_agritech": {
        "name": "Green Tech, AgriTech & Impacto",
        "weight": 0.05,
        "primary_agents": ["MERCADO", "RADAR"],
        "keywords": [
            "agritech", "agro", "agricultura", "foodtech",
            "climate tech", "esg", "sustentabilidade",
            "crédito de carbono", "carbon credit",
            "inclusão social", "impacto social",
            "edtech", "requalificação",
        ],
        "filter_questions": [
            "Tem ângulo de vantagem comparativa LATAM?",
            "Mostra dados de impacto ou adoção?",
            "Vai além de social-impact storytelling?",
        ],
        "sub_territories": [
            "agritech_foodtech",
            "climate_esg",
            "tech_inclusao",
        ],
    },
}

# Meta-território: Regulação (transversal)
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
        "name": "Se alinha com um dos 6 territórios",
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
    "press release sem análise",
    "opinião sem dados",
    "motivational content",
    "evento como jornalismo social",
    "hype sem substância",
    "tutorial básico",
    "futuro sem presente",
]


def get_territory_weight(territory_key: str) -> float:
    """Get editorial weight for a territory (0.0 to 1.0)."""
    return EDITORIAL_TERRITORIES.get(territory_key, {}).get("weight", 0.0)


def get_primary_agents_for_territory(territory_key: str) -> List[str]:
    """Get list of primary agents responsible for a territory."""
    return EDITORIAL_TERRITORIES.get(territory_key, {}).get("primary_agents", [])


def get_territory_keywords(territory_key: str) -> List[str]:
    """Get keyword list for territory classification."""
    return EDITORIAL_TERRITORIES.get(territory_key, {}).get("keywords", [])
