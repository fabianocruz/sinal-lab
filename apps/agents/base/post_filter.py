"""Post-generation content filter for agent outputs.

Detects and removes items where the LLM's own analysis concludes
the item is irrelevant, low-quality, or not worth publishing.

This catches cases where the scorer/synthesizer included an item
but the writer (LLM) realized during analysis that it's not useful.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Patterns that indicate the LLM rejected the item in its own analysis.
# These are checked against the blockquote/analysis text, not the title.
REJECTION_PATTERNS = [
    re.compile(r"nao ha razao.+?investigar", re.I),
    re.compile(r"nao ha insight.+?acionavel", re.I),
    re.compile(r"filtrem e sigam em frente", re.I),
    re.compile(r"pode ignorar sem custo", re.I),
    re.compile(r"nao invista tempo avaliando", re.I),
    re.compile(r"nao ha caso de uso.+?que justifique", re.I),
    re.compile(r"recomendacao e direta.+?nao", re.I),
    re.compile(r"nao merece atencao", re.I),
    re.compile(r"sem relevancia", re.I),
]


def filter_rejected_items(body_md: str) -> str:
    """Remove items from a Markdown report where the analysis self-rejects.

    Parses numbered items (e.g., "**3. [Title](url)** [TAG]\\n> analysis")
    and removes any where the analysis matches a rejection pattern.

    Args:
        body_md: Full Markdown body (no frontmatter).

    Returns:
        Filtered body with rejected items removed and numbers adjusted.
    """
    # Split into sections by "---" dividers
    sections = body_md.split("\n---\n")
    filtered_sections = []

    for section in sections:
        # Find all numbered items in this section
        # Pattern: **N. [Title](url)** [TAG]\n*Source*\n> Analysis
        items = re.split(r"(?=^\*\*\d+\.)", section, flags=re.MULTILINE)

        kept_items = []
        removed = 0

        for item in items:
            # Check if this is a numbered item
            if not re.match(r"^\*\*\d+\.", item):
                kept_items.append(item)
                continue

            # Check the blockquote/analysis for rejection patterns
            blockquote = re.search(r">\s*(.+?)(?=\n\n|\n\*\*|\Z)", item, re.DOTALL)
            if blockquote:
                analysis = blockquote.group(1)
                is_rejected = any(p.search(analysis) for p in REJECTION_PATTERNS)
                if is_rejected:
                    title_match = re.search(r"\[([^\]]+)\]", item)
                    title = title_match.group(1) if title_match else "unknown"
                    logger.info("Post-filter removed: %s", title[:60])
                    removed += 1
                    continue

            kept_items.append(item)

        if removed > 0:
            # Renumber remaining items
            counter = 0
            renumbered = []
            for item in kept_items:
                if re.match(r"^\*\*\d+\.", item):
                    counter += 1
                    item = re.sub(r"^\*\*\d+\.", f"**{counter}.", item)
                renumbered.append(item)
            filtered_sections.append("".join(renumbered))
            logger.info("Section: removed %d self-rejected items", removed)
        else:
            filtered_sections.append(section)

    return "\n---\n".join(filtered_sections)
