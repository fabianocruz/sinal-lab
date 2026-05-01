"""Feed Curator Agent — LLM-powered editorial curation of social signals.

Persona: Ana Torres. Runs every 4 hours. Loads recent signals from the DB,
filters spam, sends to LLM for selection and editorial rewrite, enriches
with thumbnails and embed detection, and produces a curated feed.

This is a CONTENT agent: it applies editorial judgment to raw signal data
collected by the Social Signals agent.
"""

import logging
from typing import Any, List, Optional

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.config import AgentCategory
from apps.agents.base.llm import LLMClient, LLMConfig
from apps.agents.base.output import AgentOutput
from apps.agents.feed_curator.config import FEED_CURATOR_CONFIG
from apps.agents.feed_curator.curator import (
    CuratedItem,
    curate_via_llm,
    load_recent_signals,
    pre_filter_spam,
)
from apps.agents.feed_curator.enricher import enrich_items

logger = logging.getLogger(__name__)


class FeedCuratorAgent(BaseAgent):
    """Feed Curator Agent.

    Curates social signals into a publishable feed with editorial headlines
    and context. Uses the Ana Torres persona for LLM-driven selection.

    Lifecycle:
        collect() -> load recent signals from DB
        process() -> pre-filter spam, LLM curation, enrichment
        score()   -> compute aggregate confidence
        output()  -> generate curated feed Markdown
    """

    agent_name = "feed_curator"
    agent_category = AgentCategory.CONTENT.value
    version = FEED_CURATOR_CONFIG.version

    def __init__(
        self,
        persist: bool = False,
        input_limit: int = FEED_CURATOR_CONFIG.default_input_limit,
        output_limit: int = FEED_CURATOR_CONFIG.default_output_limit,
        fetch_thumbnails: bool = True,
    ) -> None:
        super().__init__()
        self.config = FEED_CURATOR_CONFIG
        self.persist = persist
        self.input_limit = input_limit
        self.output_limit = output_limit
        self.fetch_thumbnails = fetch_thumbnails

        self._db_session: Optional[Any] = None
        self._llm_client = LLMClient(LLMConfig(
            max_tokens=4096,
            temperature=0.3,
        ))
        self._curated_items: List[CuratedItem] = []
        self._raw_signals: List[dict] = []

    def set_db_session(self, session: Any) -> None:
        """Set DB session for signal loading.

        Args:
            session: SQLAlchemy session instance.
        """
        self._db_session = session

    def collect(self) -> List[Any]:
        """Load recent social signals from the database.

        Returns:
            List of signal dicts from DB, or empty list if no session.
        """
        if self._db_session is None:
            logger.warning("No DB session set, cannot load signals")
            return []

        signals = load_recent_signals(
            session=self._db_session,
            limit=self.input_limit,
        )
        self._raw_signals = signals
        return signals

    def process(self, raw_data: List[Any]) -> List[Any]:
        """Filter spam, curate via LLM, and enrich with thumbnails.

        Args:
            raw_data: Signal dicts from collect().

        Returns:
            List of CuratedItem instances.
        """
        signals = raw_data

        # Step 1: Pre-filter spam
        filtered = pre_filter_spam(signals)
        logger.info(
            "Pre-filter: %d -> %d signals",
            len(signals),
            len(filtered),
        )

        # Step 2: LLM curation
        curated = curate_via_llm(
            signals=filtered,
            output_limit=self.output_limit,
            llm_client=self._llm_client,
        )

        # Step 3: Enrichment (thumbnails, embeds). Pass the DB session so the
        # enricher can fall back to social_signals.text (HTML, with <img>)
        # when og:image fetch fails — Reddit RSS embeds previews inline.
        if curated:
            curated = enrich_items(
                curated,
                fetch_thumbnails=self.fetch_thumbnails,
                session=self._db_session,
            )

        self._curated_items = curated
        logger.info("Curation complete: %d items", len(curated))

        return curated

    def score(self, processed_data: List[Any]) -> List[ConfidenceScore]:
        """Compute aggregate confidence for this curation run.

        Data quality scales with the number of input signals.
        Analysis confidence scales with the number of curated items
        and whether the LLM was available.

        Args:
            processed_data: List of CuratedItem from process().

        Returns:
            List with a single aggregate ConfidenceScore.
        """
        curated: List[CuratedItem] = processed_data

        if not curated:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

        # More input signals = higher data quality
        signal_count = len(self._raw_signals)
        dq = min(1.0, signal_count / 50)  # saturates at 50 signals

        # More curated items with high scores = higher analysis confidence
        avg_relevance = sum(c.relevance_score for c in curated) / len(curated)
        ac = min(1.0, (avg_relevance / 100) * 0.7 + (len(curated) / self.output_limit) * 0.3)

        return [ConfidenceScore(data_quality=dq, analysis_confidence=ac)]

    def output(
        self,
        processed_data: List[Any],
        scores: List[ConfidenceScore],
    ) -> AgentOutput:
        """Generate curated feed as publishable Markdown.

        Args:
            processed_data: List of CuratedItem from process().
            scores: Aggregate confidence scores.

        Returns:
            AgentOutput with Markdown body and structured metadata.
        """
        curated: List[CuratedItem] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3,
        )

        # Body is the editorial intro that renders as a banner on /feed.
        # The actual item stream lives in `curated_feed_items` and is fetched
        # separately by the frontend; repeating items here would be duplicate.
        intro_md = self._generate_intro(curated)
        body_md = intro_md or (
            f"*{len(curated)} itens selecionados de {len(self._raw_signals)} sinais. "
            f"Atualizado semanalmente.*"
        )

        # Build metadata
        source_urls = [c.source_url for c in curated if c.source_url]
        metadata = {
            "curated_count": len(curated),
            "input_signal_count": len(self._raw_signals),
            "categories": _count_categories(curated),
            "items": [
                {
                    "content_hash": c.content_hash,
                    "editorial_headline": c.editorial_headline,
                    "editorial_context": c.editorial_context,
                    "relevance_score": c.relevance_score,
                    "category": c.category,
                    "source_platform": c.source_platform,
                    "source_url": c.source_url,
                    "source_author": c.source_author,
                    "thumbnail_url": c.thumbnail_url,
                    "embed_type": c.embed_type,
                    "embed_url": c.embed_url,
                }
                for c in curated
            ],
        }

        editorial_title = self._generate_title(curated)

        return AgentOutput(
            title=editorial_title,
            body_md=body_md,
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            run_id=self.run_id,
            confidence=confidence,
            sources=source_urls[:30],
            content_type="FEED",
            summary=f"{len(curated)} sinais curados de {len(self._raw_signals)} coletados.",
            metadata=metadata,
        )

    def _generate_intro(self, curated: List[CuratedItem]) -> Optional[str]:
        """Generate a 2-3 paragraph editorial intro that banners /feed.

        Signed by the Ana Torres persona. Returns None when LLM is
        unavailable or generation fails, so callers can fall back to a
        template line.
        """
        if not curated:
            return None

        try:
            from apps.agents.base.llm import LLMClient
            client = LLMClient()
        except Exception:
            return None
        if not client.is_available:
            return None

        top = curated[:5]
        items_context = "\n".join(
            f"- [{c.category}] {c.editorial_headline} ({c.source_platform})"
            for c in top
        )
        cat_counts = _count_categories(curated)
        cat_line = ", ".join(
            f"{k} ({v})" for k, v in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        system = (
            "Voce e Ana Torres, editora do FEED CURADO da Sinal.lab. Seu trabalho e "
            "destacar os sinais sociais mais relevantes da semana para fundadores, CTOs "
            "e VCs LATAM. Escreve em primeira pessoa, tom editorial, analitico.\n\n"
            "Regras:\n"
            "- Portugues brasileiro, tom direto, sem hype\n"
            "- NUNCA use em dash (U+2014)\n"
            "- NAO use 'nesta semana', 'vale ressaltar', 'e importante destacar'\n"
            "- Cite temas e numeros concretos\n"
            "- Assinatura e automatica, NAO adicione 'Ana Torres' no final"
        )
        prompt = (
            f"Escreva a INTRO EDITORIAL (2 a 3 paragrafos, 150-250 palavras total) do FEED "
            f"CURADO desta semana. O feed tem {len(curated)} itens selecionados de "
            f"{len(self._raw_signals)} sinais coletados.\n\n"
            f"Top 5 destaques da semana:\n{items_context}\n\n"
            f"Distribuicao por categoria: {cat_line}\n\n"
            "Direcoes:\n"
            "- Paragrafo 1: Qual tema ou debate conecta os destaques? Abra com a tese.\n"
            "- Paragrafo 2: Cite 2-3 destaques concretos com 'por que importa pra quem constroi'\n"
            "- Paragrafo 3 (opcional): Contraste, padrao observado ou implicacao setorial\n"
            "- NAO liste todos os itens; o /feed ja mostra cada card\n"
            "- Retorne APENAS o corpo em Markdown (sem titulo H1, sem bloco de codigo)"
        )
        result = client.generate(
            user_prompt=prompt,
            system_prompt=system,
            max_tokens=600,
            temperature=0.5,
        )
        if result and result.strip():
            return result.strip()
        return None

    def _generate_title(self, curated: List[CuratedItem]) -> str:
        """Generate editorial title from the top curated items."""
        default = "Feed Curado por Ana Torres"
        if not curated:
            return default

        try:
            from apps.agents.base.llm import LLMClient
            client = LLMClient()
        except Exception:
            return default
        if not client.is_available:
            return default

        # Top 5 items by relevance (curated already sorted)
        top = curated[:5]
        items_context = "\n".join(
            f"- [{c.category}] {c.editorial_headline} ({c.source_platform})"
            for c in top
        )
        cat_counts = _count_categories(curated)
        cat_line = ", ".join(
            f"{k} ({v})" for k, v in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        system = (
            "Voce e Ana Torres, editora do FEED CURADO da Sinal.lab. Seu trabalho e "
            "destacar os sinais sociais mais relevantes da semana para fundadores, CTOs "
            "e VCs LATAM. O FEED e uma selecao editorial dos melhores posts, videos e "
            "discussoes que cruzaram seu radar.\n\n"
            "Estilo editorial:\n"
            "- Tom editorial, factual, assinado\n"
            "- Cite temas concretos, nao meta-descricao ('Feed Curado')\n"
            "- Portugues brasileiro\n"
            "- NUNCA use em dash\n"
            "- Sem hype, sem clichês"
        )
        prompt = (
            f"Crie um titulo editorial (maximo 15 palavras) para o FEED CURADO desta semana. "
            f"O feed destaca {len(curated)} sinais dos melhores posts/videos/discussoes do "
            f"ecossistema tech LATAM.\n\n"
            f"Top 5 itens selecionados:\n{items_context}\n\n"
            f"Distribuicao por categoria: {cat_line}\n\n"
            "Direcoes:\n"
            "- NAO comece com 'Feed Curado' ou 'Esta semana'\n"
            "- Angulo: qual tema ou debate domina a selecao desta semana\n"
            "- Foque no conteudo, nao no processo editorial\n"
            "- Exemplos: 'AI agents em producao dividem opinioes no LinkedIn BR', "
            "'Discussoes sobre Open Finance superam AI esta semana'\n"
            "- Retorne APENAS o titulo"
        )
        result = client.generate(
            user_prompt=prompt, system_prompt=system, max_tokens=80, temperature=0.5,
        )
        if result and result.strip():
            return result.strip().strip('"').strip("'")
        return default


def _count_categories(items: List[CuratedItem]) -> dict:
    """Count items per category.

    Args:
        items: Curated items.

    Returns:
        Dict mapping category name to count.
    """
    counts: dict = {}
    for item in items:
        counts[item.category] = counts.get(item.category, 0) + 1
    return counts
