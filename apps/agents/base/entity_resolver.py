"""Cross-agent entity resolution for EvidenceItems.

Deduplicates evidence collected by multiple agents using URL matching
and fuzzy title similarity. When the same article/event is found by
multiple agents, it's merged into a single ResolvedEntity with boosted
confidence.

Usage:
    from apps.agents.base.entity_resolver import resolve_entities

    resolved = resolve_entities(evidence_items)
    for entity in resolved:
        print(entity.canonical.title, entity.combined_confidence)
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from apps.agents.base.evidence import EvidenceItem


@dataclass
class ResolvedEntity:
    """A deduplicated entity with merged evidence from multiple agents."""

    canonical: EvidenceItem
    duplicates: List[EvidenceItem] = field(default_factory=list)
    combined_confidence: float = 0.0
    source_agents: List[str] = field(default_factory=list)


def _title_similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two titles using SequenceMatcher."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _find_match(
    item: EvidenceItem,
    groups: List[List[EvidenceItem]],
    url_exact: bool,
    title_similarity_threshold: float,
) -> Optional[int]:
    """Find an existing group that this item should be merged into.

    Returns group index or None.
    """
    for i, group in enumerate(groups):
        representative = group[0]

        # URL-based exact match
        if url_exact and item.content_hash == representative.content_hash:
            return i

        # Fuzzy title match — only across different agents.
        # Same-agent items with different URLs are genuinely different.
        group_agents = {g.agent_name for g in group}
        if item.agent_name not in group_agents:
            if _title_similarity(item.title, representative.title) >= title_similarity_threshold:
                return i

    return None


def resolve_entities(
    items: List[EvidenceItem],
    url_exact: bool = True,
    title_similarity_threshold: float = 0.85,
) -> List[ResolvedEntity]:
    """Deduplicate and merge EvidenceItems across agents.

    Args:
        items: List of evidence items from various agents.
        url_exact: If True, items with same content_hash are merged.
        title_similarity_threshold: Minimum title similarity (0-1) for merging.

    Returns:
        List of ResolvedEntity, each representing a unique piece of evidence.
    """
    if not items:
        return []

    # Group items by identity (URL or title similarity)
    groups: List[List[EvidenceItem]] = []

    for item in items:
        match_idx = _find_match(item, groups, url_exact, title_similarity_threshold)
        if match_idx is not None:
            groups[match_idx].append(item)
        else:
            groups.append([item])

    # Convert groups to ResolvedEntity
    resolved: List[ResolvedEntity] = []

    for group in groups:
        # Canonical = highest confidence
        sorted_group = sorted(group, key=lambda x: x.confidence, reverse=True)
        canonical = sorted_group[0]
        duplicates = sorted_group[1:]

        # Collect unique agent names
        source_agents = list(dict.fromkeys(item.agent_name for item in group))

        # Confidence boost: max + 0.1 per additional source
        max_conf = canonical.confidence
        num_sources = len(source_agents)
        combined = min(1.0, max_conf + 0.1 * (num_sources - 1))

        resolved.append(ResolvedEntity(
            canonical=canonical,
            duplicates=duplicates,
            combined_confidence=combined,
            source_agents=source_agents,
        ))

    return resolved
