"""LLM-powered editorial writer for MERCADO ecosystem reports.

Uses the shared LLMClient to generate editorial content for the
MERCADO agent's ecosystem snapshot reports:
  - Ecosystem narrative intro (aggregate stats about new discoveries)
  - Highlight descriptions (meaningful context for top-ranked companies)

Architecture (DIFFERENT from SINTESE):
    MERCADO has 500+ company profiles per run — too many for per-item
    LLM calls. Instead, the writer uses exactly 2 API calls total:

    synthesizer.py (orchestrator)
    ├── writer.py           <- LLM editorial content (this module)
    │   ├── write_snapshot_intro()           -> 1 API call (aggregate narrative)
    │   └── write_highlight_descriptions()   -> 1 API call (top 3-5 companies)
    └── template-based sections              <- city/sector breakdowns (existing)

Gracefully falls back (returns None) when the LLM client is unavailable
or API calls fail, allowing the synthesizer to use template-based output.
"""

import json
import logging
from collections import Counter
from typing import Optional

from apps.agents.base.llm import LLMClient, strip_code_fences
from apps.agents.mercado.scorer import ScoredCompanyProfile

logger = logging.getLogger(__name__)


# Editorial voice for MERCADO ecosystem analysis
SYSTEM_PROMPT = (
    "Voce e o analista de ecossistema tech da plataforma Sinal.lab, "
    "especializado em mapeamento de startups na America Latina (LATAM).\n\n"
    "Posicionamento: Market maps, perfis de empresas e analise de ecossistema — "
    "dados proprietarios que nao existem em portugues com essa profundidade.\n\n"
    "Territorios editoriais que o MERCADO alimenta:\n"
    "- T1: Fintech (40%) — Market maps de neobanks, BaaS, Open Finance, embedded finance\n"
    "- T5: Venture (15%) — Ecosystem mapping por cidade, perfis de empresas\n"
    "- T6: GreenTech (5%) — AgriTech, climate tech, ESG no ecossistema LATAM\n"
    "- Transversal: mapeamento de qualquer vertical com relevancia para o ecossistema\n\n"
    "Foco analitico:\n"
    "- O que novas descobertas de empresas revelam sobre tendencias de crescimento setorial\n"
    "- Quais cidades estao emergindo como hubs: SP, Florianopolis, Recife, BH, Curitiba\n"
    "- Padroes na paisagem de startups e sinais de maturidade do ecossistema\n"
    "- Dados concretos e insights acionaveis — nao especulacao\n\n"
    "Estilo editorial:\n"
    "- Tom analitico, factual e direto\n"
    "- Contextualize para o ecossistema tech LATAM (Brasil, Mexico, Colombia, Chile, Argentina)\n"
    "- Use linguagem tecnica quando apropriado, mas seja acessivel\n"
    "- Prefira verbos ativos e frases curtas\n"
    "- Escreva SEMPRE em portugues brasileiro (PT-BR)\n\n"
    "Regua editorial:\n"
    "- Sem emojis, sem 'revolucionario'/'disruptivo'/'game-changer'\n"
    "- Sem previsoes vagas — dados do presente e tendencias verificaveis\n"
    "- Va alem de listar empresas — analise o que os dados revelam sobre o ecossistema\n\n"
    "Pergunta-filtro: 'Um CTO de fintech em Sao Paulo com 10 anos de experiencia "
    "pararia de trabalhar para ler isto?'"
)


