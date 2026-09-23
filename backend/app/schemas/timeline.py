import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    title: str
    description: str | None
    event_date: date
    metadata_json: dict | None
    created_at: datetime


class TimelineResponse(BaseModel):
    product_id: uuid.UUID
    events: list[TimelineEventOut]