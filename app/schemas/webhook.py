from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class WebhookCreateRequest(BaseModel):
    url: HttpUrl
    event_types: list[str]
    secret: str | None = None

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("event_types must be a non-empty list.")

        normalized: list[str] = []
        for item in value:
            event_type = item.strip()
            if not event_type:
                raise ValueError("event_types must contain non-empty strings.")
            normalized.append(event_type)
        return normalized

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, value: str | None) -> str | None:
        if value is None:
            return None
        secret = value.strip()
        if not secret:
            raise ValueError("secret cannot be empty.")
        return secret


class WebhookUpdateRequest(BaseModel):
    url: HttpUrl | None = None
    event_types: list[str] | None = None

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("event_types must be a non-empty list.")

        normalized: list[str] = []
        for item in value:
            event_type = item.strip()
            if not event_type:
                raise ValueError("event_types must contain non-empty strings.")
            normalized.append(event_type)
        return normalized


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    url: str
    event_types: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookCreateResponse(WebhookResponse):
    secret: str
