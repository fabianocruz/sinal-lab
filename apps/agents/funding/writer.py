"""LLM-powered editorial writer for FUNDING agent.

Uses the shared LLMClient to generate editorial content for the
weekly funding report:
  - Report intro paragraph (market narrative from the week's deals)
  - Deal highlights (analytical commentary on top deals)

Architecture:
    synthesizer.py (orchestrator)
    ├── writer.py           <- LLM editorial content (this module)
    │   ├── write_report_intro()      -> 1 API call
    │   └── write_deal_highlights()   -> 1 API call
    └── format_amount()               <- template formatting (existing)

Gracefully falls back (returns None) when the LLM client is unavailable
or API calls fail, allowing the synthesizer to use template-based output.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from apps.agents.base.llm import LLMClient, strip_code_fences
from apps.agents.funding.scorer import ScoredFundingEvent
from apps.agents.funding.synthesizer import format_amount, format_round_type

logger = logging.getLogger(__name__)


# Editorial voice for capital markets analysis
SYSTEM_PROMPT = (
    "Voce e o analista de mercado de capitais da plataforma Sinal.lab, "
    "especializado no ecossistema tech da America Latina.\n\n"
    "Posicionamento: Dados proprietarios e analise de fluxo de capital no ecossistema "
    "tech LATAM — para fundadores, CTOs e investidores que acompanham o mercado.\n\n"
    "Territorio editorial: T5 — Venture Capital & Funding LATAM (15%)\n"
    "Sub-territorios:\n"
    "- Deal flow & Funding tracker — todas as rodadas com dados normalizados\n"
    "- Investor intelligence — perfis, portfolios, comportamento de investimento\n"
    "- M&A, IPOs & Exits — aquisicoes, analise de exits, pipeline\n"
    "- Angulo critico: 'Vai alem de press release? Tem analise, contexto, tendencia?'\n\n"
    "Estilo editorial:\n"
    "- Tom analitico, factual e orientado a dados\n"
    "- Foque no que as rodadas SINALIZAM sobre sentimento dos investidores\n"
    "- Analise tendencias de setor, cenario competitivo e teses de investimento\n"
    "- Contextualize para o mercado brasileiro e latino-americano\n"
    "- Use numeros concretos (valores, multiplos, comparacoes)\n"
    "- Prefira verbos ativos e frases curtas\n"
    "- Escreva SEMPRE em portugues brasileiro (PT-BR), mesmo quando a fonte for em ingles\n"
    "- Evite frases tipicas de IA: 'vale ressaltar', 'neste contexto', "
    "'e importante destacar', 'no cenario atual'\n"
    "- Seja especifico: numeros e exemplos concretos > afirmacoes vagas\n\n"
    "Regua editorial:\n"
    "- NUNCA reproduza press releases — analisamos, nao reproduzimos\n"
    "- Sem emojis, sem 'revolucionario'/'disruptivo'/'game-changer'\n"
    "- Nao repita informacoes obvias que o leitor ja ve na tabela de dados\n"
    "- Sem previsoes vagas — dados do presente e tendencias verificaveis\n"
    "- Cada rodada deve ter contexto: por que esse investimento importa?\n\n"
    "Pergunta-filtro: 'Um CTO de fintech em Sao Paulo com 10 anos de experiencia "
    "pararia de trabalhar para ler isto?'"
)


@dataclass
class SectionContent:
    """LLM-generated content for the funding report."""

    intro: str  # Market narrative paragraph
    highlights: list[str]  # One commentary per top deal


class FundingWriter:
    """LLM-powered editorial writer for the FUNDING report.

    Uses LLMClient to generate market analysis content. Falls back
    gracefully (returns None) when the client is unavailable or calls fail.
    """

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client if client is not None else LLMClient()

    @property
    def is_available(self) -> bool:
        """Check if the writer can generate content."""
        return self._client.is_available

    def write_report_intro(
        self,
        scored_events: list[ScoredFundingEvent],
        week_number: int,
    ) -> Optional[str]:
        """Generate the report intro paragraph with market narrative.

        Builds a summary of all events (total raised, dominant sectors,
        notable deals) and asks the LLM for a narrative paragraph.

        Args:
            scored_events: List of scored funding events for the week.
            week_number: Week number of the year.

        Returns:
            Intro paragraph string, or None if generation fails.
        """
        if not scored_events:
            return None

        if not self.is_available:
            return None

        events_summary = self._build_events_summary(scored_events)

        # Calculate aggregate stats for the prompt
        total_raised = sum(
            e.event.amount_usd for e in scored_events if e.event.amount_usd is not None
        )
        events_with_amount = sum(
            1 for e in scored_events if e.event.amount_usd is not None
        )

        user_prompt = (
            f"Escreva um paragrafo de introducao (3-5 frases) para o relatorio "
            f"semanal de investimentos LATAM, semana {week_number}.\n\n"
            f"Dados agregados:\n"
            f"- Total de rodadas: {len(scored_events)}\n"
            f"- Rodadas com valor divulgado: {events_with_amount}\n"
            f"- Volume total levantado: US$ {total_raised:.1f}M\n\n"
            f"Rodadas da semana:\n\n"
            f"{events_summary}\n\n"
            f"Direcoes:\n"
            f"- Identifique o que os dados sinalizam sobre o mercado LATAM\n"
            f"- Mencione os deals mais relevantes por valor ou estrategia\n"
            f"- Cite setores ou teses dominantes na semana\n"
            f"- Seja factual e especifico (cite numeros)\n"
            f"- NAO use saudacao — va direto ao ponto\n"
            f"- Retorne APENAS o paragrafo, sem titulo ou formatacao extra"
        )

        result = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
        )

        if not result or not result.strip():
            logger.warning(
                "LLM returned empty intro for funding report week %d",
                week_number,
            )
            return None

        return result.strip()

    def write_deal_highlights(
        self,
        top_events: list[ScoredFundingEvent],
    ) -> Optional[list[str]]:
        """Generate analytical commentary for top deals.

        One API call that returns a JSON array with one commentary
        per deal, focusing on what the deal signals for the market.

        Args:
            top_events: Top N scored events (typically top 3).

        Returns:
            List of commentary strings (one per event), or None on failure.
        """
        if not top_events:
            return None

        if not self.is_available:
            return None

        highlights_detail = self._build_highlights_detail(top_events)
        event_count = len(top_events)

        user_prompt = (
            f"Gere comentarios analiticos para os {event_count} principais deals "
            f"da semana no mercado tech LATAM.\n\n"
            f"Deals:\n\n"
            f"{highlights_detail}\n\n"
            f"Retorne um JSON valido com esta estrutura exata:\n"
            f'{{\n'
            f'  "highlights": [\n'
            f'    "Comentario analitico sobre o deal 1 (2-3 frases). '
            f'O que essa rodada sinaliza para o mercado?",\n'
            f'    "Comentario analitico sobre o deal 2 (2-3 frases)."\n'
            f'  ]\n'
            f'}}\n\n'
            f"Regras:\n"
            f'- O array "highlights" DEVE ter exatamente {event_count} elemento(s), '
            f"um por deal, na mesma ordem\n"
            f"- Foque no que cada deal sinaliza (tese de investimento, sentimento, setor)\n"
            f"- Mencione investidores quando relevante\n"
            f"- Nao repita informacoes que ja estao na tabela (valor, tipo de rodada)\n"
            f"- Retorne APENAS o JSON, sem texto antes ou depois"
        )

        max_tokens = max(1024, event_count * 250 + 300)

        raw = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=max_tokens,
        )

        if not raw:
            logger.warning("LLM returned empty highlights for top deals")
            return None

        return self._parse_highlights_json(raw, event_count)

    def _build_events_summary(
        self,
        events: list[ScoredFundingEvent],
    ) -> str:
        """Build a summary of all events for the intro prompt.

        Args:
            events: All scored events for the week.

        Returns:
            Formatted string with event details.
        """
        lines: list[str] = []
        for i, scored in enumerate(events, 1):
            event = scored.event
            amount_str = format_amount(event.amount_usd)
            round_str = format_round_type(event.round_type)
            investors_str = (
                ", ".join(event.lead_investors[:3])
                if event.lead_investors
                else "N/A"
            )
            lines.append(
                f"{i}. {event.company_name} — {amount_str} {round_str} "
                f"(Investidores: {investors_str})"
            )
        return "\n".join(lines)

    def _build_highlights_detail(
        self,
        events: list[ScoredFundingEvent],
    ) -> str:
        """Build detailed event descriptions for the highlights prompt.

        Args:
            events: Top events to generate highlights for.

        Returns:
            Formatted string with detailed event info.
        """
        lines: list[str] = []
        for i, scored in enumerate(events, 1):
            event = scored.event
            amount_str = format_amount(event.amount_usd)
            round_str = format_round_type(event.round_type)
            lines.append(f"{i}. **{event.company_name}** — {amount_str} {round_str}")

            if event.lead_investors:
                investors_str = ", ".join(event.lead_investors)
                lines.append(f"   Investidores: {investors_str}")

            if event.notes and not event.notes.startswith("[AMOUNT_CONFLICT"):
                lines.append(f"   Contexto: {event.notes[:200]}")

            lines.append("")
        return "\n".join(lines)

    def _parse_highlights_json(
        self,
        raw: str,
        expected_count: int,
    ) -> Optional[list[str]]:
        """Parse and validate the JSON response for deal highlights.

        Args:
            raw: Raw LLM output (may include code fences).
            expected_count: Number of highlights expected.

        Returns:
            List of highlight strings, or None if parsing/validation fails.
        """
        cleaned = strip_code_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse JSON for deal highlights: %.100s", raw
            )
            return None

        highlights = data.get("highlights")

        if not isinstance(highlights, list):
            logger.warning("Invalid JSON structure for deal highlights")
            return None

        if len(highlights) != expected_count:
            logger.warning(
                "Highlights count mismatch: expected %d, got %d",
                expected_count,
                len(highlights),
            )
            return None

        return highlights