class MercadoWriter:
    """LLM-powered editorial writer for MERCADO ecosystem reports.

    Uses LLMClient to generate editorial content. Falls back gracefully
    (returns None) when the client is unavailable or calls fail.

    Only 2 API calls per report run (not per-profile), designed for
    the scale of 500+ company profiles.
    """

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client if client is not None else LLMClient()

    @property
    def is_available(self) -> bool:
        """Check if the writer can generate content."""
        return self._client.is_available

    def write_snapshot_intro(
        self,
        scored_profiles: list[ScoredCompanyProfile],
        week_number: int,
    ) -> Optional[str]:
        """Generate an ecosystem narrative intro based on aggregate stats.

        One API call that summarizes the week's discoveries: total count,
        city distribution, sector breakdown, and top-confidence companies.

        Args:
            scored_profiles: All scored company profiles for the week.
            week_number: Week number of the year (1-52).

        Returns:
            Intro paragraph string, or None if generation fails.
        """
        if not scored_profiles:
            return None

        if not self.is_available:
            return None

        aggregate_summary = self._build_aggregate_summary(scored_profiles)

        user_prompt = (
            f"Escreva um paragrafo de introducao (3-5 frases) para o snapshot "
            f"do ecossistema LATAM na semana {week_number}.\n\n"
            f"Dados agregados das novas startups descobertas:\n\n"
            f"{aggregate_summary}\n\n"
            f"Direcoes:\n"
            f"- Identifique padroes ou tendencias nos dados (concentracao setorial, hubs emergentes)\n"
            f"- Mencione numeros concretos (total de empresas, cidades, setores dominantes)\n"
            f"- Contextualize o que esses numeros significam para o ecossistema LATAM\n"
            f"- NAO use saudacao — va direto ao ponto\n"
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

    def write_highlight_descriptions(
        self,
        top_profiles: list[ScoredCompanyProfile],
    ) -> Optional[list[str]]:
        """Generate meaningful descriptions for top-highlighted companies.

        One API call that produces contextual descriptions for 3-5 companies.
        Returns a list of strings in the same order as the input profiles.

        Args:
            top_profiles: Top-ranked profiles to describe (typically 3-5).

        Returns:
            List of description strings (one per profile), or None on failure.
        """
        if not top_profiles:
            return None

        if not self.is_available:
            return None

        highlights_detail = self._build_highlights_detail(top_profiles)
        profile_count = len(top_profiles)

        user_prompt = (
            f"Gere descricoes contextualizadas para as {profile_count} startups "
            f"em destaque no ecossistema LATAM desta semana.\n\n"
            f"Empresas em destaque:\n\n"
            f"{highlights_detail}\n\n"
            f"Retorne um JSON valido com esta estrutura exata:\n"
            f'{{\n'
            f'  "descriptions": [\n'
            f'    "Descricao da empresa 1 e por que ela se destaca no ecossistema (2-3 frases).",\n'
            f'    "Descricao da empresa 2 e por que ela se destaca no ecossistema (2-3 frases)."\n'
            f"  ]\n"
            f"}}\n\n"
            f"Regras:\n"
            f'- O array "descriptions" DEVE ter exatamente {profile_count} elemento(s), '
            f"um por empresa, na mesma ordem\n"
            f"- Cada descricao deve explicar por que a empresa e relevante para investidores e CTOs\n"
            f"- Mencione setor, localizacao e sinais tecnicos (GitHub, stack) quando disponivel\n"
            f"- Retorne APENAS o JSON, sem texto antes ou depois"
        )

        max_tokens = max(1024, profile_count * 250 + 200)

        raw = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=max_tokens,
        )

        if not raw:
            logger.warning("LLM returned empty highlight descriptions")
            return None

        return self._parse_descriptions_json(raw, profile_count)

    def _build_aggregate_summary(
        self,
        profiles: list[ScoredCompanyProfile],
    ) -> str:
        """Format aggregate stats from all profiles for the intro prompt.

        Includes: total count, city breakdown, sector distribution,
        and top-confidence companies.
        """
        lines: list[str] = []

        # Total count
        lines.append(f"Total de empresas descobertas: {len(profiles)}")
        lines.append("")

        # City breakdown
        city_counts = Counter(
            s.profile.city or "Cidade nao especificada" for s in profiles
        )
        lines.append("Distribuicao por cidade:")
        for city, count in city_counts.most_common():
            lines.append(f"- {city}: {count} empresas")
        lines.append("")

        # Sector distribution
        sector_counts = Counter(
            s.profile.sector or "Outros" for s in profiles
        )
        lines.append("Distribuicao por setor:")
        for sector, count in sector_counts.most_common():
            lines.append(f"- {sector}: {count} empresas")
        lines.append("")

        # Top confidence companies
        top_by_confidence = sorted(
            profiles, key=lambda s: s.composite_score, reverse=True
        )[:5]
        lines.append("Empresas com maior confianca:")
        for scored in top_by_confidence:
            p = scored.profile
            lines.append(
                f"- {p.name} ({p.city}, {p.sector or 'Sem setor'}) "
                f"— confianca: {scored.composite_score:.2f}"
            )

        return "\n".join(lines)

    def _build_highlights_detail(
        self,
        profiles: list[ScoredCompanyProfile],
    ) -> str:
        """Format top profiles with detail for the descriptions prompt."""
        lines: list[str] = []
        for i, scored in enumerate(profiles, 1):
            p = scored.profile
            lines.append(f"{i}. {p.name}")
            lines.append(f"   Setor: {p.sector or 'Nao classificado'}")
            lines.append(f"   Cidade: {p.city or 'Nao especificada'}, {p.country}")
            if p.description:
                lines.append(f'   Descricao original: "{p.description[:300]}"')
            if p.github_url:
                lines.append(f"   GitHub: {p.github_url}")
            if p.tech_stack:
                lines.append(f"   Tech Stack: {', '.join(p.tech_stack[:5])}")
            lines.append(
                f"   Confianca: {scored.composite_score:.2f} "
                f"(DQ {scored.confidence.data_quality:.2f}, "
                f"AC {scored.confidence.analysis_confidence:.2f})"
            )
            lines.append("")
        return "\n".join(lines)

    def _parse_descriptions_json(
        self,
        raw: str,
        expected_count: int,
    ) -> Optional[list[str]]:
        """Parse and validate the JSON response for highlight descriptions.

        Args:
            raw: Raw LLM output (may include code fences).
            expected_count: Expected number of descriptions.

        Returns:
            List of description strings, or None on parse/validation failure.
        """
        cleaned = strip_code_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse descriptions JSON: %.100s", raw
            )
            return None

        descriptions = data.get("descriptions")

        if not isinstance(descriptions, list):
            logger.warning("Invalid JSON structure: 'descriptions' is not a list")
            return None

        if len(descriptions) != expected_count:
            logger.warning(
                "Description count mismatch: expected %d, got %d",
                expected_count, len(descriptions),
            )
            return None

        return descriptions
