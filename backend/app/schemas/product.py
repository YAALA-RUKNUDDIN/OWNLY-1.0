import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PRODUCT_CATEGORIES = [
    "smartphones", "laptops", "tablets", "headphones", "electronics",
    "home_appliances", "furniture", "vehicles", "watches", "cameras",
    "gaming", "other",
]

ProductStatusLiteral = Literal["active", "sold", "lost", "replaced", "archived"]


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=120)
    model_number: str | None = Field(default=None, max_length=120)
    category: str = Field(default="other")
    purchase_date: datetime
    purchase_price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    seller: str | None = Field(default=None, max_length=200)
    purchase_location: str | None = Field(default=None, max_length=200)
    serial_number: str | None = Field(default=None, max_length=120)
    imei_number: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, max_length=120)
    custom_id: str | None = Field(default=None, max_length=120)
    payment_info: str | None = None
    return_days: int = Field(default=0, ge=0, le=3650)
    status: ProductStatusLiteral = "active"
    notes: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand: str | None = None
    model_number: str | None = None
    category: str | None = None
    purchase_date: datetime | None = None
    purchase_price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    seller: str | None = None
    purchase_location: str | None = None
    serial_number: str | None = None
    imei_number: str | None = None
    sku: str | None = None
    custom_id: str | None = None
    payment_info: str | None = None
    return_days: int | None = Field(default=None, ge=0, le=3650)
    status: ProductStatusLiteral | None = None
    notes: str | None = None


class WarrantyStatusOut(BaseModel):
    status: Literal["active", "expiring_soon", "expired", "none"]
    days_remaining: int | None
    end_date: datetime | None


class ReturnStatusOut(BaseModel):
    tracked: bool
    status: Literal["active", "expiring_soon", "expired", "none"]
    days_remaining: int | None
    end_date: datetime | None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    brand: str | None
    model_number: str | None
    category: str
    purchase_date: datetime
    purchase_price: float | None
    currency: str
    seller: str | None
    purchase_location: str | None
    serial_number: str | None
    imei_number: str | None
    sku: str | None
    custom_id: str | None
    return_days: int
    status: ProductStatusLiteral
    image_url: str | None
    notes: str | None
    created_at: datetime
    warranty: WarrantyStatusOut | None = None
    return_window: ReturnStatusOut | None = None


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int