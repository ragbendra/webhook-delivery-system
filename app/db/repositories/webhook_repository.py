from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook


async def create_webhook(
    session: AsyncSession,
    webhook_id: str,
    user_id: str,
    url: str,
    event_types: list[str],
    secret: str,
) -> Webhook:
    webhook = Webhook(
        id=webhook_id,
        user_id=user_id,
        url=url,
        event_types=event_types,
        secret=secret,
    )
    session.add(webhook)
    await session.commit()
    await session.refresh(webhook)
    return webhook


async def list_webhooks_by_user(session: AsyncSession, user_id: str) -> list[Webhook]:
    statement: Select[tuple[Webhook]] = (
        select(Webhook).where(Webhook.user_id == user_id).order_by(Webhook.created_at.desc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_webhook_by_id_for_user(
    session: AsyncSession, webhook_id: str, user_id: str
) -> Webhook | None:
    statement: Select[tuple[Webhook]] = select(Webhook).where(
        Webhook.id == webhook_id,
        Webhook.user_id == user_id,
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def update_webhook(
    session: AsyncSession,
    webhook: Webhook,
    *,
    url: str | None = None,
    event_types: list[str] | None = None,
) -> Webhook:
    if url is not None:
        webhook.url = url
    if event_types is not None:
        webhook.event_types = event_types

    await session.commit()
    await session.refresh(webhook)
    return webhook


async def delete_webhook(session: AsyncSession, webhook: Webhook) -> None:
    await session.delete(webhook)
    await session.commit()
