"""Cover image generation router — admin-only endpoint.

Generates AI editorial cover images using Recraft V3 with brand overlay,
uploaded to Vercel Blob. Synchronous endpoint (~20-50s per request).
"""

from fastapi import APIRouter, Depends, HTTPException

from apps.api.deps import get_admin_user
from apps.api.schemas.covers import (
    CoverGenerateRequest,
    CoverGenerateResponse,
    CoverImageResponse,
)
from apps.agents.covers.pipeline import CoverPipeline
from apps.agents.covers.prompt_generator import CoverBriefing
from packages.database.models.user import User

router = APIRouter(prefix="/covers", tags=["covers"])


@router.post("/generate", response_model=CoverGenerateResponse)
def generate_cover(
    body: CoverGenerateRequest,
    _admin: User = Depends(get_admin_user),
):
    """Generate AI cover images for editorial content.

    Admin-only. Synchronous — takes ~20-50s per request.
    Generates up to 3 variations with brand overlay, uploaded to Vercel Blob.
    """
    pipeline = CoverPipeline()

    briefing = CoverBriefing(
        headline=body.headline,
        lede=body.lede,
        agent=body.agent,
        edition=body.edition,
        dq_score=body.dq_score,
    )

    result = pipeline.run(briefing, variations=body.variations)

    if not result.images:
        raise HTTPException(
            status_code=502,
            detail=f"Cover generation failed: {'; '.join(result.errors)}",
        )

    return CoverGenerateResponse(
        images=[
            CoverImageResponse(url=img["url"], variation=img["variation"])
            for img in result.images
        ],
        prompt_used=result.prompt_used,
        agent=result.agent,
        errors=result.errors,
    )
