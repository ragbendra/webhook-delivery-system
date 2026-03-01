from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.delivery_repository import create_pending_deliveries_for_event
from app.db.session import get_session
from app.schemas.event import EventIngestRequest, EventIngestResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    payload: EventIngestRequest,
    session: AsyncSession = Depends(get_session),
) -> EventIngestResponse:
    deliveries = await create_pending_deliveries_for_event(
        session=session,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    delivery_ids = [delivery.id for delivery in deliveries]
    return EventIngestResponse(queued_count=len(delivery_ids), delivery_ids=delivery_ids)
