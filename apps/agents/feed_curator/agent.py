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

        # Step 3: Enrichment (thumbnails, embeds)
        if curated:
            curated = enrich_items(
                curated,
                fetch_thumbnails=self.fetch_thumbnails,
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

        # Build Markdown
        lines: List[str] = [
            "# Feed Curado\n",
            f"*{len(curated)} itens selecionados de {len(self._raw_signals)} sinais.*\n",
        ]

        for i, item in enumerate(curated, 1):
            lines.append(f"## {i}. {item.editorial_headline}")
            lines.append(f"**{item.category}** | Score: {item.relevance_score}/100")
            lines.append(f"\n{item.editorial_context}\n")

            if item.source_url:
                lines.append(f"[Fonte: {item.source_platform}]({item.source_url})")

            if item.embed_type:
                lines.append(f"\n*Embed: {item.embed_type}*")

            lines.append("")

        body_md = "\n".join(lines)

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

        return AgentOutput(
            title="Feed Curado por Ana Torres",
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
