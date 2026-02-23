"""Sector normalization for LATAM startup data.

Maps source-specific sector/vertical strings from ABStartups, YC,
Crunchbase, and GitHub to canonical SECTOR_OPTIONS values matching
the frontend (apps/web/lib/company.ts).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical sector options — must stay in sync with apps/web/lib/company.ts
SECTOR_OPTIONS = [
    "Fintech",
    "E-commerce",
    "SaaS",
    "Healthtech",
    "Edtech",
    "Logistics",
    "Agritech",
    "AI/ML",
    "Proptech",
    "HR Tech",
]

_CANONICAL_LOWER = {s.lower(): s for s in SECTOR_OPTIONS}

# Aliases from various source vocabularies -> canonical value
SECTOR_ALIASES: dict[str, str] = {
    # --- Fintech ---
    "financial services": "Fintech",
    "banking": "Fintech",
    "finance": "Fintech",
    "payments": "Fintech",
    "insurance": "Fintech",
    "insurtech": "Fintech",
    "crypto": "Fintech",
    "blockchain": "Fintech",
    "defi": "Fintech",
    "neobank": "Fintech",
    "lending": "Fintech",
    "credit": "Fintech",
    "serviços financeiros": "Fintech",
    "finanças": "Fintech",
    "pagamentos": "Fintech",
    "seguros": "Fintech",
    "crédito": "Fintech",

    # --- E-commerce ---
    "ecommerce": "E-commerce",
    "e commerce": "E-commerce",
    "retail": "E-commerce",
    "marketplace": "E-commerce",
    "varejo": "E-commerce",
    "comércio eletrônico": "E-commerce",
    "loja virtual": "E-commerce",

    # --- SaaS ---
    "software": "SaaS",
    "developer tools": "SaaS",
    "devtools": "SaaS",
    "b2b": "SaaS",
    "enterprise": "SaaS",
    "productivity": "SaaS",
    "cloud": "SaaS",
    "infrastructure": "SaaS",

    # --- Healthtech ---
    "health": "Healthtech",
    "healthcare": "Healthtech",
    "health care": "Healthtech",
    "medical": "Healthtech",
    "biotech": "Healthtech",
    "telemedicine": "Healthtech",
    "digital health": "Healthtech",
    "saúde": "Healthtech",
    "medicina": "Healthtech",

    # --- Edtech ---
    "education": "Edtech",
    "learning": "Edtech",
    "e-learning": "Edtech",
    "elearning": "Edtech",
    "educação": "Edtech",
    "ensino": "Edtech",

    # --- Logistics ---
    "delivery": "Logistics",
    "supply chain": "Logistics",
    "transportation": "Logistics",
    "shipping": "Logistics",
    "fleet": "Logistics",
    "logística": "Logistics",
    "transporte": "Logistics",
    "entrega": "Logistics",

    # --- Agritech ---
    "agriculture": "Agritech",
    "farming": "Agritech",
    "agro": "Agritech",
    "agribusiness": "Agritech",
    "foodtech": "Agritech",
    "food": "Agritech",
    "agricultura": "Agritech",
    "agronegócio": "Agritech",

    # --- AI/ML ---
    "artificial intelligence": "AI/ML",
    "machine learning": "AI/ML",
    "deep learning": "AI/ML",
    "nlp": "AI/ML",
    "computer vision": "AI/ML",
    "inteligência artificial": "AI/ML",

    # --- Proptech ---
    "real estate": "Proptech",
    "property": "Proptech",
    "construction": "Proptech",
    "contech": "Proptech",
    "imobiliário": "Proptech",
    "imóveis": "Proptech",
    "construção": "Proptech",

    # --- HR Tech ---
    "human resources": "HR Tech",
    "recruitment": "HR Tech",
    "hiring": "HR Tech",
    "talent": "HR Tech",
    "hr": "HR Tech",
    "recursos humanos": "HR Tech",
    "recrutamento": "HR Tech",
}


def normalize_sector(raw_sector: Optional[str]) -> Optional[str]:
    """Map a source-specific sector string to a canonical SECTOR_OPTIONS value.

    Matching is case-insensitive. Checks in order:
    1. Exact match against canonical SECTOR_OPTIONS.
    2. Lookup in SECTOR_ALIASES.
    3. Substring match against alias keys (for composite sectors like
       "Financial Services & Payments").

    Args:
        raw_sector: Raw sector string from any data source (may be None).

    Returns:
        Canonical sector string from SECTOR_OPTIONS, or None if no match.
    """
    if not raw_sector:
        return None

    cleaned = raw_sector.strip()
    if not cleaned:
        return None

    lower = cleaned.lower()

    # 1. Exact canonical match (case-insensitive)
    if lower in _CANONICAL_LOWER:
        return _CANONICAL_LOWER[lower]

    # 2. Exact alias match
    if lower in SECTOR_ALIASES:
        return SECTOR_ALIASES[lower]

    # 3. Substring match — check if any alias key appears in the raw string
    for alias, canonical in SECTOR_ALIASES.items():
        if alias in lower:
            return canonical

    return None
