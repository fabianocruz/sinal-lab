"""LLM-powered editorial writer for SINTESE newsletter.

Uses the shared LLMClient to generate editorial content for the
Sinal Semanal newsletter:
  - Newsletter intro paragraph (week's narrative arc)
  - Section intros (editorial commentary per category)
  - Rewritten item summaries (contextualized for LATAM audience)

Architecture:
    synthesizer.py (orchestrator)
    ├── writer.py           <- LLM editorial content (this module)
    │   ├── write_newsletter_intro()   -> 1 API call
    │   └── write_section_content()    -> 1 API call per section
    └── format_item_markdown()         <- template formatting (existing)

Gracefully falls back (returns None) when the LLM client is unavailable
or API calls fail, allowing the synthesizer to use template-based output.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from apps.agents.base.llm import LLMClient, strip_code_fences
from apps.agents.sintese.synthesizer import NewsletterSection

logger = logging.getLogger(__name__)


# Editorial voice shared across all LLM calls
SYSTEM_PROMPT = (
    "Voce e o editor-chefe da newsletter Sinal Semanal, publicada pela plataforma Sinal.lab.\n\n"
    "Sua audiencia: fundadores tecnicos, CTOs e engenheiros seniores na America Latina (LATAM).\n\n"
    "Estilo editorial:\n"
    "- Tom analitico e direto, sem hype ou marketing\n"
    "- Foque em dados, tendencias e implicacoes praticas\n"
    "- Contextualize para o ecossistema tech LATAM (Brasil, Mexico, Colombia, Chile, Argentina)\n"
    "- Use linguagem tecnica quando apropriado, mas seja acessivel\n"
    "- Nunca use frases motivacionais ou cliches de startup\n"
    "- Prefira verbos ativos e frases curtas\n"
    "- Escreva em portugues brasileiro (PT-BR)\n\n"
    "O que NAO fazer:\n"
    "- Nao use emojis\n"
    "- Nao use 'revolucionario', 'disruptivo', 'game-changer' ou jargao de marketing\n"
    "- Nao faca previsoes vagas sobre o futuro\n"
    "- Nao seja condescendente com a audiencia tecnica"
)


@dataclass
class SectionContent:
    """LLM-generated content for a newsletter section."""

    intro: str  # 2-3 sentence editorial intro for the section
    summaries: list[str]  # One rewritten summary per item (same order as input)


class SinteseWriter:
    """LLM-powered editorial writer for the SINTESE newsletter.

    Uses LLMClient to generate editorial content. Falls back gracefully
    (returns None) when the client is unavailable or calls fail.
    """

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client if client is not None else LLMClient()

    @property
    def is_available(self) -> bool:
        """Check if the writer can generate content."""
        return self._client.is_available

    def write_newsletter_intro(
        self,
        sections: list[NewsletterSection],
        edition_number: int,
    ) -> Optional[str]:
        """Generate the newsletter intro paragraph.

        Args:
            sections: Grouped newsletter sections with items.
            edition_number: Edition number for the newsletter.

        Returns:
            Intro paragraph string, or None if generation fails.
        """
        if not sections:
            return None

        if not self.is_available:
            return None

        sections_summary = self._build_sections_summary(sections)

        user_prompt = (
            f"Escreva um paragrafo de introducao (3-5 frases) para a edicao "
            f"#{edition_number} do Sinal Semanal.\n\n"
            f"A newsletter desta semana cobre os seguintes temas:\n\n"
            f"{sections_summary}\n\n"
            f"Direcoes:\n"
            f"- Identifique o fio narrativo que conecta os destaques da semana\n"
            f"- Mencione 1-2 tendencias ou temas dominantes\n"
            f"- Seja factual e especifico (cite numeros quando disponivel)\n"
            f"- Termine com uma frase que convide a leitura\n"
            f"- NAO use saudacao ('Ola', 'Caro leitor') — va direto ao ponto\n"
            f"- Retorne APENAS o paragrafo, sem titulo ou formatacao extra"
        )

        result = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
        )

        if not result or not result.strip():
            logger.warning("LLM returned empty intro for edition #%d", edition_number)
            return None

        return result.strip()

    def write_section_content(
        self,
        section: NewsletterSection,
    ) -> Optional[SectionContent]:
        """Generate editorial content for a newsletter section.

        One API call per section that generates:
        - intro: 2-3 sentence editorial commentary
        - summaries: rewritten summary for each item

        Args:
            section: A grouped newsletter section with items.

        Returns:
            SectionContent or None if generation fails.
        """
        if not section.items:
            return None

        if not self.is_available:
            return None

        items_detail = self._build_items_detail(section.items)
        item_count = len(section.items)

        user_prompt = (
            f'Gere conteudo editorial para a secao "{section.heading}" '
            f"da newsletter Sinal Semanal.\n\n"
            f"Itens desta secao:\n\n"
            f"{items_detail}\n\n"
            f"Retorne um JSON valido com esta estrutura exata:\n"
            f'{{\n'
            f'  "intro": "Paragrafo de 2-3 frases introduzindo os temas desta secao. '
            f'Identifique padroes ou tendencias entre os itens.",\n'
            f'  "summaries": [\n'
            f'    "Resumo contextualizado do item 1 (2-3 frases). '
            f'Explique por que e relevante para a audiencia LATAM.",\n'
            f'    "Resumo contextualizado do item 2 (2-3 frases)."\n'
            f"  ]\n"
            f"}}\n\n"
            f"Regras:\n"
            f'- O array "summaries" DEVE ter exatamente {item_count} elemento(s), '
            f"um por item, na mesma ordem\n"
            f"- Cada resumo deve contextualizar o item para CTOs e fundadores no Brasil/LATAM\n"
            f"- Adicione contexto que a fonte original pode nao ter "
            f"(ex: comparacao com mercado LATAM)\n"
            f"- Nao repita o titulo do item no resumo\n"
            f"- Retorne APENAS o JSON, sem texto antes ou depois"
        )

        # Scale max_tokens based on item count: ~200 tokens per summary + 150 for intro + buffer
        max_tokens = max(1024, item_count * 200 + 400)

        raw = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=max_tokens,
        )

        if not raw:
            logger.warning("LLM returned empty content for section '%s'", section.heading)
            return None

        return self._parse_section_json(raw, section.heading, item_count)

    def _build_sections_summary(self, sections: list[NewsletterSection]) -> str:
        """Build a summary of all sections for the intro prompt."""
        lines: list[str] = []
        for section in sections:
            lines.append(f"## {section.heading} ({len(section.items)} itens)")
            for item in section.items:
                lines.append(f'- "{item.item.title}" ({item.item.source_name})')
            lines.append("")
        return "\n".join(lines)

    def _build_items_detail(self, items: list) -> str:
        """Build detailed item descriptions for a section prompt."""
        lines: list[str] = []
        for i, scored_item in enumerate(items, 1):
            item = scored_item.item
            lines.append(f'{i}. "{item.title}" (Fonte: {item.source_name})')
            lines.append(f"   URL: {item.url}")
            summary = item.summary or "Sem resumo disponivel."
            lines.append(f"   Resumo original: \"{summary}\"")
            lines.append("")
        return "\n".join(lines)

    def _parse_section_json(
        self,
        raw: str,
        heading: str,
        expected_count: int,
    ) -> Optional[SectionContent]:
        """Parse and validate the JSON response for a section."""
        cleaned = strip_code_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse JSON for section '%s': %.100s", heading, raw
            )
            return None

        intro = data.get("intro")
        summaries = data.get("summaries")

        if not isinstance(intro, str) or not isinstance(summaries, list):
            logger.warning("Invalid JSON structure for section '%s'", heading)
            return None

        if len(summaries) != expected_count:
            logger.warning(
                "Summary count mismatch for section '%s': expected %d, got %d",
                heading, expected_count, len(summaries),
            )
            return None

        return SectionContent(intro=intro, summaries=summaries)
