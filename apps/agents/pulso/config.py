"""Configuration for the PULSO agent.

Defines persona, agent config, dimension weights, taxonomy, and
clustering parameters for social signal clustering and scoring.
"""

from __future__ import annotations

import re as _re

from apps.agents.base.config import AgentCategory, AgentConfig, AgentPersona

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

PULSO_PERSONA = AgentPersona(
    display_name="Sofia Reyes",
    role_title="Analista de Sinais Sociais",
    nationality="Colombiana",
    bio_short="Data scientist especializada em clustering e scoring de sinais sociais para inteligencia de mercado",
    avatar_filename="sofia-reyes.jpg",
)

# ---------------------------------------------------------------------------
# Agent config
# ---------------------------------------------------------------------------

PULSO_CONFIG = AgentConfig(
    agent_name="pulso",
    agent_category=AgentCategory.DATA,
    version="0.1.0",
    description="Social signal clustering, 8-dimension scoring, and weekly pulse generation",
    data_sources=[],  # PULSO receives signals from VOZES, no direct sources
    schedule_cron="0 9 * * 1",  # Monday 9am UTC (after VOZES at 8am)
    output_content_type="ANALYSIS",
    min_confidence_to_publish=0.3,
    max_items_per_run=2000,
    persona=PULSO_PERSONA,
)

# ---------------------------------------------------------------------------
# Thematic taxonomy (12 themes)
# ---------------------------------------------------------------------------

SIGNAL_TAXONOMY = {
    "AI": {
        "subtemas": [
            "AI agents",
            "LLM infrastructure",
            "AI safety and governance",
            "Open source AI",
            "AI developer tools",
            "Multimodal AI",
            "Edge AI and on-device",
            "AI coding assistants",
        ],
        "narratives": [
            "AI replacing analysts",
            "open source catching up to closed models",
            "AI regulation accelerating",
            "enterprise AI ROI reality check",
        ],
    },
    "Fintech": {
        "subtemas": [
            "Payments infrastructure",
            "Embedded finance",
            "Lending and credit",
            "Neobanks",
            "Crypto and DeFi",
            "Insurtech",
            "Wealthtech",
            "Cross-border payments",
            "Open banking",
            "BaaS",
        ],
        "narratives": [
            "B2B payments infrastructure",
            "open banking monetization",
            "stablecoin rails for LATAM",
            "embedded finance as default",
        ],
    },
    "AI in Banking": {
        "subtemas": [
            "AI agents for compliance",
            "KYC automation",
            "Underwriting copilots",
            "Fraud detection AI",
            "AML monitoring",
            "Core banking modernization",
            "Model risk governance",
            "GenAI compliance",
            "Voice AI in collections",
        ],
        "narratives": [
            "banks adopting copilots",
            "agentic compliance workflows",
            "AI underwriting replacing FICO",
            "real-time fraud with LLMs",
        ],
    },
    "Funding": {
        "subtemas": [
            "Seed rounds",
            "Series A-C",
            "Late stage and pre-IPO",
            "IPO and SPAC",
            "M&A and exits",
            "Valuations",
            "Down rounds and cram-downs",
            "Secondary markets",
        ],
        "narratives": [
            "LATAM funding recovery",
            "mega-rounds returning",
            "bridge rounds as new normal",
            "AI startups commanding premium valuations",
        ],
    },
    "VC": {
        "subtemas": [
            "Fund raises",
            "Investment theses",
            "LP/GP dynamics",
            "Angel investing",
            "Corporate venture",
            "Accelerators and incubators",
            "Portfolio strategy",
            "VC in LATAM",
        ],
        "narratives": [
            "VCs returning to LATAM",
            "solo GP funds rising",
            "corporate VC pullback",
            "AI-native fund strategies",
        ],
    },
    "HealthTech": {
        "subtemas": [
            "Telemedicine",
            "Clinical AI and diagnostics",
            "Wearables and remote monitoring",
            "Health data interoperability",
            "Pharma and biotech AI",
            "Mental health tech",
            "Hospital automation",
            "Health insurance tech",
        ],
        "narratives": [
            "AI diagnostics matching specialists",
            "telemedicine post-pandemic normalization",
            "wearable data as clinical evidence",
            "health AI regulation tightening",
        ],
    },
    "DevTools": {
        "subtemas": [
            "Developer experience",
            "Open source projects",
            "Observability and monitoring",
            "CI/CD and deployment",
            "API platforms",
            "Low-code and no-code",
            "Infrastructure as code",
            "AI-powered dev tools",
        ],
        "narratives": [
            "AI coding assistants disrupting IDEs",
            "observability consolidation",
            "open source sustainability crisis",
            "platform engineering as discipline",
        ],
    },
    "Startup Ops": {
        "subtemas": [
            "Hiring and talent",
            "Company culture",
            "Scaling operations",
            "Layoffs and restructuring",
            "Pivots and strategy shifts",
            "Founder mental health",
            "Remote work and async",
            "Go-to-market strategy",
        ],
        "narratives": [
            "LATAM talent arbitrage",
            "founder-led sales comeback",
            "lean teams with AI automation",
            "remote-first as competitive advantage",
        ],
    },
    "Cybersecurity": {
        "subtemas": [
            "AppSec and DevSecOps",
            "Identity and access management",
            "Data privacy and LGPD",
            "Cloud security",
            "AI security threats",
            "Ransomware and incident response",
            "Zero trust architecture",
            "Compliance automation",
        ],
        "narratives": [
            "AI-powered attacks escalating",
            "LGPD enforcement intensifying",
            "security as board-level priority",
            "identity as new perimeter",
        ],
    },
    "Regulation": {
        "subtemas": [
            "Banco Central policies",
            "CVM and securities",
            "Sandbox programs",
            "Open banking rules",
            "AI regulation",
            "Data protection (LGPD)",
            "Tax and crypto regulation",
            "Cross-border compliance",
        ],
        "narratives": [
            "Brazil leading LATAM fintech regulation",
            "AI Act impact on LATAM",
            "sandbox graduates scaling",
            "regulatory arbitrage between countries",
        ],
    },
    "RetailTech": {
        "subtemas": [
            "E-commerce platforms",
            "Marketplace infrastructure",
            "Last-mile logistics",
            "Social commerce",
            "Retail media",
            "Omnichannel",
            "Quick commerce",
            "Supply chain tech",
        ],
        "narratives": [
            "Mercado Livre ecosystem expansion",
            "social commerce via WhatsApp",
            "retail media as profit center",
            "quick commerce profitability challenge",
        ],
    },
    "CleanTech": {
        "subtemas": [
            "Renewable energy",
            "Carbon credits and ESG",
            "Electric mobility",
            "Lithium and mining tech",
            "AgriTech sustainability",
            "Water and waste tech",
            "Green hydrogen",
            "Climate fintech",
        ],
        "narratives": [
            "Brazil as green hydrogen leader",
            "carbon credit tokenization",
            "lithium LATAM supply chain",
            "ESG reporting automation with AI",
        ],
    },
    "EdTech": {
        "subtemas": [
            "Online learning platforms",
            "AI tutoring",
            "Upskilling and reskilling",
            "Corporate training",
            "EdTech for K-12",
            "Language learning",
            "Credentialing and certificates",
            "Learning analytics",
        ],
        "narratives": [
            "AI tutors replacing traditional courses",
            "corporate upskilling for AI era",
            "micro-credentials gaining employer trust",
            "LATAM edtech consolidation",
        ],
    },
}

