from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import Delivery
from app.models.delivery_attempt import DeliveryAttempt


async def get_delivery_count_for_webhook(session: AsyncSession, webhook_id: str) -> int:
    statement = select(func.count(Delivery.id)).where(Delivery.webhook_id == webhook_id)
    result = await session.execute(statement)
    return int(result.scalar_one())


async def list_deliveries_for_webhook(
    session: AsyncSession,
    webhook_id: str,
    *,
    offset: int,
    limit: int,
) -> list[Delivery]:
    statement: Select[tuple[Delivery]] = (
        select(Delivery)
        .where(Delivery.webhook_id == webhook_id)
        .order_by(Delivery.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def list_attempts_for_delivery_ids(
    session: AsyncSession, delivery_ids: list[str]
) -> list[DeliveryAttempt]:
    if not delivery_ids:
        return []

    statement: Select[tuple[DeliveryAttempt]] = (
        select(DeliveryAttempt)
        .where(DeliveryAttempt.delivery_id.in_(delivery_ids))
        .order_by(DeliveryAttempt.delivery_id.asc(), DeliveryAttempt.attempt_number.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_delivery_for_webhook(
    session: AsyncSession, webhook_id: str, delivery_id: str
) -> Delivery | None:
    statement: Select[tuple[Delivery]] = select(Delivery).where(
        Delivery.id == delivery_id,
        Delivery.webhook_id == webhook_id,
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def list_attempts_for_delivery(session: AsyncSession, delivery_id: str) -> list[DeliveryAttempt]:
    statement: Select[tuple[DeliveryAttempt]] = (
        select(DeliveryAttempt)
        .where(DeliveryAttempt.delivery_id == delivery_id)
        .order_by(DeliveryAttempt.attempt_number.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
