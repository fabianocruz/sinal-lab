"""Cover image generation pipeline for Sinal editorial content.

Generates AI editorial cover images using Recraft V3, applies brand overlay
with Pillow, and uploads to Vercel Blob for use as OG images.

Usage:
    from apps.agents.covers.pipeline import CoverPipeline
    from apps.agents.covers.prompt_generator import CoverBriefing

    pipeline = CoverPipeline()
    result = pipeline.run(CoverBriefing(
        headline="Nubank testa agentes de AI",
        lede="O maior banco digital da LATAM...",
        agent="radar",
        edition=30,
    ))
    for img in result.images:
        print(img["url"])
"""
