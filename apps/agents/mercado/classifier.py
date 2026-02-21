"""Sector classification for MERCADO agent.

Classifies companies into sectors based on keywords in description and tech stack.
"""

import logging
from typing import Optional

from apps.agents.mercado.collector import CompanyProfile

logger = logging.getLogger(__name__)

# Sector classification keywords
SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Fintech": [
        "pagamento", "payment", "credito", "credit",
        "bank", "banco", "pix", "financial", "financeira",
        "cartão", "card", "wallet", "carteira",
        "fintech", "neobank", "neobanco", "lending", "emprestimo",
        "investimento", "investment", "crypto", "blockchain",
        "remessa", "remittance", "checkout",
    ],
    "HealthTech": [
        "saude", "health", "telemedicine", "telemedicina",
        "clinica", "clinic", "hospital", "medical", "medico",
        "pharma", "farmacia",
    ],
    "Edtech": [
        "educacao", "education", "ensino", "learning",
        "escola", "school", "curso", "course",
        "estudante", "student",
    ],
    "E-commerce": [
        "ecommerce", "e-commerce", "marketplace",
        "loja", "store", "varejo", "retail",
        "compra", "shopping",
        "shop", "vendas", "sales", "catalog", "catalogo",
        "inventory", "estoque", "fulfillment",
    ],
    "SaaS": [
        "saas", "enterprise",
        "automation", "automação",
        "crm", "erp", "b2b",
        "dashboard", "workflow", "integration",
    ],
    "Logistics": [
        "logistica", "logistics", "entrega", "delivery",
        "transporte", "transport", "frete", "shipping",
    ],
    "Agritech": [
        "agricultura", "agriculture", "agro", "farm",
        "fazenda", "rural", "crop", "plantio",
    ],
    "PropTech": [
        "imovel", "real estate", "property", "propriedade",
        "aluguel", "rent", "moradia", "housing",
    ],
    "DevTools": [
        "developer", "devops", "ci/cd", "cicd", "pipeline",
        "infrastructure", "infra", "microservice", "sdk",
        "open-source", "open source", "monitoring",
        "observability", "deployment", "container", "kubernetes",
        "terraform", "serverless",
    ],
    "Cybersecurity": [
        "security", "segurança", "seguridad", "cyber",
        "encryption", "criptografia", "firewall",
        "vulnerability", "pentest", "authentication",
        "identity", "identidade", "fraud", "fraude",
    ],
    "CleanTech": [
        "solar", "renewable", "renovavel", "energia",
        "energy", "sustentavel", "sustainable", "carbono",
        "carbon", "climate", "clima", "cleantech",
        "reciclagem", "recycling",
    ],
    "HRTech": [
        "recruiting", "recrutamento",
        "talent", "talento", "hiring", "contratacao",
        "payroll", "folha", "workforce",
    ],
    "InsurTech": [
        "seguro", "insurance", "insurtech",
        "apolice", "sinistro", "corretora",
    ],
    "LegalTech": [
        "juridico", "legal", "advogado", "lawyer",
        "contrato", "contract", "compliance",
        "regulatorio", "regulatory", "lawtech", "legaltech",
    ],
}


def classify_sector(profile: CompanyProfile) -> Optional[str]:
    """Classify company sector based on weighted keyword matching.

    Uses three text sources with different weights:
    - Description: 1.0 per keyword hit (most reliable)
    - Tags: 0.7 per keyword hit (from Crunchbase/LinkedIn categories)
    - Name/slug: 0.5 per keyword hit (less reliable for short names)

    Args:
        profile: CompanyProfile to classify

    Returns:
        Sector name (e.g., "Fintech") or None if unclassified
    """
    description_text = (profile.description or "").lower()
    name_text = ((profile.slug or "") + " " + (profile.name or "")).lower()
    tags_text = " ".join(t.lower() for t in profile.tags) if profile.tags else ""

    if not description_text and not name_text.strip() and not tags_text:
        return None

    sector_scores: dict[str, float] = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if kw in description_text:
                score += 1.0
            if kw in name_text:
                score += 0.5
            if kw in tags_text:
                score += 0.7
        if score > 0:
            sector_scores[sector] = score

    if not sector_scores:
        return None

    best_sector = max(sector_scores.items(), key=lambda x: x[1])
    logger.debug(
        "Classified %s as %s (score: %.1f)",
        profile.name,
        best_sector[0],
        best_sector[1],
    )

    return best_sector[0]


def generate_tags(profile: CompanyProfile) -> list[str]:
    """Generate tags for a company profile.

    Args:
        profile: CompanyProfile to tag

    Returns:
        List of tags extracted from description and tech stack
    """
    tags = []

    # Add sector as tag if classified
    if profile.sector:
        tags.append(profile.sector.lower())

    # Add tech stack as tags
    for tech in profile.tech_stack:
        tags.append(tech.lower())

    # Add country/city as tags
    if profile.city:
        tags.append(profile.city.lower().replace(" ", "-"))
    if profile.country:
        tags.append(profile.country.lower())

    # Deduplicate
    tags = list(set(tags))

    return tags


def classify_all_profiles(profiles: list[CompanyProfile]) -> list[CompanyProfile]:
    """Classify sector and generate tags for all profiles.

    Args:
        profiles: List of CompanyProfile objects

    Returns:
        List of classified CompanyProfile objects
    """
    for profile in profiles:
        profile.sector = classify_sector(profile)
        profile.tags = generate_tags(profile)

    classified_count = sum(1 for p in profiles if p.sector is not None)
    logger.info("Classified %d/%d profiles into sectors", classified_count, len(profiles))

    return profiles
