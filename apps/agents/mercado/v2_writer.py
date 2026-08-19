"""MERCADO v2 editorial writer — market intelligence analysis.

Generates LLM-powered editorial content for the weekly market report:
- Headline (tese da semana, 15 words max)
- Intro paragraph (thesis of the week)
- Per-sector analysis (2-3 paragraphs per section)
- Callouts (3 highlights like SINTESE)

Falls back gracefully (returns None) when the client is unavailable.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from apps.agents.base.llm import LLMClient, strip_code_fences
from apps.agents.base.writing_rules import WRITING_RULES
from apps.agents.mercado.market_event import SectorSection

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Voce e o analista de mercado da plataforma Sinal.lab, especializado no "
    "ecossistema tech LATAM — fintech, AI, DevTools, e verticais emergentes.\n\n"
    "Posicionamento: Analise semanal de mercado para fundadores, CTOs e "
    "investidores. Nao e lista de rodadas — e interpretacao do que os numeros "
    "e movimentos revelam sobre sentimento de mercado, teses emergentes e "
    "dinamica competitiva.\n\n"
    "DIVISAO DE RESPONSABILIDADES com outros agents do Sinal:\n"
    "- FUNDING agent ja cobre: lista de rodadas da semana, volume agregado, "
    "investidores de cada deal, factual por round. Nao repita esse trabalho.\n"
    "- MERCADO (voce) cobre: TESE SETORIAL (o que o padrao de rodadas revela "
    "sobre o mercado), CONTRASTE (setor X vs Y, regiao A vs B), IMPLICACAO "
    "(o que muda para quem constroi ou investe), HISTORICO (como a semana se "
    "compara com trimestres anteriores). Pense em 'zoom-out' dos dados.\n\n"
    "Territorio editorial: T1 Fintech (40%), T2 AI (20%), T3 DevTools (10%), "
    "Verticais Rotativas (15%), Cross-sector (15%).\n\n"
    "Estilo editorial:\n"
    "- Tom analitico, factual e orientado a dados\n"
    "- Cada paragrafo deve responder 'por que importa pra CTOs/VCs?'\n"
    "- Cruze rodadas + movimentos de mercado + contexto setorial\n"
    "- Cite numeros concretos (valores, multiplos, comparacoes historicas)\n"
    "- Prefira verbos ativos e frases curtas\n"
    "- Escreva SEMPRE em portugues brasileiro (PT-BR)\n"
    "- Evite clicheres de IA: 'vale ressaltar', 'neste contexto', 'é importante destacar', "
    "'no cenário atual'\n"
    "- Nao use hype: 'revolucionario', 'disruptivo', 'game-changer'\n\n"
    "Pergunta-filtro: 'Um CTO de fintech em Sao Paulo com 10 anos de "
    "experiencia pararia de trabalhar para ler isto?' Se nao, reformule.\n\n"
    + WRITING_RULES
)


@dataclass
class EditorialMetadata:
    """LLM-generated metadata for the newsletter payload."""
    callouts: list[dict]  # [{type, content, position}, ...]
    companies_mentioned: list[str]
    topics: list[str]
    email_subject: Optional[str] = None


class MercadoV2Writer:
    """LLM editorial writer for MERCADO v2."""

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client if client is not None else LLMClient()

    @property
    def is_available(self) -> bool:
        return self._client.is_available

    def write_headline(
        self,
        sections: list[SectorSection],
        week_number: int,
    ) -> Optional[str]:
        """Generate editorial headline (max 15 words)."""
        if not sections or not self.is_available:
            return None

        summary = self._sections_summary(sections, top_per_section=3)

        prompt = (
            f"Crie um titulo editorial (maximo 15 palavras) para o MARKET INTELLIGENCE "
            f"WEEKLY da semana {week_number}. IMPORTANTE: O Sinal tem um agent FUNDING "
            f"separado que cobre 'rodadas da semana'. MERCADO e sobre TESE SETORIAL, "
            f"MOVIMENTOS DE PODER e DINAMICA COMPETITIVA — nao liste deals ou volumes.\n\n"
            f"Setores cobertos e destaques:\n\n{summary}\n\n"
            "Direcoes:\n"
            "- Angulo MERCADO: tese, padrao, implicacao setorial\n"
            "- NAO cite volumes agregados ('X rodadas movimentam $Y') — isso e FUNDING\n"
            "- NAO comece com nome de empresa + valor ('Plata levanta $405M') — isso e FUNDING\n"
            "- FOQUE em: qual setor/regiao/tese esta ganhando, que movimento de poder "
            "apareceu, que contradicao ou consolidacao surgiu\n"
            "- Exemplos de bom angulo: 'Mexico consolida lideranca fintech enquanto "
            "Brasil aposta em early-stage cripto', 'Credito ao consumidor LATAM atrai "
            "capital crossover: tese muda de volume para margem'\n"
            "- Tom analitico, interpretativo\n"
            "- Nada de 'Semana N:' no inicio\n"
            "- Retorne APENAS o titulo"
        )

        result = self._client.generate(
            user_prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=96,
        )
        if not result or not result.strip():
            return None
        return result.strip().strip('"').strip("'")

    def write_intro(
        self,
        sections: list[SectorSection],
        week_number: int,
    ) -> Optional[str]:
        """Generate intro paragraph (thesis of the week, 4-6 sentences)."""
        if not sections or not self.is_available:
            return None

        summary = self._sections_summary(sections, top_per_section=5)

        prompt = (
            f"Escreva o paragrafo de abertura (4 a 6 frases) do MARKET "
            f"INTELLIGENCE WEEKLY LATAM, semana {week_number}.\n\n"
            f"IMPORTANTE: O Sinal ja tem um agent FUNDING que lista rodadas. "
            f"MERCADO e para ANALISE SETORIAL e de mercado — nao liste rodadas "
            f"nem comece citando 'X empresa levantou $Y'.\n\n"
            f"Dados da semana (para referencia, NAO listar):\n\n{summary}\n\n"
            "Direcoes obrigatorias:\n"
            "- NAO comece com nome de empresa + valor ('Plata levanta $405M'): "
            "isso e estilo FUNDING\n"
            "- NAO comece com '95% do capital foi para fintech': isso tambem e FUNDING\n"
            "- COMECE com tese ou observacao macro ('Capital crossover volta a LATAM', "
            "'Mexico consolida posicao como 2o polo fintech', 'Early-stage cripto "
            "concentra investidores tier-1')\n"
            "- DEPOIS cite dados concretos que sustentam a tese (inclui numeros)\n"
            "- Use CONTRASTE: setor X vs Y, regiao A vs B, estagio N vs M\n"
            "- Identifique 'o que muda' para quem constroi ou investe\n"
            "- 4-6 frases, densas, sem hype\n"
            "- Retorne APENAS o paragrafo"
        )

        result = self._client.generate(
            user_prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
        )
        if not result or not result.strip():
            return None
        return result.strip()

    def write_sector_analysis(
        self,
        section: SectorSection,
        week_number: int,
    ) -> Optional[str]:
        """Generate analysis paragraphs for one sector section (2-3 parags)."""
        if not section.events or not self.is_available:
            return None

        events_block = self._format_events_for_prompt(section.events)

        prompt = (
            f"Escreva a analise da secao '{section.heading}' para o relatorio "
            f"semanal, semana {week_number}.\n\n"
            f"Eventos da semana neste setor:\n\n{events_block}\n\n"
            "Direcoes:\n"
            "- 2 a 3 paragrafos (150-250 palavras total)\n"
            "- Cada paragrafo analisa um angulo (tese, contraste, implicacao)\n"
            "- Cite empresas e valores concretos\n"
            "- Responda 'o que isso revela?' em cada paragrafo\n"
            "- NAO liste as rodadas sequencialmente — integre em narrativa\n"
            "- Tom analitico e direto\n"
            "- Retorne APENAS o corpo da secao, sem titulo (o titulo ja existe)"
        )

        result = self._client.generate(
            user_prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
        )
        if not result or not result.strip():
            return None
        return result.strip()

    def write_editorial_metadata(
        self,
        sections: list[SectorSection],
        week_number: int,
    ) -> Optional[EditorialMetadata]:
        """Generate callouts + topics + companies_mentioned + email subject."""
        if not sections or not self.is_available:
            return None

        summary = self._sections_summary(sections, top_per_section=5)

        prompt = (
            f"Gere metadata editorial JSON para o relatorio de market intelligence, "
            f"semana {week_number}.\n\n"
            f"Dados:\n\n{summary}\n\n"
            "Retorne JSON valido com esta estrutura exata:\n"
            "{\n"
            '  "callouts": [\n'
            '    {"type": "highlight", "content": "...", "position": "after_intro"},\n'
            '    ... (3 items total, cada 1-2 frases analiticas)\n'
            "  ],\n"
            '  "companies_mentioned": ["Empresa1", "Empresa2", ...],\n'
            '  "topics": ["tema 1", "tema 2", ...],\n'
            '  "email_subject": "Subject line curto (max 70 chars, cite dado concreto)"\n'
            "}\n\n"
            "Regras:\n"
            "- Exatamente 3 callouts\n"
            "- 5-10 topics concisos\n"
            "- Lista unica de empresas citadas nos eventos\n"
            "- Retorne APENAS o JSON"
        )

        result = self._client.generate(
            user_prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1024,
        )
        if not result:
            return None

        try:
            data = json.loads(strip_code_fences(result))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse editorial metadata JSON: %s", e)
            return None

        return EditorialMetadata(
            callouts=data.get("callouts", [])[:3],
            companies_mentioned=data.get("companies_mentioned", [])[:20],
            topics=data.get("topics", [])[:10],
            email_subject=(data.get("email_subject") or "").strip() or None,
        )

    # --- Helpers ---

    def _sections_summary(
        self,
        sections: list[SectorSection],
        top_per_section: int = 3,
    ) -> str:
        lines: list[str] = []
        for section in sections:
            lines.append(f"### {section.heading} ({len(section.events)} eventos)")
            for scored in section.events[:top_per_section]:
                e = scored.event if hasattr(scored, "event") else scored
                amount = _format_compact(e.amount_usd) if e.amount_usd else "nao divulgado"
                investors = f" [{', '.join(e.investors[:3])}]" if e.investors else ""
                lines.append(
                    f"- {e.company_name} ({e.country or 'LATAM'}): "
                    f"{e.round_type or e.event_type} {amount}{investors}"
                )
            lines.append("")
        return "\n".join(lines)

    def _format_events_for_prompt(self, scored_events: list) -> str:
        lines: list[str] = []
        for s in scored_events:
            e = s.event if hasattr(s, "event") else s
            amount = _format_compact(e.amount_usd) if e.amount_usd else "nao divulgado"
            sector = e.sector or "setor nao classificado"
            location = ", ".join(filter(None, [e.city, e.country])) or "LATAM"
            investors = f" Investidores: {', '.join(e.investors[:4])}." if e.investors else ""
            summary = (e.summary or "")[:200]
            lines.append(
                f"- **{e.company_name}** ({location}) — {e.round_type or e.event_type} {amount}. "
                f"Setor: {sector}.{investors} {summary}".strip()
            )
        return "\n".join(lines)


def _format_compact(amount_usd: Optional[float]) -> str:
    if not amount_usd:
        return "nao divulgado"
    if amount_usd >= 1_000_000_000:
        return f"${amount_usd / 1_000_000_000:.1f}B"
    if amount_usd >= 1_000_000:
        return f"${amount_usd / 1_000_000:.1f}M"
    return f"${amount_usd / 1000:.0f}K"
