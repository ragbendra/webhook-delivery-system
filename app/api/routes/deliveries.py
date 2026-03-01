import math
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.repositories.delivery_history_repository import (
    get_delivery_count_for_webhook,
    get_delivery_for_webhook,
    list_attempts_for_delivery,
    list_attempts_for_delivery_ids,
    list_deliveries_for_webhook,
)
from app.db.repositories.webhook_repository import get_webhook_by_id_for_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.delivery import (
    DeliveryAttemptDetailResponse,
    DeliveryAttemptListItemResponse,
    DeliveryDetailResponse,
    DeliveryHistoryResponse,
    DeliveryListItemResponse,
)

router = APIRouter(prefix="/webhooks/{id}/deliveries", tags=["deliveries"])


@router.get("", response_model=DeliveryHistoryResponse)
async def list_delivery_history(
    id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DeliveryHistoryResponse:
    webhook = await get_webhook_by_id_for_user(
        session=session,
        webhook_id=str(id),
        user_id=current_user.id,
    )
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")

    total_count = await get_delivery_count_for_webhook(session=session, webhook_id=webhook.id)
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
    offset = (page - 1) * page_size

    deliveries = await list_deliveries_for_webhook(
        session=session,
        webhook_id=webhook.id,
        offset=offset,
        limit=page_size,
    )
    delivery_ids = [delivery.id for delivery in deliveries]
    attempts = await list_attempts_for_delivery_ids(session=session, delivery_ids=delivery_ids)

    attempts_by_delivery: dict[str, list[DeliveryAttemptListItemResponse]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_delivery[attempt.delivery_id].append(
            DeliveryAttemptListItemResponse(
                attempt_number=attempt.attempt_number,
                http_status=attempt.http_status,
                succeeded=attempt.succeeded,
                attempted_at=attempt.attempted_at,
            )
        )

    results = [
        DeliveryListItemResponse(
            id=delivery.id,
            event_type=delivery.event_type,
            status=delivery.status.value,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
            attempts=attempts_by_delivery.get(delivery.id, []),
        )
        for delivery in deliveries
    ]

    return DeliveryHistoryResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=results,
    )


@router.get("/{delivery_id}", response_model=DeliveryDetailResponse)
async def get_delivery_detail(
    id: uuid.UUID,
    delivery_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DeliveryDetailResponse:
    webhook = await get_webhook_by_id_for_user(
        session=session,
        webhook_id=str(id),
        user_id=current_user.id,
    )
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")

    delivery = await get_delivery_for_webhook(
        session=session,
        webhook_id=webhook.id,
        delivery_id=str(delivery_id),
    )
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found.")

    attempts = await list_attempts_for_delivery(session=session, delivery_id=delivery.id)
    attempt_items = [
        DeliveryAttemptDetailResponse(
            attempt_number=attempt.attempt_number,
            http_status=attempt.http_status,
            succeeded=attempt.succeeded,
            attempted_at=attempt.attempted_at,
            response_body=attempt.response_body,
        )
        for attempt in attempts
    ]

    return DeliveryDetailResponse(
        id=delivery.id,
        webhook_id=delivery.webhook_id,
        event_type=delivery.event_type,
        status=delivery.status.value,
        payload=delivery.payload,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
        attempts=attempt_items,
    )
