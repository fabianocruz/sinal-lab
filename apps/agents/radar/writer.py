"""LLM-powered editorial writer for RADAR trend reports.

Uses the shared LLMClient to generate editorial content for the
RADAR weekly trend intelligence report:
  - Report intro paragraph (week's trend narrative)
  - Section intros (editorial analysis per topic category)
  - Rewritten signal summaries (contextualized for LATAM audience)

Architecture:
    synthesizer.py (orchestrator)
    ├── writer.py           <- LLM editorial content (this module)
    │   ├── write_report_intro()     -> 1 API call
    │   └── write_section_content()  -> 1 API call per section
    └── format_signal_markdown()     <- template formatting (existing)

Gracefully falls back (returns None) when the LLM client is unavailable
or API calls fail, allowing the synthesizer to use template-based output.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from apps.agents.base.llm import LLMClient, strip_code_fences
from apps.agents.radar.synthesizer import TrendSection

logger = logging.getLogger(__name__)


# Editorial voice shared across all LLM calls
SYSTEM_PROMPT = (
    "Voce e o analista-chefe do RADAR, o agente de inteligencia de tendencias "
    "da plataforma Sinal.lab.\n\n"
    "Posicionamento: Deteccao precoce de sinais emergentes em tech e fintech LATAM — "
    "para fundadores tecnicos, CTOs e engenheiros seniores que tomam decisoes com dados.\n\n"
    "Territorios que o RADAR monitora:\n"
    "- T2: AI Aplicada (20%) — O que esta em producao vs o que e vapor. Cases reais, "
    "dados de impacto. AI agents, governance, Gen AI em servicos.\n"
    "- T4: Engenharia (20%) — Ferramentas, frameworks e infraestrutura emergente. "
    "Benchmarks, comparativos tecnicos, decisoes de stack.\n"
    "- T1: Fintech (40%) — Sinais de inovacao em pagamentos, Open Finance, embedded finance.\n"
    "- Transversal: sinais de qualquer territorio que indiquem mudanca estrutural.\n\n"
    "Estilo editorial:\n"
    "- Tom analitico e direto, sem hype ou marketing\n"
    "- Explique POR QUE os sinais importam, nao apenas O QUE sao\n"
    "- Identifique padroes e convergencias entre sinais (tendencias se cruzando)\n"
    "- Contextualize para o ecossistema Brasil/LATAM (impacto local, oportunidades)\n"
    "- Use linguagem tecnica quando apropriado, mas seja acessivel\n"
    "- Prefira verbos ativos e frases curtas\n"
    "- Escreva SEMPRE em portugues brasileiro (PT-BR), mesmo quando a fonte for em ingles\n"
    "- Evite frases tipicas de IA: 'vale ressaltar', 'neste contexto', "
    "'e importante destacar', 'no cenario atual'\n"
    "- Seja especifico: numeros e exemplos concretos > afirmacoes vagas\n\n"
    "Regua editorial:\n"
    "- Sempre va alem do resumo da fonte — adicione contexto LATAM, comparativos, implicacoes\n"
    "- Nunca reproduza press releases sem analise\n"
    "- Sem emojis, sem 'revolucionario'/'disruptivo'/'game-changer'\n"
    "- Sem previsoes vagas sobre o futuro sem dados do presente\n"
    "- Nao ignore o contexto LATAM — sempre conecte sinais globais ao impacto regional\n\n"
    "Pergunta-filtro: 'Um CTO de fintech em Sao Paulo com 10 anos de experiencia "
    "pararia de trabalhar para ler isto?'"
)


@dataclass
class SectionContent:
    """LLM-generated content for a trend report section."""

    intro: str  # 2-3 sentence editorial intro for the section
    summaries: list[str]  # One rewritten summary per signal (same order as input)


class RadarWriter:
    """LLM-powered editorial writer for the RADAR trend report.

    Uses LLMClient to generate editorial content. Falls back gracefully
    (returns None) when the client is unavailable or calls fail.
    """

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client if client is not None else LLMClient()

    @property
    def is_available(self) -> bool:
        """Check if the writer can generate content."""
        return self._client.is_available

    def write_headline(
        self,
        sections: list[TrendSection],
        week_number: int,
        item_count: int = 0,
    ) -> Optional[str]:
        """Generate an editorial headline for the RADAR report.

        Args:
            sections: Grouped trend sections with classified signals.
            week_number: Week number for the report.
            item_count: Total signals analyzed (for context).

        Returns:
            Headline string (max ~15 words), or None if generation fails.
        """
        if not sections or not self.is_available:
            return None

        sections_summary = self._build_sections_summary(sections)
        count_ctx = f"\nTotal de sinais analisados: {item_count}\n" if item_count else ""

        user_prompt = (
            f"Crie um titulo editorial (maximo 15 palavras) para a edicao da semana "
            f"{week_number} do RADAR Semanal.\n\n"
            f"{count_ctx}"
            f"Destaques:\n\n{sections_summary}\n\n"
            f"Direcoes:\n"
            f"- O titulo deve capturar o tema ou sinal mais relevante da semana\n"
            f"- Seja especifico e concreto (cite dado, tecnologia ou tendencia)\n"
            f"- Tom direto, sem hype ou adjetivos vazios\n"
            f"- Escreva em portugues brasileiro\n"
            f"- Retorne APENAS o titulo, sem aspas, sem formatacao extra"
        )

        result = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=64,
        )

        if not result or not result.strip():
            logger.warning("LLM returned empty headline for week %d", week_number)
            return None

        return result.strip().strip('"').strip("'")

    def write_report_intro(
        self,
        sections: list[TrendSection],
        week_number: int,
    ) -> Optional[str]:
        """Generate the trend report intro paragraph.

        Args:
            sections: Grouped trend sections with classified signals.
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
            f"Escreva um paragrafo de introducao (3-5 frases) para o RADAR Semanal "
            f"da semana {week_number}.\n\n"
            f"O relatorio desta semana detectou os seguintes sinais:\n\n"
            f"{sections_summary}\n\n"
            f"Direcoes:\n"
            f"- Identifique o fio narrativo que conecta os sinais mais relevantes\n"
            f"- Destaque convergencias entre tendencias de diferentes categorias\n"
            f"- Mencione 1-2 padroes emergentes e por que importam para LATAM\n"
            f"- Seja factual e especifico (cite numeros quando disponivel)\n"
            f"- Termine com uma frase que convide a leitura aprofundada\n"
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
        section: TrendSection,
    ) -> Optional[SectionContent]:
        """Generate editorial content for a trend report section.

        One API call per section that generates:
        - intro: 2-3 sentence editorial analysis
        - summaries: rewritten summary for each signal

        Args:
            section: A grouped trend section with classified signals.

        Returns:
            SectionContent or None if generation fails.
        """
        if not section.signals:
            return None

        if not self.is_available:
            return None

        items_detail = self._build_items_detail(section.signals)
        item_count = len(section.signals)

        user_prompt = (
            f'Gere conteudo editorial para a secao "{section.heading}" '
            f"do RADAR Semanal.\n\n"
            f"Sinais detectados nesta secao:\n\n"
            f"{items_detail}\n\n"
            f"Retorne um JSON valido com esta estrutura exata:\n"
            f'{{\n'
            f'  "intro": "Paragrafo de 2-3 frases analisando os sinais desta secao. '
            f'Identifique padroes, convergencias e por que importam para LATAM.",\n'
            f'  "summaries": [\n'
            f'    "Analise contextualizada do sinal 1 (2-3 frases). '
            f'Explique por que e relevante e qual o impacto potencial.",\n'
            f'    "Analise contextualizada do sinal 2 (2-3 frases)."\n'
            f"  ]\n"
            f"}}\n\n"
            f"Regras:\n"
            f'- O array "summaries" DEVE ter exatamente {item_count} elemento(s), '
            f"um por sinal, na mesma ordem\n"
            f"- Cada resumo deve contextualizar o sinal para CTOs e fundadores no Brasil/LATAM\n"
            f"- Adicione contexto que a fonte original pode nao ter "
            f"(ex: comparacao com tendencias LATAM, impacto no ecossistema local)\n"
            f"- Nao repita o titulo do sinal no resumo\n"
            f"- Retorne APENAS o JSON, sem texto antes ou depois"
        )

        # Scale max_tokens based on signal count: ~200 tokens per summary + 150 for intro + buffer
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

    def _build_sections_summary(self, sections: list[TrendSection]) -> str:
        """Build a summary of all sections for the intro prompt."""
        lines: list[str] = []
        for section in sections:
            lines.append(f"## {section.heading} ({len(section.signals)} sinais)")
            for classified_signal in section.signals:
                lines.append(f'- "{classified_signal.signal.title}" ({classified_signal.signal.source_name})')
            lines.append("")
        return "\n".join(lines)

    def _build_items_detail(self, signals: list) -> str:
        """Build detailed signal descriptions for a section prompt."""
        lines: list[str] = []
        for i, classified_signal in enumerate(signals, 1):
            signal = classified_signal.signal
            lines.append(f'{i}. "{signal.title}" (Fonte: {signal.source_name})')
            lines.append(f"   URL: {signal.url}")
            summary = signal.summary or "Sem resumo disponivel."
            lines.append(f'   Resumo original: "{summary}"')
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
