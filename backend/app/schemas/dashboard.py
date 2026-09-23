import uuid
from datetime import date, datetime

from pydantic import BaseModel


class AttentionItem(BaseModel):
    kind: str                 # warranty_expiring | warranty_expired | return_expiring | service_due | reminder_due
    severity: str             # critical | warning | info
    product_id: uuid.UUID | None   # None for user-level reminders without a product
    product_name: str | None
    title: str
    message: str
    due_date: date
    days_remaining: int


class UpcomingItem(BaseModel):
    kind: str
    product_id: uuid.UUID | None
    product_name: str | None
    title: str
    due_date: date
    days_remaining: int


class RecentlyAddedItem(BaseModel):
    product_id: uuid.UUID
    name: str
    brand: str | None
    category: str
    image_url: str | None
    created_at: datetime


class DashboardStats(BaseModel):
    total_products: int
    active_warranties: int
    expiring_warranties: int
    documents_stored: int


class TodayDashboard(BaseModel):
    greeting: str
    attention: list[AttentionItem]
    upcoming: list[UpcomingItem]
    recently_added: list[RecentlyAddedItem]
    stats: DashboardStats