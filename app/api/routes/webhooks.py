import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.repositories.webhook_repository import (
    create_webhook,
    delete_webhook,
    get_webhook_by_id_for_user,
    list_webhooks_by_user,
    update_webhook,
)
from app.db.session import get_session
from app.models.user import User
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookResponse,
    WebhookUpdateRequest,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_route(
    payload: WebhookCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> WebhookCreateResponse:
    secret = payload.secret or secrets.token_urlsafe(32)
    webhook = await create_webhook(
        session=session,
        webhook_id=str(uuid.uuid4()),
        user_id=current_user.id,
        url=str(payload.url),
        event_types=payload.event_types,
        secret=secret,
    )
    return WebhookCreateResponse.model_validate(webhook)


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks_route(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[WebhookResponse]:
    webhooks = await list_webhooks_by_user(session=session, user_id=current_user.id)
    return [WebhookResponse.model_validate(webhook) for webhook in webhooks]


@router.get("/{id}", response_model=WebhookResponse)
async def get_webhook_route(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> WebhookResponse:
    webhook = await get_webhook_by_id_for_user(
        session=session,
        webhook_id=str(id),
        user_id=current_user.id,
    )
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")
    return WebhookResponse.model_validate(webhook)


@router.patch("/{id}", response_model=WebhookResponse)
async def update_webhook_route(
    id: uuid.UUID,
    payload: WebhookUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> WebhookResponse:
    webhook = await get_webhook_by_id_for_user(
        session=session,
        webhook_id=str(id),
        user_id=current_user.id,
    )
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")

    updated = await update_webhook(
        session=session,
        webhook=webhook,
        url=str(payload.url) if payload.url is not None else None,
        event_types=payload.event_types,
    )
    return WebhookResponse.model_validate(updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_route(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    webhook = await get_webhook_by_id_for_user(
        session=session,
        webhook_id=str(id),
        user_id=current_user.id,
    )
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")

    await delete_webhook(session=session, webhook=webhook)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
