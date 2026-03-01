from datetime import datetime

from pydantic import BaseModel


class DeliveryAttemptListItemResponse(BaseModel):
    attempt_number: int
    http_status: int | None
    succeeded: bool
    attempted_at: datetime


class DeliveryAttemptDetailResponse(DeliveryAttemptListItemResponse):
    response_body: str | None


class DeliveryListItemResponse(BaseModel):
    id: str
    event_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    attempts: list[DeliveryAttemptListItemResponse]


class DeliveryHistoryResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    total_pages: int
    results: list[DeliveryListItemResponse]


class DeliveryDetailResponse(BaseModel):
    id: str
    webhook_id: str
    event_type: str
    status: str
    payload: dict
    created_at: datetime
    updated_at: datetime
    attempts: list[DeliveryAttemptDetailResponse]
