"""Notification history schemas (read-only projection of notification_log)."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    subject_type: str
    subject_id: uuid.UUID
    milestone: str
    due_date: date
    title: str
    body: str
    delivery_status: str
    sent_at: datetime | None = None


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    total: int
    page: int
    page_size: int


class TestNotificationRequest(BaseModel):
    title: str = "OWNLY Test Alert"
    body: str = "This is a test notification from OWNLY."
    route: str = "/today"
    deep_link: str | None = None


class TestNotificationResponse(BaseModel):
    message: str
    recipient_count: int
    tokens: list[str]
    route: str
    deep_link: str
