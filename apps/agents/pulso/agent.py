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

        themed_count = len([s for s in self._all_signals if s.theme])
        platform_count = len(set(s.post.platform for s in self._all_signals)) if self._all_signals else 0

        # Editorial memo — 3 paragraphs that render as the /signals?tab=memo
        # banner. Falls back to the stats line when LLM is unavailable.
        editorial_memo = self._generate_memo(clusters, themed_count, platform_count)

        body_sections: List[str] = []
        body_sections.append(
            f"# Pulso Semanal - Semana {self.week_number}\n"
        )

        if editorial_memo:
            body_sections.append(editorial_memo)
        else:
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

    def _generate_memo(
        self,
        clusters: List[SignalClusterResult],
        themed_count: int,
        platform_count: int,
    ) -> Optional[str]:
        """Generate a 3-paragraph editorial memo for the Weekly Pulse.

        The memo replaces the generic stats line as the banner content on
        /signals?tab=memo. Structure:
          1. Dominant thesis (what's converging)
          2. Sectoral contrast (what stood out vs last week / vs other sectors)
          3. What to monitor (emerging signals, not yet dominant)

        Returns None when LLM is unavailable so the caller falls back to a
        template line.
        """
        if not clusters or not self._llm_client.is_available:
            return None

        # Build cluster context (top 8 by score) with enough detail for the LLM
        top_clusters = clusters[:8]
        cluster_lines = []
        for c in top_clusters:
            platforms = ", ".join(sorted(c.platforms)) if c.platforms else "?"
            cluster_lines.append(
                f"- {c.name}: {c.signal_count} sinais, plataformas={platforms}, "
                f"stage={c.narrative_stage}, score={c.composite_score:.2f}"
            )
        context = "\n".join(cluster_lines)

        # Sample top posts for texture (3 random from top clusters)
        sample_posts: List[str] = []
        for c in top_clusters[:3]:
            if c.signals:
                top_signal = c.signals[0]
                text_snippet = (top_signal.post.text or "")[:120].replace("\n", " ")
                if text_snippet:
                    sample_posts.append(
                        f"- [{top_signal.post.platform}] {text_snippet}..."
                    )

        system = (
            "Voce e o analista de sinais sociais da plataforma Sinal.lab, especializado em "
            "identificar teses emergentes no ecossistema tech LATAM antes que virem mainstream.\n\n"
            "Seu trabalho e escrever o MEMO SEMANAL — 3 paragrafos editoriais que dao contexto "
            "aos sinais coletados em Twitter, LinkedIn, Bluesky, Reddit e YouTube. Nao e lista "
            "de clusters; e interpretacao do que os padroes revelam.\n\n"
            "Estilo editorial:\n"
            "- Tom analitico, especifico, factual\n"
            "- Portugues brasileiro (PT-BR)\n"
            "- NUNCA use em dash (U+2014). Use virgula, dois pontos ou ponto.\n"
            "- Sem 'vale ressaltar', 'neste contexto', 'e importante destacar'\n"
            "- Sem 'revolucionario', 'disruptivo', 'game-changer'\n"
            "- Pergunta-filtro: 'Um CTO pararia de trabalhar para ler isto?'"
        )

        sample_posts_block = "\n".join(sample_posts) if sample_posts else "(sem amostras)"

        prompt = (
            f"Escreva o MEMO SEMANAL do PULSO da semana {self.week_number}. "
            f"3 paragrafos, 300-450 palavras total.\n\n"
            f"Dados da semana:\n"
            f"- {themed_count} sinais classificados em {platform_count} plataformas\n"
            f"- {len(clusters)} clusters identificados\n\n"
            f"Top clusters:\n{context}\n\n"
            f"Amostras de posts:\n{sample_posts_block}\n\n"
            "Estrutura dos 3 paragrafos:\n"
            "1. TESE DOMINANTE: qual padrao conecta os clusters mais fortes. Cite 2-3 clusters "
            "concretos e o que eles revelam juntos sobre sentimento do ecossistema.\n"
            "2. CONTRASTE: onde ha divergencia entre plataformas, setores ou regioes. "
            "Cite numeros concretos.\n"
            "3. O QUE MONITORAR: sinal emergente que ainda nao e tese, mas merece atencao "
            "na proxima semana. Seja especifico.\n\n"
            "Regras:\n"
            "- NAO use titulos H1/H2 dentro dos paragrafos\n"
            "- Pode usar **bold** para destacar nomes/numeros\n"
            "- NAO inicie com 'Nesta semana', 'A semana N', 'Esta edicao'\n"
            "- Retorne APENAS os 3 paragrafos em Markdown"
        )

        result = self._llm_client.generate(
            user_prompt=prompt,
            system_prompt=system,
            max_tokens=900,
            temperature=0.5,
        )
        if result and result.strip():
            return result.strip()
        return None

    def _generate_title(self, clusters: List[SignalClusterResult]) -> str:
        """Generate an editorial title for the Weekly Pulse."""
        if not clusters or not self._llm_client.is_available:
            return f"Pulso Semanal - Semana {self.week_number}"

        # Rich context: top clusters with signal count + platforms
        cluster_lines = []
        for c in clusters[:5]:
            platforms = ", ".join(sorted(c.platforms))
            cluster_lines.append(
                f"- {c.name}: {c.signal_count} sinais em {platforms}, stage={c.narrative_stage}"
            )
        context = "\n".join(cluster_lines)

        system = (
            "Voce e o analista de sinais sociais da plataforma Sinal.lab, especializado em "
            "identificar teses emergentes no ecossistema tech LATAM antes que virem mainstream.\n\n"
            "PULSO cobre sinais sociais: o que CTOs, founders e VCs LATAM estao discutindo em "
            "Twitter, LinkedIn, Bluesky, Reddit e YouTube. A analise foca em DETECCAO PRECOCE "
            "de temas que ganham tracao, nao em recapitular noticias.\n\n"
            "Estilo:\n"
            "- Tom analitico, especifico, sem hype\n"
            "- Escreva em portugues brasileiro\n"
            "- NUNCA use em dash (use virgula, dois pontos ou ponto)\n"
            "- Evite 'revolucionario', 'disruptivo', 'game-changer'\n"
            "- Pergunta-filtro: 'Um CTO pararia de trabalhar para ler isto?'"
        )

        prompt = (
            f"Crie um titulo editorial (maximo 15 palavras, 80 chars) para o PULSO SEMANAL "
            f"da semana {self.week_number}. O PULSO analisa o que esta acelerando nas "
            f"conversas tech LATAM.\n\n"
            f"Clusters da semana:\n{context}\n\n"
            "Direcoes:\n"
            "- Angulo PULSO: tema em aceleracao, sinal emergente, tese cruzando plataformas\n"
            "- NAO comece com 'Semana N:' nem com 'Pulso Semanal'\n"
            "- Cite o tema/tese mais relevante, nao liste todos\n"
            "- Exemplos de bom angulo: 'Agentes de AI viram pauta em LATAM antes dos deals', "
            "'Open Finance Colombia domina conversas tech esta semana'\n"
            "- Retorne APENAS o titulo"
        )

        result = self._llm_client.generate(
            user_prompt=prompt,
            system_prompt=system,
            max_tokens=80,
            temperature=0.5,
        )
        if result and result.strip():
            return result.strip().strip('"').strip("'")
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
            signal_count = cluster.signal_count
            platforms = ", ".join(cluster.platforms)

            lines.append(f"### {cluster.name}")
            # Neither the composite score nor the raw dimension dump is
            # published any more. Measured over 3.000 production clusters,
            # velocity and new_entrants have 2 distinct values each,
            # cross_platform has 4, and authority is pinned near zero because
            # the active Twitter collector never populates author_followers.
            # Printing "Velocidade: 0.50" on every cluster reads as a
            # measurement of that cluster; it is the default.
            lines.append(
                f"**Sinais:** {signal_count} | "
                f"**Plataformas:** {platforms} | "
                f"**Estagio:** {cluster.narrative_stage}"
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

        LATAM filter (2026-04-21): drops posts that have zero LATAM signal
        in text/language/handle. Editorial promise is "Signal Intelligence
        LATAM" — 20VC/Stratechery/generic global threads were crowding the
        leaderboard and hiding LATAM voices.
        """
        lines = ["## Posts mais Relevantes\n"]

        all_top: List[dict] = []
        for cluster in clusters:
            all_top.extend(cluster.top_posts)

        # Filter for LATAM relevance; keep full list as fallback if filter
        # drops everything (rare but possible on thin weeks).
        latam_posts = [p for p in all_top if _is_latam_post(p)]
        pool = latam_posts if latam_posts else all_top

        def _engagement(p: dict) -> float:
            m = p.get("metrics", {})
            return (
                m.get("likes", 0)
                + m.get("replies", 0) * 2
                + m.get("reposts", 0) * 3
                + m.get("score", 0)
            )

        pool.sort(key=_engagement, reverse=True)

        for i, post in enumerate(pool[:10], 1):
            author = post.get("author", "")
            platform = post.get("platform", "")
            text = post.get("text", "")[:120]
            url = post.get("url", "")

            lines.append(
                f"{i}. **{author}** ({platform}): {text}"
                + (f" [link]({url})" if url else "")
            )

        if not pool:
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
        """Render companies mentioned across all clusters.

        Entity validation (2026-04-21): cross-references each extracted name
        against the `companies` table and `funding_rounds.company_name`. Drops:
        - Names starting with /u/ or @ (social handles, not companies)
        - Names < 3 chars or uppercase-only codes (e.g. "BN", "TRN")
        - Names that don't match any known company AND appear < 3 times
        """
        lines = ["## Startups para Monitorar\n"]

        company_total: dict = {}
        for cluster in clusters:
            for company in cluster.related_companies:
                name = company["name"]
                count = company.get("mention_count", 1)
                company_total[name] = company_total.get(name, 0) + count

        validated = self._validate_company_mentions(company_total)
        sorted_companies = sorted(
            validated.items(), key=lambda x: x[1], reverse=True,
        )

        for i, (name, count) in enumerate(sorted_companies[:15], 1):
            lines.append(f"{i}. **{name}** ({count} mencoes)")

        if not sorted_companies:
            lines.append("*Nenhuma startup validada esta semana.*")

        lines.append("")
        return "\n".join(lines)

    def _validate_company_mentions(self, mentions: dict) -> dict:
        """Filter raw entity mentions against known LATAM company database.

        An entity passes validation if EITHER:
          - slug matches a row in `companies` table, OR
          - slug matches a `funding_rounds.company_name`, OR
          - name appears >= 3 times (high-confidence organic mention)
        """
        if not mentions:
            return {}

        # Discard social handles and codes up front
        clean = {}
        for name, count in mentions.items():
            if not name or len(name) < 3:
                continue
            if name.startswith(("/u/", "@", "u/", "r/")):
                continue
            # Filter all-caps codes shorter than 5 chars (e.g. BN, TRN, FII)
            if len(name) < 5 and name == name.upper():
                continue
            clean[name] = count

        if not clean:
            return {}

        # Load known slugs/names from DB
        known_set: set = set()
        try:
            from packages.database.session import get_session
            from packages.database.models.company import Company
            from packages.database.models.funding_round import FundingRound

            session = get_session()
            try:
                for (slug,) in session.query(Company.slug).all():
                    if slug:
                        known_set.add(slug.lower())
                for (cname,) in session.query(FundingRound.company_name).distinct().all():
                    if cname:
                        known_set.add(cname.lower())
            finally:
                session.close()
        except Exception as e:
            logger.warning("Entity validation DB lookup failed: %s", e)
            # If DB unreachable, keep only high-confidence organic mentions (>=3).
            return {n: c for n, c in clean.items() if c >= 3}

        validated = {}
        for name, count in clean.items():
            norm = name.lower().strip()
            if norm in known_set or count >= 3:
                validated[name] = count
        return validated

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


# --- Module-level helpers ---

# Token set that signals LATAM relevance in text, handle, or source.
# Kept intentionally narrow to avoid over-triggering on generic Spanish.
_LATAM_HINTS = frozenset({
    "latam", "latin america", "america latina", "américa latina",
    "brasil", "brazil", "brazilian", "brasileir",
    "mexico", "méxico", "mexican",
    "argentina", "argentino", "argentine",
    "colombia", "colombian",
    "chile", "chilean",
    "peru", "perú", "peruvian",
    "uruguai", "uruguay",
    "pix", "bacen", "anbima", "b3",
    "nubank", "mercado livre", "mercadolibre", "kavak", "rappi",
    "plata", "creditas", "cloudwalk", "uala", "pomelo",
    "latitud", "contxto", "canary", "onevc", "valor capital",
    "sao paulo", "são paulo", "rio de janeiro", "bogota", "bogotá",
    "buenos aires", "santiago", "medellin", "medellín", "lima",
    "ciudad de mexico", "cdmx",
})


def _is_latam_post(post: dict) -> bool:
    """Return True when the post has any LATAM-relevance signal.

    Checked sources: text, author handle, platform source name, and
    detected language (pt/es). Intentionally conservative: a single hit
    is enough because the surrounding cluster already passed topical
    relevance filters.
    """
    haystack_parts: list[str] = []
    for key in ("text", "author", "handle", "author_handle", "source_name"):
        value = post.get(key)
        if isinstance(value, str):
            haystack_parts.append(value)
    haystack = " ".join(haystack_parts).lower()

    if not haystack.strip():
        return False

    # Quick language check: Portuguese/Spanish give strong LATAM bias
    lang = (post.get("language") or post.get("lang") or "").lower()
    if lang in {"pt", "pt-br", "pt_br", "es", "es-mx", "es-ar"}:
        return True

    # Keyword hit
    return any(hint in haystack for hint in _LATAM_HINTS)
