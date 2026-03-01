from typing import Any

from pydantic import BaseModel, field_validator


class EventIngestRequest(BaseModel):
    event_type: str
    payload: dict[str, Any]

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        event_type = value.strip()
        if not event_type:
            raise ValueError("event_type must be a non-empty string.")
        return event_type


class EventIngestResponse(BaseModel):
    queued_count: int
    delivery_ids: list[str]
