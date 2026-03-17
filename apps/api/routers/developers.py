"""Developers router — API access request form."""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from apps.api.schemas.developers import ApiAccessRequest, ApiAccessResponse
from apps.api.services.email import send_api_access_notification
from apps.api.services.email_validation import validate_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/developers", tags=["developers"])


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

    email_error = validate_email(email)
    if email_error:
        raise HTTPException(status_code=400, detail=email_error)

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
