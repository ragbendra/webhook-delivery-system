import json
import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import Delivery, DeliveryStatus
from app.models.webhook import Webhook


async def create_pending_deliveries_for_event(
    session: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, Any],
) -> list[Delivery]:
    statement: Select[tuple[str]] = select(Webhook.id).where(
        Webhook.is_active.is_(True),
        func.json_contains(Webhook.event_types, json.dumps([event_type])) == 1,
    )
    result = await session.execute(statement)
    webhook_ids = list(result.scalars().all())

    if not webhook_ids:
        return []

    deliveries = [
        Delivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            status=DeliveryStatus.PENDING,
        )
        for webhook_id in webhook_ids
    ]
    session.add_all(deliveries)
    await session.commit()
    return deliveries
