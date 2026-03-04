"""Entity name extraction from article titles.

Extracts company/entity names using lightweight heuristics so that
synthesizers can apply a frequency cap (max N articles per entity).

No NLP/NER required -- relies on:
1. ALL-CAPS words (3+ chars): EFEX, KAVAK, VTEX, TOTVS
2. Capitalized words immediately before funding verbs
3. Normalized to lowercase for comparison
"""

import re
from typing import List

# Words that are ALL-CAPS but NOT entity names.
# Keep this short -- only add well-known false positives.
_ALLCAPS_STOPWORDS: set[str] = {
    "ai", "ml", "api", "ceo", "cto", "cfo", "coo", "cio",
    "ipo", "etf", "nft", "usa", "nyc", "gdp", "b2b", "b2c",
    "saas", "paas", "iaas", "defi", "dao", "llm", "rag",
    "aws", "gcp", "sql", "gpu", "cpu", "ram", "ios",
    "html", "css", "http", "rest", "sdk", "vps", "vpn",
    "eur", "usd", "brl", "gbp", "jpy",
    "latam", "emea", "apac",
    "pre", "via", "the", "and", "for",
}

# Verbs that typically follow a company name in funding headlines.
_FUNDING_VERBS_RE = re.compile(
    r"\b(?:raises?|raised|fecha|capta|levanta|closes?|closed"
    r"|secures?|secured|lands?|landed|gets?|nabs?|bags?)\b",
    re.IGNORECASE,
)

# Pattern: Capitalized word(s) right before a funding verb.
# Matches "Kavak raises", "Stone fecha", "Nu Holdings closes".
_PRE_VERB_ENTITY_RE = re.compile(
    r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+"
    r"(?:raises?|raised|fecha|capta|levanta|closes?|closed"
    r"|secures?|secured|lands?|landed|gets?|nabs?|bags?)\b",
)

# Common title-case words that are NOT entity names.
_TITLECASE_STOPWORDS: set[str] = {
    "the", "new", "how", "why", "what", "who", "when", "where",
    "big", "top", "best", "first", "next", "last", "latest",
    "series", "round", "seed", "pre", "post",
    "startup", "startups", "company", "companies",
    "tech", "digital", "global", "capital", "venture",
    "funding", "investment", "report", "weekly",
    "south", "north", "latin", "america",
    "google", "apple", "microsoft", "amazon", "meta", "openai",
    "anthropic", "nvidia",
}


def extract_entities(title: str) -> List[str]:
    """Extract company/entity names from an article title.

    Returns lowercase normalized entity names suitable for frequency
    counting. Intentionally simple -- catches obvious cases like
    ALL-CAPS brand names (EFEX, KAVAK) and capitalized names before
    funding verbs (Kavak raises, Stone fecha).

    Args:
        title: Article title string.

    Returns:
        List of lowercase entity names (deduplicated, order-preserved).
    """
    if not title or not title.strip():
        return []

    entities: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        normalized = name.lower().strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            entities.append(normalized)

    # Heuristic 1: ALL-CAPS words of 3+ characters.
    for match in re.finditer(r"\b([A-Z]{3,})\b", title):
        word = match.group(1)
        if word.lower() not in _ALLCAPS_STOPWORDS:
            _add(word)

    # Heuristic 2: Capitalized word(s) immediately before a funding verb.
    for match in _PRE_VERB_ENTITY_RE.finditer(title):
        candidate = match.group(1)
        # Skip single common words
        if candidate.lower() in _TITLECASE_STOPWORDS:
            continue
        _add(candidate)

    return entities
