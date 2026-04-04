"""Social Signals Intelligence Agent.

Monitors Twitter/X, Reddit, Bluesky, and newsletter RSS feeds to detect
emerging signals in AI, Fintech, and Banking before they become consensus.
Produces a Weekly Pulse report with cluster analysis, top voices, and
strategic implications.

This is a DATA agent: it collects and indexes all relevant social signals
without editorial filtering. The editorial pipeline handles publication
decisions downstream.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.config import AgentCategory, DataSourceConfig
from apps.agents.base.llm import LLMClient
from apps.agents.base.output import AgentOutput
from apps.agents.social_signals.collector import collect_all
from apps.agents.social_signals.config import SOCIAL_SIGNALS_CONFIG
from apps.agents.social_signals.historical import (
    build_historical_context,
    load_previous_clusters,
)
from apps.agents.social_signals.models import (
    ProcessedSignal,
    SignalClusterResult,
    SocialPost,
)
from apps.agents.social_signals.pipeline import run_pipeline

logger = logging.getLogger(__name__)


class SocialSignalsAgent(BaseAgent):
    """Social Signal Intelligence Agent.

    Monitors social media platforms and newsletters to detect emerging
    signals in AI, Fintech, and Banking across LATAM and global markets.

    Lifecycle:
        collect() -> fetch from Twitter, Reddit, Bluesky, RSS
        process() -> classify (batch), cluster, score signals (with historical context)
        score()   -> compute aggregate confidence
        output()  -> generate Weekly Pulse Markdown report
    """

    agent_name = "social_signals"
    agent_category = AgentCategory.DATA.value
    version = SOCIAL_SIGNALS_CONFIG.version

    # Enable async collection by default (falls back to sync on failure)
    use_async = True

    def __init__(self, week_number: int = 1) -> None:
        super().__init__()
        self.config = SOCIAL_SIGNALS_CONFIG
        self.week_number = week_number
        self._llm_client = LLMClient()

        # Pipeline state (populated during process())
        self._clusters: List[SignalClusterResult] = []
        self._all_signals: List[ProcessedSignal] = []

        # Historical context (loaded from DB when session is available)
        self._historical_context: Optional[Dict[str, Any]] = None
        self._db_session: Optional[Any] = None

        # Timing info for async vs sync comparison
        self._collect_method: str = ""
        self._collect_elapsed: float = 0.0

    def collect(self) -> List[Any]:
        """Fetch posts from all configured social media sources.

        When use_async is True (default), runs all platform collectors in
        parallel via asyncio.to_thread(). Falls back to sequential sync
        collection if async fails.

        Returns:
            List of SocialPost items, deduplicated by content_hash.
        """
        sources = self.config.get_enabled_sources()
        logger.info(
            "Social Signals collecting from %d enabled sources (async=%s)",
            len(sources),
            self.use_async,
        )

        start = time.monotonic()

        if self.use_async:
            posts = self._collect_async(sources)
            if posts is not None:
                self._collect_method = "async"
                self._collect_elapsed = time.monotonic() - start
                logger.info(
                    "Async collection completed: %d posts in %.2fs",
                    len(posts),
                    self._collect_elapsed,
                )
                return posts
            # Async failed, fall through to sync
            logger.warning("Async collection failed, falling back to sync")

        posts = collect_all(
            sources=sources,
            provenance=self.provenance,
            agent_name=self.agent_name,
            run_id=self.run_id,
            db_session=self._db_session,
        )
        self._collect_method = "sync"
        self._collect_elapsed = time.monotonic() - start
        logger.info(
            "Sync collection completed: %d posts in %.2fs",
            len(posts),
            self._collect_elapsed,
        )
        return posts

    def _collect_async(
        self, sources: List[DataSourceConfig],
    ) -> Optional[List[SocialPost]]:
        """Attempt async parallel collection. Returns None on failure.

        Uses asyncio.run() to execute the async collector. If we are already
        inside an event loop (e.g., Jupyter, nested async), this will fail
        gracefully and return None so the caller can fall back to sync.

        Args:
            sources: Enabled data source configs.

        Returns:
            List of SocialPost on success, None on failure.
        """
        try:
            from apps.agents.social_signals.async_collector import async_collect_all

            return asyncio.run(async_collect_all(
                sources=sources,
                provenance=self.provenance,
                agent_name=self.agent_name,
                run_id=self.run_id,
                db_session=self._db_session,
            ))
        except RuntimeError as exc:
            # "cannot be called from a running event loop"
            logger.warning("Cannot start async event loop: %s", exc)
            return None
        except Exception as exc:
            logger.warning("Async collection raised unexpected error: %s", exc)
            return None

    def set_db_session(self, session: Any) -> None:
        """Set DB session for historical context loading.

        Called by the orchestrator or CLI before process() to enable
        historical velocity/sentiment comparisons.

        Args:
            session: SQLAlchemy session instance.
        """
        self._db_session = session

    def _load_historical_context(self) -> Optional[Dict[str, Any]]:
        """Load historical context from DB if session is available.

        Returns:
            Historical context dict, or None if DB is unavailable.
        """
        if self._db_session is None:
            logger.info("No DB session, skipping historical context (first run?)")
            return None

        try:
            previous_clusters = load_previous_clusters(
                session=self._db_session,
                weeks_back=4,
            )
            if not previous_clusters:
                logger.info("No previous clusters found in DB")
                return None

            context = build_historical_context(previous_clusters)
            logger.info(
                "Loaded historical context: %d themes, %d known authors",
                len(context.get("theme_counts", {})),
                len(context.get("known_authors", set())),
            )
            return context

        except Exception as exc:
            logger.warning("Failed to load historical context: %s", exc)
            return None

    def process(self, raw_data: List[Any]) -> List[Any]:
        """Classify, cluster, and score all collected signals.

        Runs the full pipeline with batch classification (keyword-first,
        LLM for top 20 only) and historical context for velocity/sentiment
        dimensions.

        Args:
            raw_data: List of SocialPost from collect().

        Returns:
            List of SignalClusterResult sorted by composite score.
        """
        posts: List[SocialPost] = raw_data

        # Load historical context for velocity and sentiment baselines
        if self._historical_context is None:
            self._historical_context = self._load_historical_context()

        self._clusters, self._all_signals = run_pipeline(
            posts=posts,
            llm_client=self._llm_client,
            historical_context=self._historical_context,
            top_n_for_llm=20,
        )

        logger.info(
            "Processed %d posts into %d clusters (%d themed signals)",
            len(posts),
            len(self._clusters),
            len([s for s in self._all_signals if s.theme]),
        )

        return self._clusters

    def score(self, processed_data: List[Any]) -> List[ConfidenceScore]:
        """Compute aggregate confidence score for this run.

        Data quality is based on source diversity (number of distinct
        platforms and sources contributing signals). Analysis confidence
        scales with the number of themed signals and clusters found.

        Args:
            processed_data: List of SignalClusterResult from process().

        Returns:
            List containing a single aggregate ConfidenceScore.
        """
        clusters: List[SignalClusterResult] = processed_data

        if not clusters:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

        # Count distinct sources and platforms
        source_names = set()
        platforms = set()
        for cluster in clusters:
            for signal in cluster.signals:
                source_names.add(signal.post.source_name)
                platforms.add(signal.post.platform)

        confidence = compute_confidence(
            source_count=len(source_names),
            sources_verified=0,
            data_freshness_days=0,
            cross_validated=len(platforms) >= 2,
        )

        return [confidence]

    def output(
        self,
        processed_data: List[Any],
        scores: List[ConfidenceScore],
    ) -> AgentOutput:
        """Generate the Weekly Pulse report as publishable Markdown.

        Sections:
            1. Temas em Aceleracao (top clusters with stage=accelerating)
            2. Sinais Emergentes (top clusters with stage=emerging)
            3. Posts mais Relevantes (top posts across all clusters)
            4. Vozes da Semana (top voices across all clusters)
            5. Startups para Monitorar (companies from entity mentions)
            6. Implicacoes Setoriais (LLM-generated strategic implications)

        Args:
            processed_data: List of SignalClusterResult from process().
            scores: List containing the aggregate ConfidenceScore.

        Returns:
            AgentOutput with Markdown body and structured metadata.
        """
        clusters: List[SignalClusterResult] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3,
        )

        # Generate editorial title
        editorial_title = self._generate_title(clusters)

        # Build Markdown body
        body_sections: List[str] = []
        body_sections.append(
            f"# Social Signal Intelligence - Semana {self.week_number}\n"
        )

        themed_count = len([s for s in self._all_signals if s.theme])
        platform_count = len(set(s.post.platform for s in self._all_signals))
        body_sections.append(
            f"*{themed_count} sinais analisados de {platform_count} plataformas. "
            f"{len(clusters)} clusters identificados.*\n"
        )

        # Section 1: Temas em Aceleracao
        accelerating = [
            c for c in clusters if c.narrative_stage == "accelerating"
        ][:5]
        body_sections.append(
            self._render_cluster_section(
                "Temas em Aceleracao", accelerating,
            )
        )

        # Section 2: Sinais Emergentes
        emerging = [
            c for c in clusters if c.narrative_stage == "emerging"
        ][:5]
        body_sections.append(
            self._render_cluster_section(
                "Sinais Emergentes", emerging,
            )
        )

        # Section 3: Posts mais Relevantes
        body_sections.append(self._render_top_posts(clusters))

        # Section 4: Vozes da Semana
        body_sections.append(self._render_top_voices(clusters))

        # Section 5: Startups para Monitorar
        body_sections.append(self._render_companies(clusters))

        # Section 6: Implicacoes Setoriais
        body_sections.append(self._render_implications(clusters))

        body_md = "\n".join(body_sections)

        # Build structured metadata for API and email rendering
        source_urls = self.provenance.get_source_urls()[:30]
        metadata = self._build_metadata(clusters)

        return AgentOutput(
            title=editorial_title,
            body_md=body_md,
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            run_id=self.run_id,
            confidence=confidence,
            sources=source_urls,
            content_type="ANALYSIS",
            summary=(
                f"Semana {self.week_number}: {themed_count} sinais sociais "
                f"analisados de {len(self.provenance.get_sources())} fontes. "
                f"{len(clusters)} clusters identificados."
            ),
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_title(self, clusters: List[SignalClusterResult]) -> str:
        """Generate an editorial title for the Weekly Pulse.

        Uses LLM when available, falls back to template-based title.

        Args:
            clusters: Scored clusters for context.

        Returns:
            Title string.
        """
        if clusters and self._llm_client.is_available:
            top_themes = [c.name for c in clusters[:3]]
            prompt = (
                f"Generate a concise, compelling title (max 80 chars) for a weekly "
                f"social signal intelligence report covering these top themes: "
                f"{', '.join(top_themes)}.\n\n"
                f"The report covers AI, Fintech, and Banking signals from social media.\n"
                f"Write in Portuguese (Brazil). Do NOT use em dash.\n"
                f"Reply with ONLY the title."
            )
            result = self._llm_client.generate(
                user_prompt=prompt,
                system_prompt="You write concise Portuguese titles for tech intelligence reports.",
                max_tokens=50,
                temperature=0.5,
            )
            if result and result.strip():
                return result.strip().strip('"')

        return f"Social Signal Intelligence - Semana {self.week_number}"

    def _render_cluster_section(
        self,
        heading: str,
        clusters: List[SignalClusterResult],
    ) -> str:
        """Render a Markdown section for a list of clusters.

        Args:
            heading: Section heading (e.g., "Temas em Aceleracao").
            clusters: Clusters to render.

        Returns:
            Markdown string for this section.
        """
        lines = [f"## {heading}\n"]

        if not clusters:
            lines.append("*Nenhum sinal nesta categoria esta semana.*\n")
            return "\n".join(lines)

        for cluster in clusters:
            score = cluster.composite_score
            dims = cluster.dimensions
            signal_count = cluster.signal_count
            platforms = ", ".join(cluster.platforms)

            lines.append(f"### {cluster.name}")
            lines.append(
                f"**Score:** {score:.2f} | "
                f"**Sinais:** {signal_count} | "
                f"**Plataformas:** {platforms} | "
                f"**Estagio:** {cluster.narrative_stage}"
            )

            if dims:
                lines.append(
                    f"Volume: {dims.volume:.2f} | "
                    f"Velocidade: {dims.velocity:.2f} | "
                    f"Autoridade: {dims.authority_concentration:.2f} | "
                    f"Cross-platform: {dims.cross_platform_propagation:.2f}"
                )

            if cluster.description:
                lines.append(f"\n> {cluster.description}")

            if cluster.related_companies:
                companies = [c["name"] for c in cluster.related_companies[:5]]
                lines.append(f"\n**Empresas mencionadas:** {', '.join(companies)}")

            lines.append("")

        return "\n".join(lines)

    def _render_top_posts(self, clusters: List[SignalClusterResult]) -> str:
        """Render top 10 posts across all clusters.

        Args:
            clusters: All scored clusters.

        Returns:
            Markdown section string.
        """
        lines = ["## Posts mais Relevantes\n"]

        # Aggregate top posts from all clusters, take top 10
        all_top: List[dict] = []
        for cluster in clusters:
            all_top.extend(cluster.top_posts)

        # Sort by engagement (likes + replies*2 + reposts*3)
        def _engagement(p: dict) -> float:
            m = p.get("metrics", {})
            return (
                m.get("likes", 0)
                + m.get("replies", 0) * 2
                + m.get("reposts", 0) * 3
                + m.get("score", 0)
            )

        all_top.sort(key=_engagement, reverse=True)

        for i, post in enumerate(all_top[:10], 1):
            author = post.get("author", "")
            platform = post.get("platform", "")
            text = post.get("text", "")[:120]
            url = post.get("url", "")

            lines.append(
                f"{i}. **{author}** ({platform}): {text}"
                + (f" [link]({url})" if url else "")
            )

        if not all_top:
            lines.append("*Nenhum post relevante identificado.*")

        lines.append("")
        return "\n".join(lines)

    def _render_top_voices(self, clusters: List[SignalClusterResult]) -> str:
        """Render top 10 voices across all clusters.

        Args:
            clusters: All scored clusters.

        Returns:
            Markdown section string.
        """
        lines = ["## Vozes da Semana\n"]

        # Aggregate voices, dedup by handle, sort by authority
        seen_handles: set = set()
        all_voices: List[dict] = []
        for cluster in clusters:
            for voice in cluster.top_voices:
                handle = voice.get("handle", "")
                if handle and handle not in seen_handles:
                    seen_handles.add(handle)
                    all_voices.append(voice)

        all_voices.sort(
            key=lambda v: v.get("authority", 0) * 0.6 + min(1.0, v.get("signal_count", 0) / 10) * 0.4,
            reverse=True,
        )

        for i, voice in enumerate(all_voices[:10], 1):
            handle = voice.get("handle", "")
            name = voice.get("name", handle)
            platform = voice.get("platform", "")
            authority = voice.get("authority", 0)
            count = voice.get("signal_count", 0)

            lines.append(
                f"{i}. **{name}** (@{handle}, {platform}) "
                f"- autoridade: {authority:.2f}, sinais: {count}"
            )

        if not all_voices:
            lines.append("*Nenhuma voz relevante identificada.*")

        lines.append("")
        return "\n".join(lines)

    def _render_companies(self, clusters: List[SignalClusterResult]) -> str:
        """Render companies mentioned across all clusters.

        Args:
            clusters: All scored clusters.

        Returns:
            Markdown section string.
        """
        lines = ["## Startups para Monitorar\n"]

        # Aggregate company mentions
        company_total: dict = {}
        for cluster in clusters:
            for company in cluster.related_companies:
                name = company["name"]
                count = company.get("mention_count", 1)
                if name in company_total:
                    company_total[name] += count
                else:
                    company_total[name] = count

        sorted_companies = sorted(
            company_total.items(), key=lambda x: x[1], reverse=True,
        )

        for i, (name, count) in enumerate(sorted_companies[:15], 1):
            lines.append(f"{i}. **{name}** ({count} mencoes)")

        if not sorted_companies:
            lines.append("*Nenhuma startup identificada nas mencoes.*")

        lines.append("")
        return "\n".join(lines)

    def _render_implications(self, clusters: List[SignalClusterResult]) -> str:
        """Render strategic implications section.

        Uses LLM to generate 3 implications from the top clusters.
        Falls back to a template-based summary.

        Args:
            clusters: All scored clusters.

        Returns:
            Markdown section string.
        """
        lines = ["## Implicacoes Setoriais\n"]

        if clusters and self._llm_client.is_available:
            cluster_summaries = []
            for c in clusters[:5]:
                cluster_summaries.append(
                    f"- {c.name} (score: {c.composite_score:.2f}, "
                    f"stage: {c.narrative_stage}, "
                    f"signals: {c.signal_count})"
                )

            prompt = (
                f"Based on these social signal clusters from the past week, "
                f"write exactly 3 strategic implications for tech founders "
                f"and CTOs in LATAM. Write in Portuguese (Brazil).\n\n"
                f"Clusters:\n" + "\n".join(cluster_summaries) + "\n\n"
                f"Format each implication as a numbered item (1. 2. 3.) "
                f"with a bold title and 1-2 sentence explanation.\n"
                f"Do NOT use em dash."
            )

            result = self._llm_client.generate(
                user_prompt=prompt,
                system_prompt=(
                    "You are an analyst writing strategic implications for "
                    "a LATAM tech intelligence report. Be specific and actionable."
                ),
                max_tokens=500,
                temperature=0.5,
            )

            if result and result.strip():
                lines.append(result.strip())
                lines.append("")
                return "\n".join(lines)

        # Fallback: template-based implications
        if clusters:
            top = clusters[0]
            lines.append(
                f"1. **{top.name} ganha tracao:** "
                f"com {top.signal_count} sinais e score de {top.composite_score:.2f}, "
                f"este tema merece atencao imediata de fundadores no espaco."
            )
            if len(clusters) > 1:
                second = clusters[1]
                lines.append(
                    f"2. **{second.name} em movimento:** "
                    f"sinais de {', '.join(second.platforms)} indicam "
                    f"interesse crescente no tema."
                )
            lines.append(
                "3. **Monitoramento continuo recomendado:** "
                "os sinais desta semana sugerem mudancas nas narrativas "
                "dominantes do ecossistema."
            )
        else:
            lines.append(
                "*Sem sinais suficientes para gerar implicacoes esta semana.*"
            )

        lines.append("")
        return "\n".join(lines)

    def _build_metadata(self, clusters: List[SignalClusterResult]) -> dict:
        """Build structured metadata for API responses and email rendering.

        Args:
            clusters: All scored clusters.

        Returns:
            Dict with cluster summaries, top posts, top voices, and counts.
        """
        return {
            "week_number": self.week_number,
            "cluster_count": len(clusters),
            "total_signals": len(self._all_signals),
            "themed_signals": len([s for s in self._all_signals if s.theme]),
            "total_sources": len(self.provenance.get_sources()),
            "clusters": [
                {
                    "name": c.name,
                    "slug": c.slug,
                    "theme": c.theme,
                    "sub_theme": c.sub_theme,
                    "signal_count": c.signal_count,
                    "composite_score": round(c.composite_score, 3),
                    "narrative_stage": c.narrative_stage,
                    "platforms": c.platforms,
                    "dimensions": c.dimensions.to_dict() if c.dimensions else {},
                    "top_voices": c.top_voices[:5],
                    "top_posts": c.top_posts[:5],
                    "related_companies": c.related_companies[:5],
                }
                for c in clusters[:20]
            ],
        }
