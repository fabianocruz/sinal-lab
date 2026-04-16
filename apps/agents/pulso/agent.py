"""PULSO Agent — Social signal clustering, scoring, and weekly pulse.

Takes pre-collected, pre-classified signals from VOZES and produces
the Weekly Pulse report with cluster analysis, top voices, and
strategic implications.

This is a DATA agent: it clusters and scores all signals without
editorial filtering. The editorial pipeline handles publication
decisions downstream.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.config import AgentCategory
from apps.agents.base.llm import LLMClient
from apps.agents.base.output import AgentOutput
from apps.agents.pulso.config import PULSO_CONFIG
from apps.agents.pulso.models import (
    PipelineResult,
    ProcessedSignal,
    SignalClusterResult,
    SocialPost,
)
from apps.agents.pulso.pipeline import run_pipeline

logger = logging.getLogger(__name__)


class PulsoAgent(BaseAgent):
    """PULSO Agent for social signal clustering and scoring.

    Lifecycle:
        collect() -> load pre-classified signals from VOZES output
        process() -> cluster and score signals
        score()   -> compute aggregate confidence
        output()  -> generate Weekly Pulse Markdown report
    """

    agent_name = "pulso"
    agent_category = AgentCategory.DATA.value
    version = PULSO_CONFIG.version

    def __init__(self, week_number: int = 1) -> None:
        super().__init__()
        self.config = PULSO_CONFIG
        self.week_number = week_number
        self._llm_client = LLMClient()

        # Pipeline state
        self._clusters: List[SignalClusterResult] = []
        self._all_signals: List[ProcessedSignal] = []

        # Historical context (loaded from DB when session is available)
        self._historical_context: Optional[Dict[str, Any]] = None
        self._db_session: Optional[Any] = None

        # Pre-computed embeddings from VOZES
        self._signal_embeddings: Dict[str, List[float]] = {}

        # Path to VOZES output JSON (set via CLI or orchestrator)
        self._vozes_output_path: Optional[str] = None

    def set_db_session(self, session: Any) -> None:
        """Set DB session for historical context and persistence."""
        self._db_session = session

    def set_vozes_output(self, path: str) -> None:
        """Set path to VOZES agent output JSON."""
        self._vozes_output_path = path

    def collect(self) -> List[Any]:
        """Load pre-classified ProcessedSignals from VOZES output.

        Tries in order:
            1. VOZES output JSON file (if path set)
            2. Database query for recent signals
            3. Empty list (no data)

        Returns:
            List of ProcessedSignal items.
        """
        # Try loading from JSON file
        if self._vozes_output_path:
            signals = self._load_from_json(self._vozes_output_path)
            if signals:
                logger.info("Loaded %d signals from VOZES output: %s", len(signals), self._vozes_output_path)
                return signals

        # Try loading from database
        if self._db_session:
            signals = self._load_from_db()
            if signals:
                logger.info("Loaded %d signals from database", len(signals))
                return signals

        logger.warning("No VOZES data available, returning empty signal list")
        return []

    def _load_from_json(self, path: str) -> List[ProcessedSignal]:
        """Load ProcessedSignals from a VOZES output JSON file."""
        try:
            file_path = Path(path)
            if not file_path.exists():
                logger.warning("VOZES output file not found: %s", path)
                return []

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            signals: List[ProcessedSignal] = []
            for item in data.get("signals", []):
                post = SocialPost(
                    text=item.get("text", ""),
                    url=item.get("url", ""),
                    platform=item.get("platform", ""),
                    author_handle=item.get("author_handle", ""),
                    author_display_name=item.get("author_display_name", ""),
                    author_followers=item.get("author_followers", 0),
                    source_name=item.get("source_name", ""),
                    metrics=item.get("metrics", {}),
                    content_hash=item.get("content_hash", ""),
                )
                signal = ProcessedSignal(
                    post=post,
                    theme=item.get("theme", ""),
                    sub_theme=item.get("sub_theme", ""),
                    sentiment=item.get("sentiment", 0.0),
                    authority_score=item.get("authority_score", 0.0),
                    is_commercial=item.get("is_commercial", False),
                )
                signals.append(signal)

            # Load embeddings if present
            if "embeddings" in data:
                self._signal_embeddings = data["embeddings"]

            return signals

        except Exception as exc:
            logger.error("Failed to load VOZES JSON: %s", exc)
            return []

    def _load_from_db(self) -> List[ProcessedSignal]:
        """Load recent signals from the database."""
        try:
            from packages.database.models.social_signal import SocialSignal
            from sqlalchemy import desc

            records = (
                self._db_session.query(SocialSignal)
                .order_by(desc(SocialSignal.collected_at))
                .limit(self.config.max_items_per_run)
                .all()
            )

            signals: List[ProcessedSignal] = []
            for r in records:
                post = SocialPost(
                    text=r.text or "",
                    url=r.post_url or "",
                    platform=r.platform or "",
                    author_handle=r.author_handle or "",
                    author_display_name=r.author_display_name or "",
                    metrics=r.metrics or {},
                    content_hash=r.content_hash or "",
                )
                signal = ProcessedSignal(
                    post=post,
                    theme=r.theme or "",
                    sub_theme=r.sub_theme or "",
                    sentiment=r.sentiment or 0.0,
                    authority_score=r.authority_score or 0.0,
                )
                signals.append(signal)

                # Load embedding if available
                if r.embedding_json:
                    self._signal_embeddings[r.content_hash] = r.embedding_json

            return signals

        except Exception as exc:
            logger.warning("Failed to load signals from DB: %s", exc)
            return []

    def _load_historical_context(self) -> Optional[Dict[str, Any]]:
        """Load historical context from DB if session is available."""
        if self._db_session is None:
            logger.info("No DB session, skipping historical context")
            return None

        try:
            from apps.agents.social_signals.historical import (
                build_historical_context,
                load_previous_clusters,
            )

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
        """Cluster and score all pre-classified signals.

        Args:
            raw_data: List of ProcessedSignal from collect().

        Returns:
            List of SignalClusterResult sorted by composite score.
        """
        signals: List[ProcessedSignal] = raw_data

        if self._historical_context is None:
            self._historical_context = self._load_historical_context()

        result = run_pipeline(
            signals=signals,
            llm_client=self._llm_client,
            historical_context=self._historical_context,
            signal_embeddings=self._signal_embeddings or None,
        )
        self._clusters = result.clusters
        self._all_signals = result.all_signals

        logger.info(
            "Processed %d signals into %d clusters",
            len(signals),
            len(self._clusters),
        )

        return self._clusters

    def score(self, processed_data: List[Any]) -> List[ConfidenceScore]:
        """Compute aggregate confidence score for this run."""
        clusters: List[SignalClusterResult] = processed_data

        if not clusters:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

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
            1. Temas em Aceleracao
            2. Sinais Emergentes
            3. Posts mais Relevantes
            4. Vozes da Semana
            5. Startups para Monitorar
            6. Implicacoes Setoriais
        """
        clusters: List[SignalClusterResult] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3,
        )

        editorial_title = self._generate_title(clusters)

        body_sections: List[str] = []
        body_sections.append(
            f"# Pulso Semanal - Semana {self.week_number}\n"
        )

        themed_count = len([s for s in self._all_signals if s.theme])
        platform_count = len(set(s.post.platform for s in self._all_signals)) if self._all_signals else 0
        body_sections.append(
            f"*{themed_count} sinais analisados de {platform_count} plataformas. "
            f"{len(clusters)} clusters identificados.*\n"
        )

        # Section 1: Temas em Aceleracao
        accelerating = [c for c in clusters if c.narrative_stage == "accelerating"][:5]
        body_sections.append(self._render_cluster_section("Temas em Aceleracao", accelerating))

        # Section 2: Sinais Emergentes
        emerging = [c for c in clusters if c.narrative_stage == "emerging"][:5]
        body_sections.append(self._render_cluster_section("Sinais Emergentes", emerging))

        # Section 3: Posts mais Relevantes
        body_sections.append(self._render_top_posts(clusters))

        # Section 4: Vozes da Semana
        body_sections.append(self._render_top_voices(clusters))

        # Section 5: Startups para Monitorar
        body_sections.append(self._render_companies(clusters))

        # Section 6: Implicacoes Setoriais
        body_sections.append(self._render_implications(clusters))

        body_md = "\n".join(body_sections)

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
                f"clusterizados e pontuados. {len(clusters)} clusters identificados."
            ),
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_title(self, clusters: List[SignalClusterResult]) -> str:
        """Generate an editorial title for the Weekly Pulse."""
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

        return f"Pulso Semanal - Semana {self.week_number}"

    def _render_cluster_section(
        self,
        heading: str,
        clusters: List[SignalClusterResult],
    ) -> str:
        """Render a Markdown section for a list of clusters."""
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
        """Render top 10 posts across all clusters."""
        lines = ["## Posts mais Relevantes\n"]

        all_top: List[dict] = []
        for cluster in clusters:
            all_top.extend(cluster.top_posts)

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
        """Render top 10 voices across all clusters."""
        lines = ["## Vozes da Semana\n"]

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
        """Render companies mentioned across all clusters."""
        lines = ["## Startups para Monitorar\n"]

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
        """Render strategic implications section."""
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

        # Fallback
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
        """Build structured metadata for API responses."""
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
                    "platform_distribution": c.platform_distribution,
                    "dimensions": c.dimensions.to_dict() if c.dimensions else {},
                    "top_voices": c.top_voices[:5],
                    "top_posts": c.top_posts[:5],
                    "related_companies": c.related_companies[:5],
                }
                for c in clusters[:20]
            ],
        }
