"""LLM-powered editorial writer for SINTESE newsletter.

Uses the shared LLMClient to generate editorial content for the
Sinal Semanal newsletter:
  - Newsletter intro paragraph (week's narrative arc)
  - Section intros (editorial commentary per category)
  - Rewritten item summaries (contextualized for LATAM audience)
  - Editorial metadata (callouts, companies, topics, featured video)

Architecture:
    synthesizer.py (orchestrator)
    ├── writer.py           <- LLM editorial content (this module)
    │   ├── write_newsletter_intro()      -> 1 API call
    │   ├── write_section_content()       -> 1 API call per section
    │   └── write_editorial_metadata()    -> 1 API call
    └── format_item_markdown()            <- template formatting (existing)

Gracefully falls back (returns None) when the LLM client is unavailable
or API calls fail, allowing the synthesizer to use template-based output.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from apps.agents.base.llm import LLMClient, strip_code_fences
from apps.agents.sintese.synthesizer import NewsletterSection

logger = logging.getLogger(__name__)


# Editorial voice shared across all LLM calls
SYSTEM_PROMPT = (
    "Voce e o editor-chefe da newsletter Sinal Semanal, publicada pela plataforma Sinal.lab.\n\n"
    "Posicionamento: Inteligencia de mercado sobre AI, fintech e infraestrutura digital "
    "na America Latina — para fundadores tecnicos, CTOs e engenheiros seniores que tomam "
    "decisoes com dados, nao com hype.\n\n"
    "Territorios editoriais (por peso):\n"
    "1. AI & Infraestrutura Inteligente (35%) — Pilar zero. Agentic AI, LLMs, AI aplicada, "
    "infra de AI, governance. AI nao e 'mais um tema' — e a mudanca de plataforma.\n"
    "2. Fintech & Infraestrutura Financeira LATAM (30%) — Open Finance, Pix, neobanks, "
    "stablecoins, tokenizacao, embedded finance, remessas\n"
    "3. Engenharia & Plataforma (20%) — Arquitetura, cloud, DevOps, seguranca, LGPD\n"
    "4. Venture Capital & Ecossistema (15%) — Deal flow, investor intelligence, M&A, "
    "ecosystem mapping (inclui agritech, climate tech)\n\n"
    "Voz editorial (5 atributos inegociaveis):\n"
    "- PRECISA: Toda afirmacao tem dado ou fonte. Sem 'muitos acreditam' ou 'e amplamente reconhecido'.\n"
    "- DENSA: Cada paragrafo carrega informacao nova. Zero filler.\n"
    "- OPINATIVA: Temos ponto de vista editorial. Conectamos fatos a consequencias.\n"
    "- DIRETA: Frases curtas. Voz ativa. Sem jargao corporativo.\n"
    "- CONSTRUIDA: Falamos como builders para builders. Tom peer-to-peer.\n\n"
    "Escreva SEMPRE em portugues brasileiro (PT-BR).\n\n"
    "Anti-patterns (nunca usar):\n"
    "- 'Neste artigo, vamos explorar...' (meta-linguagem)\n"
    "- 'E importante ressaltar que...' / 'Vale destacar que...' (filler)\n"
    "- 'O futuro e promissor...' (vazio)\n"
    "- 'Cada vez mais empresas estao...' (sem dado)\n"
    "- 'Segundo especialistas...' (quais?)\n"
    "- Adjetivos sem dado: 'impressionante', 'revolucionario', 'disruptivo'\n\n"
    "Regua editorial — O que NAO entra:\n"
    "- Reescrita de press release (analisamos, nao reproduzimos)\n"
    "- Opiniao sem dados de suporte\n"
    "- Hype sem substancia\n"
    "- Conteudo motivacional/inspiracional\n"
    "- Tutoriais basicos que existem em qualquer lugar\n"
    "- 'O futuro do X' sem dados sobre o presente do X\n\n"
    "Pergunta-filtro: 'Um CTO de fintech em Sao Paulo com 10 anos de experiencia "
    "pararia de trabalhar para ler isto?' Se nao, reformule."
)


@dataclass
class SectionContent:
    """LLM-generated content for a newsletter section."""

    intro: str  # 2-3 sentence editorial intro for the section
    summaries: list[str]  # One rewritten summary per item (same order as input)


@dataclass
class EditorialMetadata:
    """LLM-generated editorial metadata for newsletter enrichment."""

    callouts: List[dict] = field(default_factory=list)
    companies_mentioned: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    featured_video_url: Optional[str] = None


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

    def write_editorial_metadata(
        self,
        sections: list[NewsletterSection],
        edition_number: int,
    ) -> Optional[EditorialMetadata]:
        """Generate editorial metadata (callouts, companies, topics) in a single LLM call.

        Produces structured metadata that enriches the newsletter display without
        affecting the body markdown.

        Args:
            sections: Grouped newsletter sections with items.
            edition_number: Edition number for context.

        Returns:
            EditorialMetadata or None if generation fails.
        """
        if not self.is_available or not sections:
            return None

        sections_summary = self._build_sections_summary(sections)

        # Scan items for YouTube/Vimeo URLs
        video_candidates: list[str] = []
        for section in sections:
            for scored_item in section.items:
                url = scored_item.item.url
                if any(v in url for v in ["youtube.com", "youtu.be", "vimeo.com"]):
                    video_candidates.append(url)

        user_prompt = (
            f"Analise o conteudo da edicao #{edition_number} do Sinal Semanal "
            f"e gere metadados editoriais estruturados.\n\n"
            f"Conteudo:\n{sections_summary}\n\n"
            f"URLs de video encontradas: {video_candidates if video_candidates else 'Nenhuma'}\n\n"
            f"Retorne um JSON valido:\n"
            f'{{\n'
            f'  "callouts": [\n'
            f'    {{\n'
            f'      "type": "highlight",\n'
            f'      "content": "Frase de destaque editorial (1-2 frases, dado ou insight marcante).",\n'
            f'      "position": "after_intro"\n'
            f'    }}\n'
            f'  ],\n'
            f'  "companies_mentioned": ["Nubank", "Rappi"],\n'
            f'  "topics": ["AI", "fintech"],\n'
            f'  "featured_video_url": null\n'
            f'}}\n\n'
            f"Regras:\n"
            f"- callouts: gere 1-3 callouts (tipo highlight). Cada um deve ser um insight acionavel "
            f"ou dado marcante da semana.\n"
            f"- companies_mentioned: liste todas as empresas mencionadas nos titulos e resumos.\n"
            f"- topics: liste os 3-5 temas principais desta edicao.\n"
            f"- featured_video_url: se houver URL de video relevante, inclua-a. Senao, null.\n"
            f"- Retorne APENAS o JSON, sem texto antes ou depois."
        )

        raw = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1024,
        )

        if not raw:
            logger.warning("LLM returned empty editorial metadata for edition #%d", edition_number)
            return None

        return self._parse_editorial_metadata_json(raw)

    def _parse_editorial_metadata_json(self, raw: str) -> Optional[EditorialMetadata]:
        """Parse and validate the editorial metadata JSON response.

        Strips code fences, validates structure (callouts, companies, topics must
        be lists), filters invalid callouts (must have 'content' key), and enforces
        limits (max 20 companies, 10 topics). Returns None on any parse/validation failure.
        """
        cleaned = strip_code_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse editorial metadata JSON: %.100s", raw)
            return None

        callouts = data.get("callouts", [])
        companies = data.get("companies_mentioned", [])
        topics = data.get("topics", [])
        video_url = data.get("featured_video_url")

        if not isinstance(callouts, list) or not isinstance(companies, list) or not isinstance(topics, list):
            logger.warning("Invalid editorial metadata structure")
            return None

        # Validate callout structure
        valid_callouts: list[dict] = []
        for c in callouts:
            if isinstance(c, dict) and "content" in c:
                valid_callouts.append({
                    "type": c.get("type", "highlight"),
                    "content": c["content"],
                    "position": c.get("position", "after_intro"),
                })

        return EditorialMetadata(
            callouts=valid_callouts,
            companies_mentioned=[str(c) for c in companies[:20]],
            topics=[str(t) for t in topics[:10]],
            featured_video_url=video_url if isinstance(video_url, str) else None,
        )
