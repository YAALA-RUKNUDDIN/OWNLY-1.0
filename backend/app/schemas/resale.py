"""Pydantic request and response contracts for product resale, valuation, listing generator, and portfolio analytics."""
import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

ConditionLiteral = Literal["mint", "excellent", "good", "fair", "poor"]
DisposalTypeLiteral = Literal["recycled", "donated", "archived"]


class PriceRangeOut(BaseModel):
    low: float
    fair: float
    high: float


class ProductValuationOut(BaseModel):
    product_id: uuid.UUID
    product_name: str
    brand: str | None
    category: str
    condition: str
    purchase_date: datetime
    purchase_price: float | None
    currency: str
    days_owned: int
    estimated_resale_value: float | None
    value_retention_percent: float | None
    total_repairs_cost: float
    net_cost_of_ownership: float | None
    cost_per_day: float | None
    depreciation_amount: float | None
    annual_depreciation_rate: float
    suggested_listing_price_range: PriceRangeOut | None
    is_sold: bool
    actual_resale_price: float | None = None
    realized_net_cost: float | None = None


class ResaleDocumentOut(BaseModel):
    name: str
    type: str
    download_url: str


class ResaleRepairOut(BaseModel):
    repair_date: str | None
    repair_vendor: str | None
    description: str | None
    cost: float | None


class ResaleListingPacketOut(BaseModel):
    product_id: uuid.UUID
    title: str
    suggested_price: float | None
    suggested_price_range: PriceRangeOut | None
    condition: str
    specifications: dict[str, Any]
    repair_history: list[ResaleRepairOut]
    verified_documents: list[ResaleDocumentOut]
    formatted_markdown: str
    plain_text_description: str


class ProductSellIn(BaseModel):
    resale_price: float = Field(ge=0, description="Actual realized sale price")
    resale_date: datetime | None = Field(default=None, description="Transaction date (cannot be future)")
    resale_platform: str | None = Field(default=None, max_length=100, description="eBay, Swappa, Craigslist, Facebook, etc.")
    resale_notes: str | None = Field(default=None, description="Buyer or transaction notes")
    condition: ConditionLiteral | None = Field(default=None, description="Updated condition at sale time")


class ProductDisposeIn(BaseModel):
    disposal_type: DisposalTypeLiteral = Field(default="recycled", description="recycled, donated, or archived")
    disposal_date: datetime | None = Field(default=None, description="Date of disposal (cannot be future)")
    notes: str | None = Field(default=None, description="Recycling facility or donation organization notes")


class CategoryValueBreakdown(BaseModel):
    category: str
    product_count: int
    total_purchase_value: float
    total_estimated_resale_value: float
    retention_percent: float


class PortfolioAnalyticsOut(BaseModel):
    total_products_count: int
    active_products_count: int
    sold_products_count: int
    disposed_products_count: int
    total_purchase_value: float
    total_estimated_resale_value: float
    total_realized_from_sales: float
    total_net_cost_of_ownership: float
    average_value_retention_percent: float
    categories_breakdown: list[CategoryValueBreakdown]
