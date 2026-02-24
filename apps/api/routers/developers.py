"""Developers router — API access request form."""

import logging
import re

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from apps.api.schemas.developers import ApiAccessRequest, ApiAccessResponse
from apps.api.services.email import send_api_access_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/developers", tags=["developers"])

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@router.post(
    "/request-access",
    response_model=ApiAccessResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_api_access(
    body: ApiAccessRequest,
    background_tasks: BackgroundTasks,
):
    """Submit an API access request.

    Sends a notification email to contact@sinal.tech with the request details.
    No authentication required — this is a public lead-gen form.
    """
    email = body.email.strip().lower()

    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Email inválido.")

    background_tasks.add_task(
        send_api_access_notification,
        name=body.name,
        email=email,
        company=body.company,
        role=body.role,
        use_case=body.use_case,
    )

    logger.info(
        "API access request from %s (%s) at %s",
        body.name,
        email,
        body.company,
    )

    return ApiAccessResponse(
        message="Solicitação enviada! Entraremos em contato em breve."
    )
