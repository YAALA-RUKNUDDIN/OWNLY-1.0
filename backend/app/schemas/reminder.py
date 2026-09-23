import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    reminder_type: Literal["warranty_expiry", "return_expiry", "service_due", "custom"] = "custom"
    scheduled_date: date
    product_id: uuid.UUID | None = None
    recurrence_months: int | None = Field(default=None, ge=1, le=60)


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    scheduled_date: date | None = None
    status: Literal["upcoming", "completed", "dismissed"] | None = None


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID | None
    title: str
    description: str | None
    reminder_type: str
    scheduled_date: date
    status: str
    recurrence_months: int | None
    created_at: datetime
