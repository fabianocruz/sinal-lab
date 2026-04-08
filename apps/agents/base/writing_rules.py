"""Shared writing rules appended to all agent system prompts.

Import WRITING_RULES and append to your SYSTEM_PROMPT to ensure
consistent formatting across all agents.
"""

WRITING_RULES = (
    "\n\n## Regras de Escrita (obrigatorias)\n"
    "- NUNCA use em dash (caractere Unicode U+2014). Use virgula, ponto e virgula, "
    "dois pontos ou ponto para separar ideias.\n"
    "- NUNCA use en dash (U+2013). Use hifen simples (-) para intervalos numericos.\n"
    "- Escreva em portugues brasileiro, mas mantenha termos tecnicos em ingles "
    "(API, LLM, Series A, seed, etc.).\n"
    "- Nao use emojis no corpo do texto.\n"
    "- Nao inclua o frontmatter YAML no corpo do texto. O frontmatter e gerado separadamente.\n"
    "- Se voce nao tem informacao suficiente para analisar um item, nao o inclua. "
    "Prefira menos items com analise profunda a mais items com analise rasa.\n"
    "- Se sua propria analise conclui que um item nao e relevante, nao o publique.\n"
)
