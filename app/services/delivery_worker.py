import asyncio
import logging
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session
from app.models.delivery import Delivery, DeliveryStatus
from app.models.delivery_attempt import DeliveryAttempt
from app.models.webhook import Webhook

logger = logging.getLogger("delivery_worker")


@dataclass
class AttemptResult:
    succeeded: bool
    http_status: int | None
    response_body: str | None


async def run_worker_loop() -> None:
    timeout = httpx.Timeout(settings.WORKER_HTTP_TIMEOUT_SECONDS)
    success_statuses = set(settings.WORKER_SUCCESS_STATUS_CODE_LIST)

    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            try:
                while True:
                    processed = await process_one_pending_delivery(
                        client=client,
                        success_statuses=success_statuses,
                        max_attempts=settings.WORKER_MAX_DELIVERY_ATTEMPTS,
                        min_backoff=settings.WORKER_MIN_BACKOFF_SECONDS,
                        max_backoff=settings.WORKER_MAX_BACKOFF_SECONDS,
                    )
                    if not processed:
                        break
            except Exception:
                # Keep polling even if a cycle fails unexpectedly.
                logger.exception("Worker cycle failed")

            await asyncio.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)


async def process_one_pending_delivery(
    *,
    client: httpx.AsyncClient,
    success_statuses: set[int],
    max_attempts: int,
    min_backoff: float,
    max_backoff: float,
) -> bool:
    async with async_session() as session:
        async with session.begin():
            delivery, webhook_url = await _lock_next_delivery(session=session)
            if delivery is None or webhook_url is None:
                return False

            attempt_number = await _next_attempt_number(session=session, delivery_id=delivery.id)
            attempt_result = await _perform_http_attempt(
                client=client,
                webhook_url=webhook_url,
                payload=delivery.payload,
                success_statuses=success_statuses,
            )

            session.add(
                DeliveryAttempt(
                    id=str(uuid.uuid4()),
                    delivery_id=delivery.id,
                    attempt_number=attempt_number,
                    http_status=attempt_result.http_status,
                    response_body=_truncate_response(attempt_result.response_body),
                    attempted_at=datetime.now(UTC),
                    succeeded=attempt_result.succeeded,
                )
            )

            if attempt_result.succeeded:
                delivery.status = DeliveryStatus.SUCCESS
                delivery.next_attempt_at = None
                return True

            if attempt_number >= max_attempts:
                delivery.status = DeliveryStatus.PERMANENTLY_FAILED
                delivery.next_attempt_at = None
                return True

            delay_seconds = _compute_backoff_seconds(
                attempt_number=attempt_number,
                min_backoff=min_backoff,
                max_backoff=max_backoff,
            )
            delivery.status = DeliveryStatus.PENDING
            delivery.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
            return True


async def _lock_next_delivery(session: AsyncSession) -> tuple[Delivery | None, str | None]:
    statement: Select[tuple[Delivery, str]] = (
        select(Delivery, Webhook.url)
        .join(Webhook, Webhook.id == Delivery.webhook_id)
        .where(
            Delivery.status == DeliveryStatus.PENDING,
            or_(Delivery.next_attempt_at.is_(None), Delivery.next_attempt_at <= func.now()),
        )
        .order_by(Delivery.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(statement)
    row = result.first()
    if row is None:
        return None, None
    return row[0], row[1]


async def _next_attempt_number(session: AsyncSession, delivery_id: str) -> int:
    statement = select(func.count(DeliveryAttempt.id)).where(DeliveryAttempt.delivery_id == delivery_id)
    result = await session.execute(statement)
    attempts_count = int(result.scalar_one())
    return attempts_count + 1


async def _perform_http_attempt(
    *,
    client: httpx.AsyncClient,
    webhook_url: str,
    payload: dict[str, Any],
    success_statuses: set[int],
) -> AttemptResult:
    try:
        response = await client.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        body = response.text if response.text else None
        return AttemptResult(
            succeeded=response.status_code in success_statuses,
            http_status=response.status_code,
            response_body=body,
        )
    except httpx.HTTPError as exc:
        logger.warning("Delivery attempt HTTP error for url=%s: %s", webhook_url, str(exc))
        return AttemptResult(
            succeeded=False,
            http_status=None,
            response_body=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected delivery attempt error for url=%s", webhook_url)
        return AttemptResult(
            succeeded=False,
            http_status=None,
            response_body=str(exc),
        )


def _truncate_response(response_body: str | None) -> str | None:
    if response_body is None:
        return None
    return response_body[:500]


def _compute_backoff_seconds(*, attempt_number: int, min_backoff: float, max_backoff: float) -> float:
    bounded_min = max(min_backoff, 0)
    bounded_max = max(max_backoff, bounded_min)
    base = min(bounded_min * (2**attempt_number), bounded_max)
    jitter = random.uniform(0, min(1.0, bounded_max * 0.1))
    return base + jitter
