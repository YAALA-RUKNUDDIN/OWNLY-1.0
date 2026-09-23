import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WarrantyCreate(BaseModel):
    provider: str | None = Field(default=None, max_length=200)
    warranty_type: Literal["manufacturer", "extended", "store", "third_party"] = "manufacturer"
    start_date: datetime
    end_date: datetime | None = None
    duration_months: int | None = Field(default=None, ge=1, le=240)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date is None and self.duration_months is None:
            raise ValueError("Provide either end_date or duration_months")
        return self


class WarrantyUpdate(BaseModel):
    provider: str | None = None
    warranty_type: Literal["manufacturer", "extended", "store", "third_party"] | None = None
    end_date: datetime | None = None
    duration_months: int | None = Field(default=None, ge=1, le=240)
    notes: str | None = None


class WarrantyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    provider: str | None
    warranty_type: str
    start_date: datetime
    end_date: datetime
    duration_months: int | None
    notes: str | None
    status: Literal["active", "expiring_soon", "expired"] | None = None
    days_remaining: int | None = None