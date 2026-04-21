"""VozesAgent — social media collection, classification, and authority scoring.

Lifecycle:
    collect() -> fetch from all configured sources via collector
    process() -> classify, filter (LATAM, spam, authority), extract entities
    score()   -> compute aggregate confidence scores
    output()  -> write ProcessedSignals summary as AgentOutput
"""

from __future__ import annotations

import json
import logging
from typing import Any, List

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.output import AgentOutput, format_markdown_output
from apps.agents.social_signals.models import ProcessedSignal, SocialPost
from apps.agents.vozes.authority import (
    compute_authority_score,
    extract_top_voices,
    filter_low_authority,
)
from apps.agents.vozes.classifier import classify_posts_batch
from apps.agents.vozes.collector import collect_all
from apps.agents.vozes.config import VOZES_CONFIG

logger = logging.getLogger(__name__)


class VozesAgent(BaseAgent):
    """Social media voice monitoring, classification, and authority scoring.

    Collects posts from Twitter/X, Reddit, Bluesky, RSS, YouTube, and web.
    Classifies each post by theme/sub-theme, extracts entities, computes
    authority scores, detects sentiment, and filters spam/self-promo/off-topic.

    Outputs classified ProcessedSignals for PULSO to cluster and score.
    """

    agent_name: str = "vozes"
    agent_category: str = "data"
    version: str = "0.1.0"

    def __init__(self, week_number: int = 0) -> None:
        super().__init__()
        self.week_number = week_number
        self._all_signals: List[ProcessedSignal] = []
        self._top_voices: List[dict] = []

    def collect(self) -> List[SocialPost]:
        """Fetch posts from all configured sources.

        Returns:
            List of raw SocialPost items, deduplicated and filtered.
        """
        sources = VOZES_CONFIG.get_enabled_sources()
        logger.info(
            "Collecting from %d enabled sources (max %d items)",
            len(sources),
            VOZES_CONFIG.max_items_per_run,
        )

        posts = collect_all(
            sources=sources,
            provenance=self.provenance,
            agent_name=self.agent_name,
            run_id=self.run_id,
        )

        # Cap at max_items_per_run
        if len(posts) > VOZES_CONFIG.max_items_per_run:
            logger.info(
                "Capping collected posts: %d -> %d",
                len(posts),
                VOZES_CONFIG.max_items_per_run,
            )
            posts = posts[:VOZES_CONFIG.max_items_per_run]

        return posts

    def process(self, raw_data: List[Any]) -> List[Any]:
        """Classify posts, filter by LATAM relevance, compute authority.

        Args:
            raw_data: List of SocialPost from collect().

        Returns:
            List of ProcessedSignal with classifications and authority scores.
        """
        posts: List[SocialPost] = raw_data

        # Try to get LLM client for enrichment
        llm_client = None
        try:
            from apps.agents.base.llm import LLMClient
            llm_client = LLMClient()
            if not llm_client.is_available:
                llm_client = None
        except Exception:
            pass

        # Classify all posts (keyword-first, LLM for top N)
        signals = classify_posts_batch(
            posts,
            llm_client=llm_client,
            top_n_for_llm=20,
            apply_latam_filter=True,
        )

        # Override authority scores with our enhanced computation
        for signal in signals:
            signal.authority_score = compute_authority_score(signal.post)

        # Filter low-authority signals
        signals = filter_low_authority(signals)

        # Extract top voices for output
        self._top_voices = extract_top_voices(signals, limit=10)

        # Store for persistence
        self._all_signals = signals

        return signals

    def score(self, processed_data: List[Any]) -> List[ConfidenceScore]:
        """Compute aggregate confidence scores for the run.

        Args:
            processed_data: List of ProcessedSignal from process().

        Returns:
            Single-element list with aggregate ConfidenceScore.
        """
        signals: List[ProcessedSignal] = processed_data

        if not signals:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

        # Source diversity
        platforms = set(s.post.platform for s in signals)
        source_names = set(s.post.source_name for s in signals if s.post.source_name)

        # Themed ratio (higher = better classification)
        themed = sum(1 for s in signals if s.theme)
        theme_ratio = themed / len(signals) if signals else 0

        confidence = compute_confidence(
            source_count=len(source_names),
            sources_verified=0,
            data_freshness_days=0,
            cross_validated=len(platforms) >= 3,
        )

        # Adjust analysis confidence by classification quality
        adjusted_ac = confidence.analysis_confidence * (0.5 + 0.5 * theme_ratio)

        return [ConfidenceScore(
            data_quality=confidence.data_quality,
            analysis_confidence=round(adjusted_ac, 3),
            source_count=len(source_names),
            verified=confidence.verified,
            notes=f"{len(signals)} signals, {len(platforms)} platforms, {themed} themed",
        )]

    def output(
        self,
        processed_data: List[Any],
        scores: List[ConfidenceScore],
    ) -> AgentOutput:
        """Format results as AgentOutput with summary statistics.

        Args:
            processed_data: List of ProcessedSignal from process().
            scores: Confidence scores from score().

        Returns:
            AgentOutput with Markdown body summarizing the collection run.
        """
        signals: List[ProcessedSignal] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.1, analysis_confidence=0.1,
        )

        # Build summary statistics
        platforms = {}
        themes = {}
        for s in signals:
            platforms[s.post.platform] = platforms.get(s.post.platform, 0) + 1
            if s.theme:
                themes[s.theme] = themes.get(s.theme, 0) + 1

        # Build Markdown sections
        sections = []

        # Summary
        sections.append({
            "heading": "Collection Summary",
            "content": (
                f"Collected and classified **{len(signals)} signals** "
                f"from **{len(platforms)} platforms** across "
                f"**{len(themes)} themes**.\n\n"
                f"Week: {self.week_number} | "
                f"Confidence: {confidence.grade} "
                f"(DQ: {confidence.data_quality:.2f}, AC: {confidence.analysis_confidence:.2f})"
            ),
        })

        # Platform breakdown
        platform_lines = "\n".join(
            f"- **{p}**: {c} signals"
            for p, c in sorted(platforms.items(), key=lambda x: x[1], reverse=True)
        )
        sections.append({
            "heading": "Platform Breakdown",
            "content": platform_lines,
        })

        # Theme breakdown
        theme_lines = "\n".join(
            f"- **{t}**: {c} signals"
            for t, c in sorted(themes.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        sections.append({
            "heading": "Top Themes",
            "content": theme_lines,
        })

        # Top voices
        if self._top_voices:
            voice_lines = "\n".join(
                f"- **{v['name'] or v['handle']}** ({v['platform']}) "
                f"authority: {v['authority']:.2f}, {v['signal_count']} signals"
                for v in self._top_voices[:5]
            )
            sections.append({
                "heading": "Top Voices",
                "content": voice_lines,
            })

        editorial_title = self._generate_title(
            themes=themes,
            platforms=platforms,
            signal_count=len(signals),
        )

        return format_markdown_output(
            title=editorial_title,
            sections=sections,
            agent_name=self.agent_name,
            run_id=self.run_id,
            confidence=confidence,
            sources=self.provenance.get_sources(),
            content_type="DATA_REPORT",
            agent_category="data",
            summary=(
                f"{len(signals)} sinais sociais de {len(platforms)} plataformas "
                f"classificados em {len(themes)} temas."
            ),
        )

    def _generate_title(
        self,
        themes: dict,
        platforms: dict,
        signal_count: int,
    ) -> str:
        """Generate an editorial title for the VOZES collection report."""
        default = f"VOZES Collection Report - Week {self.week_number}"
        if not themes:
            return default

        try:
            from apps.agents.base.llm import LLMClient
            client = LLMClient()
        except Exception:
            return default
        if not client.is_available:
            return default

        top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]
        top_platforms = sorted(platforms.items(), key=lambda x: x[1], reverse=True)[:3]
        context_themes = ", ".join(f"{t} ({c})" for t, c in top_themes)
        context_platforms = ", ".join(f"{p} ({c})" for p, c in top_platforms)

        system = (
            "Voce e o analista de vozes do ecossistema tech LATAM na plataforma Sinal.lab. "
            "VOZES rastreia quem esta falando o que nas redes sociais: fundadores, CTOs, VCs, "
            "engenheiros seniores. O output detecta figuras-chave e temas quentes antes que "
            "virem noticia tradicional.\n\n"
            "Estilo:\n"
            "- Tom analitico, factual, sem hype\n"
            "- Portugues brasileiro\n"
            "- NUNCA use em dash\n"
            "- Foque em PADRAO, nao em volume"
        )
        prompt = (
            f"Crie um titulo editorial (maximo 15 palavras) para o relatorio de coleta social "
            f"VOZES da semana {self.week_number}.\n\n"
            f"Dados:\n"
            f"- {signal_count} sinais sociais coletados\n"
            f"- Temas dominantes: {context_themes}\n"
            f"- Plataformas: {context_platforms}\n\n"
            "Direcoes:\n"
            "- Angulo VOZES: quem/o que esta falando mais, onde converge o foco\n"
            "- NAO comece com 'VOZES' nem 'Week N'\n"
            "- Cite tema dominante OU plataforma dominante com contexto\n"
            "- Retorne APENAS o titulo"
        )
        result = client.generate(
            user_prompt=prompt, system_prompt=system, max_tokens=80, temperature=0.5,
        )
        if result and result.strip():
            return result.strip().strip('"').strip("'")
        return default

    def export_signals_json(self, path: str) -> int:
        """Export classified signals as JSON for PULSO to consume.

        Args:
            path: File path to write JSON output.

        Returns:
            Number of signals exported.
        """
        signals_data = []
        for s in self._all_signals:
            item = {
                "text": s.post.text,
                "url": s.post.url,
                "platform": s.post.platform,
                "author_handle": s.post.author_handle,
                "author_display_name": s.post.author_display_name,
                "author_followers": s.post.author_followers,
                "source_name": s.post.source_name,
                "metrics": s.post.metrics or {},
                "content_hash": s.post.content_hash,
                "theme": s.theme,
                "sub_theme": s.sub_theme,
                "sentiment": s.sentiment,
                "authority_score": s.authority_score,
                "is_commercial": s.is_commercial,
            }
            if hasattr(s, "entities") and s.entities:
                item["entities"] = [
                    {"name": e.name, "entity_type": e.entity_type, "confidence": e.confidence}
                    for e in s.entities
                ]
            signals_data.append(item)

        output = {
            "agent": self.agent_name,
            "run_id": self.run_id,
            "week_number": self.week_number,
            "signal_count": len(signals_data),
            "signals": signals_data,
        }

        import json
        from pathlib import Path

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info("Exported %d signals to %s", len(signals_data), path)
        return len(signals_data)
