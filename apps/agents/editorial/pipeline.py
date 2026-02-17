"""Editorial pipeline orchestrator for Sinal.lab.

Runs AgentOutput through 6 sequential editorial layers:
    1. PESQUISA — provenance validation
    2. VALIDACAO — data quality cross-referencing
    3. VERIFICACAO — structural fact-checking
    4. VIES — bias detection (Batch 2)
    5. SEO — search optimization (Batch 2)
    6. SINTESE_FINAL — editorial assembly (Batch 2)

Halts on blocker flags. Returns EditorialResult with accumulated
layer results and a publish_ready determination.
"""

import logging
from typing import Any, Callable, Optional

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.layers.pesquisa import run_pesquisa
from apps.agents.editorial.layers.seo import run_seo
from apps.agents.editorial.layers.sintese_final import run_sintese_final
from apps.agents.editorial.layers.validacao import run_validacao
from apps.agents.editorial.layers.verificacao import run_verificacao
from apps.agents.editorial.layers.vies import run_vies
from apps.agents.editorial.models import (
    EditorialResult,
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)

# Type alias for layer functions
LayerFn = Callable[[AgentOutput], LayerResult]


class EditorialPipeline:
    """Orchestrates the 6-layer editorial governance pipeline.

    Usage:
        pipeline = EditorialPipeline()
        result = pipeline.review(agent_output)
        if result.publish_ready:
            # safe to publish
        else:
            # route to human review queue
    """

    def __init__(self, halt_on_blocker: bool = True) -> None:
        """Initialize the pipeline.

        Args:
            halt_on_blocker: If True, stop processing when a layer
                produces a blocker flag. If False, run all layers
                regardless (useful for full diagnostic reports).
        """
        self.halt_on_blocker = halt_on_blocker
        self._layers: list[tuple[str, LayerFn]] = self._build_layer_chain()

    def _build_layer_chain(self) -> list[tuple[str, LayerFn]]:
        """Assemble the ordered list of 6 editorial layers.

        Layer 6 (SINTESE_FINAL) is handled specially in review()
        because it needs access to all prior layer results.
        """
        layers: list[tuple[str, LayerFn]] = [
            ("pesquisa", run_pesquisa),
            ("validacao", run_validacao),
            ("verificacao", run_verificacao),
            ("vies", run_vies),
            ("seo", run_seo),
            # sintese_final is invoked directly in review() with prior_layer_results
        ]
        return layers

    def register_layer(self, name: str, layer_fn: LayerFn) -> None:
        """Register an additional layer at the end of the chain.

        Used by Batch 2 to plug in layers 4-6 without modifying
        existing code.
        """
        self._layers.append((name, layer_fn))

    def review(self, agent_output: AgentOutput) -> EditorialResult:
        """Run the agent output through all editorial layers.

        Args:
            agent_output: The AgentOutput to review.

        Returns:
            EditorialResult with all layer results, flags,
            and publish_ready determination.
        """
        layer_results: list[LayerResult] = []
        all_flags: list[ReviewFlag] = []
        halted_at: Optional[str] = None

        logger.info(
            "Starting editorial review for '%s' (agent=%s, run=%s)",
            agent_output.title,
            agent_output.agent_name,
            agent_output.run_id,
        )

        # Warn when a data agent output enters the editorial pipeline.
        # Data agents (FUNDING, MERCADO, INDEX) produce raw data reports
        # that typically bypass editorial review. This is not a blocker,
        # just an alert for the editorial team.
        agent_category = getattr(agent_output, "agent_category", "content")
        if agent_category == "data":
            logger.warning(
                "Data agent '%s' output entering editorial pipeline — "
                "data agents normally bypass editorial review.",
                agent_output.agent_name,
            )
            all_flags.append(ReviewFlag(
                severity=FlagSeverity.WARNING,
                category=FlagCategory.DATA_QUALITY,
                message=(
                    f"Data agent '{agent_output.agent_name}' output entering editorial "
                    f"pipeline. Data agents normally bypass editorial review."
                ),
                layer="pipeline",
            ))

        for layer_name, layer_fn in self._layers:
            logger.info("Running editorial layer: %s", layer_name)

            try:
                result = layer_fn(agent_output)
            except Exception as e:
                logger.error("Layer %s raised exception: %s", layer_name, e)
                result = LayerResult(
                    layer_name=layer_name,
                    passed=False,
                    grade="D",
                    flags=[ReviewFlag(
                        severity=FlagSeverity.BLOCKER,
                        category=FlagCategory.EDITORIAL,
                        message=f"Layer {layer_name} failed with exception: {e}",
                        layer=layer_name,
                    )],
                )

            layer_results.append(result)
            all_flags.extend(result.flags)

            if self.halt_on_blocker and result.has_blockers:
                logger.warning(
                    "Pipeline halted at layer '%s' due to blocker flag(s)",
                    layer_name,
                )
                halted_at = layer_name
                break

        # --- Layer 6: SINTESE_FINAL (always runs unless halted) ---
        seo_metadata: dict = {}
        byline: Optional[str] = None

        if halted_at is None:
            logger.info("Running editorial layer: sintese_final")
            try:
                final_result = run_sintese_final(agent_output, prior_layer_results=layer_results)
            except Exception as e:
                logger.error("Layer sintese_final raised exception: %s", e)
                final_result = LayerResult(
                    layer_name="sintese_final",
                    passed=False,
                    grade="D",
                    flags=[ReviewFlag(
                        severity=FlagSeverity.BLOCKER,
                        category=FlagCategory.EDITORIAL,
                        message=f"Layer sintese_final failed with exception: {e}",
                        layer="sintese_final",
                    )],
                )

            layer_results.append(final_result)
            all_flags.extend(final_result.flags)
            byline = final_result.modifications.get("byline")
            seo_metadata = final_result.modifications.get("jsonld", {})

        # Determine publish readiness
        has_any_blocker = any(f.severity == FlagSeverity.BLOCKER for f in all_flags)
        publish_ready = not has_any_blocker

        editorial_result = EditorialResult(
            content_title=agent_output.title,
            agent_name=agent_output.agent_name,
            run_id=agent_output.run_id,
            publish_ready=publish_ready,
            layer_results=layer_results,
            all_flags=all_flags,
            seo_metadata=seo_metadata,
            byline=byline,
        )

        logger.info(
            "Editorial review complete: publish_ready=%s, grade=%s, "
            "layers_run=%d/%d, total_flags=%d%s",
            publish_ready,
            editorial_result.overall_grade,
            len(layer_results),
            len(self._layers),
            len(all_flags),
            f", halted_at={halted_at}" if halted_at else "",
        )

        return editorial_result

    def get_layer_names(self) -> list[str]:
        """Return ordered list of all layer names (including sintese_final)."""
        names = [name for name, _ in self._layers]
        names.append("sintese_final")
        return names