# ---------------------------------------------------------------------------
# Signal scoring parameters (adjusted from social_signals)
# ---------------------------------------------------------------------------

SIGNAL_DIMENSIONS = [
    "volume",
    "velocity",
    "authority_concentration",
    "cross_platform_propagation",
    "sentiment_shift",
    "new_entrants",
    "narrative_maturity",
    "commercial_signals",
]

# Adjusted weights: velocity reduced (was too dominant), authority and
# cross-platform increased (more important for signal quality).
DIMENSION_WEIGHTS = {
    "volume": 0.10,
    "velocity": 0.15,                    # was 0.20
    "authority_concentration": 0.20,      # was 0.15
    "cross_platform_propagation": 0.20,   # was 0.15
    "sentiment_shift": 0.10,
    "new_entrants": 0.10,
    "narrative_maturity": 0.10,
    "commercial_signals": 0.05,           # was 0.10
}

# Minimum composite score for a cluster to be included in the pulse.
MIN_CLUSTER_COMPOSITE_SCORE = 0.25  # was 0.3

# ---------------------------------------------------------------------------
# Clustering parameters (critical quality fixes)
# ---------------------------------------------------------------------------

# Distance threshold for TF-IDF agglomerative clustering.
# Lowered from 0.7 to 0.35 — the #1 fix for repetitive clusters.
CLUSTERING_DISTANCE_THRESHOLD = 0.35

# Distance threshold for embedding-based clustering.
# Lowered from 0.5 to 0.3.
EMBEDDING_DISTANCE_THRESHOLD = 0.3

# Maximum cluster size before re-splitting.
MAX_CLUSTER_SIZE = 80  # was 150

# Minimum signals per cluster (filters out noise).
MIN_CLUSTER_SIZE = 5

# Cosine similarity threshold for merging similar clusters.
MERGE_SIMILARITY_THRESHOLD = 0.85

# ---------------------------------------------------------------------------
# Cluster name blocklist
# ---------------------------------------------------------------------------

CLUSTER_NAME_BLOCKLIST: list[str] = [
    # Generic / no-theme clusters
    "sem tema comum",
    "sem tema claro",
    "diversas sem tema",
    "diversas de redes sociais",
    "diversas em redes sociais",
    "diversas sobre",
    "publicações diversas",
    "postagens diversas",
    "publicações virais",
    "conteúdo variado",
    "conteúdos diversos",
    "tópicos variados",
    "notícias diversas",
    # Off-topic content
    "política e poder",
    "política e sociedade",
    "política, economia e mídia",
    "política, sociedade",
    "política e mercados",
    "poder global",
    "geopolítica",
    "previsões políticas",
    "apostas especulativas",
    "regulação ambiental",
    "ciência e sociedade",
    "cinema e inteligência artificial",
    "exploradores, amazônia",
    "revisão por pares",
    "acadêmicas",
    # Noise from podcasts/RSS
    "episódios do podcast",
]

# Pre-compiled regex for efficient filtering.
CLUSTER_NAME_BLOCKLIST_RE = _re.compile(
    "|".join(_re.escape(p) for p in CLUSTER_NAME_BLOCKLIST),
    _re.IGNORECASE,
)
