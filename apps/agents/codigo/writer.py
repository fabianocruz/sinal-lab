"""LLM-powered editorial writer for CODIGO dev ecosystem reports.

Uses the shared LLMClient to generate editorial content for the
CODIGO Semanal report:
  - Report intro paragraph (week's developer ecosystem narrative arc)
  - Section intros (editorial commentary per category)
  - Rewritten signal summaries (contextualized for LATAM dev teams)

Architecture:
    synthesizer.py (orchestrator)
    ├── writer.py           <- LLM editorial content (this module)
    │   ├── write_report_intro()      -> 1 API call
    │   └── write_section_content()   -> 1 API call per section
    └── format_signal_markdown()      <- template formatting (existing)

Gracefully falls back (returns None) when the LLM client is unavailable
or API calls fail, allowing the synthesizer to use template-based output.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from apps.agents.base.llm import LLMClient, strip_code_fences
from apps.agents.codigo.synthesizer import ReportSection

logger = logging.getLogger(__name__)


# Editorial voice shared across all LLM calls
SYSTEM_PROMPT = (
    "Voce e o analista-chefe de ecossistema developer do relatorio CODIGO Semanal, "
    "publicado pela plataforma Sinal.lab.\n\n"
    "Sua audiencia: fundadores tecnicos, CTOs e engenheiros seniores na America Latina (LATAM).\n\n"
    "Estilo editorial:\n"
    "- Tom analitico e direto, sem hype ou marketing\n"
    "- Foque em adocao de frameworks, comparacao de ferramentas e tendencias dev\n"
    "- Explique o que bibliotecas e ferramentas em ascensao significam para times brasileiros/LATAM\n"
    "- Implicacoes praticas: o time deveria adotar isso? Por que sim ou por que nao?\n"
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
    """LLM-generated content for a report section."""

    intro: str  # 2-3 sentence editorial intro for the section
    summaries: list[str]  # One rewritten summary per signal (same order as input)


class CodigoWriter:
    """LLM-powered editorial writer for the CODIGO dev ecosystem report.

    Uses LLMClient to generate editorial content. Falls back gracefully
    (returns None) when the client is unavailable or calls fail.
    """

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client if client is not None else LLMClient()

    @property
    def is_available(self) -> bool:
        """Check if the writer can generate content."""
        return self._client.is_available

    def write_report_intro(
        self,
        sections: list[ReportSection],
        week_number: int,
    ) -> Optional[str]:
        """Generate the report intro paragraph.

        Args:
            sections: Grouped report sections with signals.
            week_number: Week number for the report.

        Returns:
            Intro paragraph string, or None if generation fails.
        """
        if not sections:
            return None

        if not self.is_available:
            return None

        sections_summary = self._build_sections_summary(sections)

        user_prompt = (
            f"Escreva um paragrafo de introducao (3-5 frases) para a semana "
            f"{week_number} do relatorio CODIGO Semanal.\n\n"
            f"O relatorio desta semana cobre os seguintes sinais do ecossistema dev:\n\n"
            f"{sections_summary}\n\n"
            f"Direcoes:\n"
            f"- Identifique o fio narrativo que conecta os destaques da semana\n"
            f"- Mencione 1-2 tendencias ou padroes dominantes no ecossistema dev\n"
            f"- Seja factual e especifico (cite linguagens, frameworks ou metricas quando disponivel)\n"
            f"- Termine com uma frase que convide a leitura\n"
            f"- NAO use saudacao ('Ola', 'Caro leitor') — va direto ao ponto\n"
            f"- Retorne APENAS o paragrafo, sem titulo ou formatacao extra"
        )

        result = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
        )

        if not result or not result.strip():
            logger.warning("LLM returned empty intro for week %d", week_number)
            return None

        return result.strip()

    def write_section_content(
        self,
        section: ReportSection,
    ) -> Optional[SectionContent]:
        """Generate editorial content for a report section.

        One API call per section that generates:
        - intro: 2-3 sentence editorial commentary
        - summaries: rewritten summary for each signal

        Args:
            section: A grouped report section with signals.

        Returns:
            SectionContent or None if generation fails.
        """
        if not section.signals:
            return None

        if not self.is_available:
            return None

        items_detail = self._build_items_detail(section.signals)
        signal_count = len(section.signals)

        user_prompt = (
            f'Gere conteudo editorial para a secao "{section.heading}" '
            f"do relatorio CODIGO Semanal.\n\n"
            f"Sinais desta secao:\n\n"
            f"{items_detail}\n\n"
            f"Retorne um JSON valido com esta estrutura exata:\n"
            f'{{\n'
            f'  "intro": "Paragrafo de 2-3 frases introduzindo os temas desta secao. '
            f'Identifique padroes de adocao ou tendencias entre os sinais.",\n'
            f'  "summaries": [\n'
            f'    "Resumo contextualizado do sinal 1 (2-3 frases). '
            f'Explique o impacto pratico para times dev no Brasil/LATAM.",\n'
            f'    "Resumo contextualizado do sinal 2 (2-3 frases)."\n'
            f"  ]\n"
            f"}}\n\n"
            f"Regras:\n"
            f'- O array "summaries" DEVE ter exatamente {signal_count} elemento(s), '
            f"um por sinal, na mesma ordem\n"
            f"- Cada resumo deve contextualizar o sinal para CTOs e engenheiros no Brasil/LATAM\n"
            f"- Inclua orientacao pratica: vale adotar? Em que cenarios?\n"
            f"- Nao repita o titulo do sinal no resumo\n"
            f"- Retorne APENAS o JSON, sem texto antes ou depois"
        )

        # Scale max_tokens based on signal count: ~200 tokens per summary + 150 for intro + buffer
        max_tokens = max(1024, signal_count * 200 + 400)

        raw = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=max_tokens,
        )

        if not raw:
            logger.warning("LLM returned empty content for section '%s'", section.heading)
            return None

        return self._parse_section_json(raw, section.heading, signal_count)

    def _build_sections_summary(self, sections: list[ReportSection]) -> str:
        """Build a summary of all sections for the intro prompt."""
        lines: list[str] = []
        for section in sections:
            lines.append(f"## {section.heading} ({len(section.signals)} sinais)")
            for analyzed in section.signals:
                lines.append(f'- "{analyzed.signal.title}" ({analyzed.signal.source_name})')
            lines.append("")
        return "\n".join(lines)

    def _build_items_detail(self, signals: list) -> str:
        """Build detailed signal descriptions for a section prompt."""
        lines: list[str] = []
        for i, analyzed in enumerate(signals, 1):
            sig = analyzed.signal
            lines.append(f'{i}. "{sig.title}" (Fonte: {sig.source_name})')
            lines.append(f"   URL: {sig.url}")
            summary = sig.summary or "Sem resumo disponivel."
            lines.append(f'   Resumo original: "{summary}"')
            if sig.language:
                lines.append(f"   Linguagem: {sig.language}")
            if analyzed.adoption_indicator:
                lines.append(f"   Adocao: {analyzed.adoption_indicator}")
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
