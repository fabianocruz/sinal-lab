"""Cover image generation pipeline for Sinal editorial content.

Generates AI editorial cover images using Recraft V3, applies brand overlay
with Pillow, and uploads to Vercel Blob for use as OG images.

Usage (briefing):
    from apps.agents.covers.pipeline import CoverPipeline
    from apps.agents.covers.prompt_generator import CoverBriefing

    pipeline = CoverPipeline()
    result = pipeline.run(CoverBriefing(
        headline="Nubank testa agentes de AI",
        lede="O maior banco digital da LATAM...",
        agent="radar",
        edition=30,
    ))

Usage (article):
    from apps.agents.covers.prompt_generator import ArticleBriefing

    result = pipeline.run_article(ArticleBriefing(
        title="6 PRs para colocar um site no ar",
        thesis="A jornada de construir infra do zero",
        article_type="diary",
        author="Fabiano Cruz",
    ))
"""
