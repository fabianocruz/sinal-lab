"""Sector classification for MERCADO agent.

Classifies companies into sectors based on keywords in description and tech stack.
"""

import logging
from typing import Optional

from apps.agents.mercado.collector import CompanyProfile

logger = logging.getLogger(__name__)

# Sector classification keywords
SECTOR_KEYWORDS = {
    "Fintech": [
        "pagamento",
        "payment",
        "credito",
        "credit",
        "bank",
        "banco",
        "pix",
        "financial",
        "financeira",
        "cartão",
        "card",
        "wallet",
        "carteira",
    ],
    "HealthTech": [
        "saude",
        "health",
        "telemedicine",
        "telemedicina",
        "clinica",
        "clinic",
        "hospital",
        "medical",
        "medico",
        "pharma",
        "farmacia",
    ],
    "Edtech": [
        "educacao",
        "education",
        "ensino",
        "learning",
        "escola",
        "school",
        "curso",
        "course",
        "estudante",
        "student",
    ],
    "E-commerce": [
        "ecommerce",
        "e-commerce",
        "marketplace",
        "loja",
        "store",
        "varejo",
        "retail",
        "compra",
        "shopping",
    ],
    "SaaS": [
        "software",
        "platform",
        "saas",
        "enterprise",
        "cloud",
        "api",
        "automation",
        "automação",
    ],
    "Logistics": [
        "logistica",
        "logistics",
        "entrega",
        "delivery",
        "transporte",
        "transport",
        "frete",
        "shipping",
    ],
    "Agritech": [
        "agricultura",
        "agriculture",
        "agro",
        "farm",
        "fazenda",
        "rural",
        "crop",
        "plantio",
    ],
    "PropTech": [
        "imovel",
        "real estate",
        "property",
        "propriedade",
        "aluguel",
        "rent",
        "moradia",
        "housing",
    ],
}


def classify_sector(profile: CompanyProfile) -> Optional[str]:
    """Classify company sector based on keywords.

    Checks both the org description and name/slug for keyword matches.
    Name matches count less (0.5 per hit) to avoid over-weighting short names.

    Args:
        profile: CompanyProfile to classify

    Returns:
        Sector name (e.g., "Fintech") or None if unclassified
    """
    # Build searchable text from description and name
    text_parts = []
    if profile.description:
        text_parts.append(profile.description.lower())
    if profile.slug:
        text_parts.append(profile.slug.lower())
    if profile.name:
        text_parts.append(profile.name.lower())

    if not text_parts:
        return None

    searchable_text = " ".join(text_parts)

    # Check each sector's keywords
    sector_scores: dict[str, float] = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in searchable_text)
        if score > 0:
            sector_scores[sector] = score

    if not sector_scores:
        return None

    # Return sector with highest score
    best_sector = max(sector_scores.items(), key=lambda x: x[1])
    logger.debug(
        "Classified %s as %s (score: %d)",
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
