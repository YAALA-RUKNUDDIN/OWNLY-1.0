"""Resale, valuation depreciation engine, listing generator, and lifecycle exit service."""
import math
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.integrations.storage import get_storage
from app.models import EventType, Product, User
from app.models.product import ProductCondition, ProductStatus
from app.repositories.product_repo import ProductRepository
from app.schemas.resale import (
    CategoryValueBreakdown,
    PortfolioAnalyticsOut,
    PriceRangeOut,
    ProductDisposeIn,
    ProductSellIn,
    ProductValuationOut,
    ResaleDocumentOut,
    ResaleListingPacketOut,
    ResaleRepairOut,
)
from app.services.timeline_service import record_event
from app.services.warranty_service import compute_warranty_status


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResaleService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.product_repo = ProductRepository(db, user.id)

    @staticmethod
    def _compute_depreciation_rate(category: str, condition: str) -> tuple[float, float, float]:
        """Returns (year_1_rate, subsequent_year_rate, min_floor)."""
        cat = (category or "other").lower().strip()

        if cat in ("smartphones", "laptops", "tablets", "headphones", "electronics", "gaming", "cameras"):
            y1 = 0.30
            sub = 0.15
            floor = 0.10
        elif cat in ("home_appliances", "appliances"):
            y1 = 0.15
            sub = 0.12
            floor = 0.15
        elif cat in ("furniture", "home"):
            y1 = 0.25
            sub = 0.10
            floor = 0.20
        elif cat in ("vehicles", "bikes", "automotive"):
            y1 = 0.20
            sub = 0.10
            floor = 0.15
        elif cat in ("watches", "jewelry"):
            y1 = 0.12
            sub = 0.05
            floor = 0.35
        elif cat in ("tools", "equipment"):
            y1 = 0.15
            sub = 0.08
            floor = 0.25
        else:
            y1 = 0.25
            sub = 0.12
            floor = 0.15

        # Condition modifier adjustments
        cond = (condition or "good").lower()
        if cond == "mint":
            cond_mult = 1.15
        elif cond == "excellent":
            cond_mult = 1.05
        elif cond == "good":
            cond_mult = 1.00
        elif cond == "fair":
            cond_mult = 0.80
        elif cond == "poor":
            cond_mult = 0.50
        else:
            cond_mult = 1.00

        return y1, sub, floor, cond_mult

    def calculate_valuation(self, product: Product, now: Optional[datetime] = None) -> ProductValuationOut:
        """Computes current estimated resale value, TCO, and retention rate at read time."""
        now_dt = now or utcnow()
        p_date = product.purchase_date
        if p_date.tzinfo is None:
            p_date = p_date.replace(tzinfo=timezone.utc)

        days_owned = max(1, (now_dt - p_date).days)
        years_owned = days_owned / 365.25

        total_repairs = sum(float(r.cost) for r in product.repairs if r.cost is not None)
        is_sold = product.status == ProductStatus.sold

        if product.purchase_price is None or float(product.purchase_price) <= 0:
            actual_resale = float(product.resale_price) if product.resale_price is not None else None
            realized_net = (total_repairs - actual_resale) if actual_resale is not None else None
            return ProductValuationOut(
                product_id=product.id,
                product_name=product.name,
                brand=product.brand,
                category=product.category,
                condition=product.condition or "good",
                purchase_date=p_date,
                purchase_price=None,
                currency=product.currency or "USD",
                days_owned=days_owned,
                estimated_resale_value=actual_resale,
                value_retention_percent=None,
                total_repairs_cost=round(total_repairs, 2),
                net_cost_of_ownership=realized_net,
                cost_per_day=round(realized_net / days_owned, 2) if realized_net is not None else None,
                depreciation_amount=None,
                annual_depreciation_rate=0.0,
                suggested_listing_price_range=None,
                is_sold=is_sold,
                actual_resale_price=actual_resale,
                realized_net_cost=round(realized_net, 2) if realized_net is not None else None,
            )

        P = float(product.purchase_price)
        y1, sub, floor, cond_mult = self._compute_depreciation_rate(product.category, product.condition)

        # Compound depreciation curve
        if years_owned <= 1.0:
            retention = 1.0 - (y1 * years_owned)
        else:
            remaining_years = years_owned - 1.0
            retention = (1.0 - y1) * math.pow(1.0 - sub, remaining_years)

        adjusted_retention = max(floor, retention * cond_mult)
        # Cap retention at 1.25x original purchase price
        adjusted_retention = min(1.25, adjusted_retention)

        estimated_val = round(P * adjusted_retention, 2)

        low_val = round(estimated_val * 0.90, 2)
        high_val = round(estimated_val * 1.10, 2)
        price_range = PriceRangeOut(low=low_val, fair=estimated_val, high=high_val)

        # Net Cost of Ownership calculation
        if is_sold and product.resale_price is not None:
            actual_sale = float(product.resale_price)
            net_cost = P + total_repairs - actual_sale
            actual_resale_out = actual_sale
            realized_net_out = round(net_cost, 2)
        else:
            actual_sale = None
            actual_resale_out = None
            realized_net_out = None
            net_cost = P + total_repairs - estimated_val

        cost_per_day = round(net_cost / days_owned, 2)
        retention_pct = round((estimated_val / P) * 100, 1)
        depreciation_amt = round(P - estimated_val, 2)
        annual_rate = round(y1 * 100, 1) if years_owned <= 1 else round(((1.0 - adjusted_retention) / years_owned) * 100, 1)

        return ProductValuationOut(
            product_id=product.id,
            product_name=product.name,
            brand=product.brand,
            category=product.category,
            condition=product.condition or "good",
            purchase_date=p_date,
            purchase_price=P,
            currency=product.currency or "USD",
            days_owned=days_owned,
            estimated_resale_value=estimated_val,
            value_retention_percent=retention_pct,
            total_repairs_cost=round(total_repairs, 2),
            net_cost_of_ownership=round(net_cost, 2),
            cost_per_day=cost_per_day,
            depreciation_amount=depreciation_amt,
            annual_depreciation_rate=annual_rate,
            suggested_listing_price_range=price_range,
            is_sold=is_sold,
            actual_resale_price=actual_resale_out,
            realized_net_cost=realized_net_out,
        )

    def get_product_valuation(self, product_id: uuid.UUID) -> ProductValuationOut:
        product = self.product_repo.get(product_id)
        if not product:
            raise NotFoundError("Product not found.")
        return self.calculate_valuation(product)

    def generate_resale_packet(self, product_id: uuid.UUID) -> ResaleListingPacketOut:
        """Generates marketplace-ready markdown and plain text listings with verified document links."""
        product = self.product_repo.get_with_documents(product_id)
        if not product:
            raise NotFoundError("Product not found.")

        val = self.calculate_valuation(product)
        storage = get_storage()

        docs_out: list[ResaleDocumentOut] = []
        for doc in product.documents:
            try:
                download_url = storage.signed_url(doc.file_url, expires_in_seconds=86400)  # 24 hour URL for buyers
            except Exception:
                download_url = doc.file_url

            docs_out.append(
                ResaleDocumentOut(
                    name=doc.document_name,
                    type=doc.document_type.value,
                    download_url=download_url,
                )
            )

        repairs_out: list[ResaleRepairOut] = []
        for r in product.repairs:
            repairs_out.append(
                ResaleRepairOut(
                    repair_date=r.created_at.strftime("%Y-%m-%d") if r.created_at else None,
                    repair_vendor=r.vendor,
                    description=r.notes,
                    cost=float(r.cost) if r.cost is not None else None,
                )
            )

        # Warranty status string
        warranty_str = "None"
        if product.warranties:
            active_w = next((w for w in product.warranties if w.end_date), product.warranties[0])
            status_str, days_rem = compute_warranty_status(active_w.end_date)
            if status_str in ("active", "expiring_soon"):
                warranty_str = f"Active ({active_w.provider or 'Manufacturer'}) through {active_w.end_date.strftime('%Y-%m-%d')} ({days_rem} days remaining)"
            else:
                warranty_str = f"Expired on {active_w.end_date.strftime('%Y-%m-%d')}"

        # Masked serial for security
        serial_masked = "Not provided"
        if product.serial_number:
            raw_s = product.serial_number
            if len(raw_s) > 4:
                serial_masked = "*" * (len(raw_s) - 4) + raw_s[-4:]
            else:
                serial_masked = raw_s

        specs = {
            "name": product.name,
            "brand": product.brand or "Unknown",
            "model_number": product.model_number or "N/A",
            "serial_number_masked": serial_masked,
            "category": product.category,
            "condition": (product.condition or "good").capitalize(),
            "original_purchase_date": product.purchase_date.strftime("%Y-%m-%d"),
            "days_owned": val.days_owned,
            "warranty_status": warranty_str,
        }

        # Formatted Markdown
        brand_prefix = f"{product.brand} " if product.brand else ""
        listing_title = f"{brand_prefix}{product.name} - {(product.condition or 'good').capitalize()} Condition"
        suggested_price = val.estimated_resale_value

        md_lines = [
            f"# {listing_title}",
            "",
            f"**Asking Price:** ${suggested_price:,.2f} USD" if suggested_price else "**Asking Price:** Best reasonable offer",
            "",
            "## 📋 Item Specifications",
            f"- **Item:** {product.name}",
            f"- **Brand:** {product.brand or 'N/A'}",
            f"- **Model Number:** {product.model_number or 'N/A'}",
            f"- **Condition:** {(product.condition or 'good').capitalize()}",
            f"- **Original Purchase Date:** {product.purchase_date.strftime('%B %d, %Y')}",
            f"- **Serial Number:** `{serial_masked}`",
            f"- **Warranty:** {warranty_str}",
            "",
            "## 🛠️ Maintenance & Care History",
        ]

        if repairs_out:
            for rep in repairs_out:
                rep_date = rep.repair_date or "Recorded"
                rep_vendor = f" by {rep.repair_vendor}" if rep.repair_vendor else ""
                rep_desc = f": {rep.description}" if rep.description else ""
                md_lines.append(f"- **{rep_date}**{rep_vendor}{rep_desc}")
        else:
            md_lines.append("- *No repairs needed during ownership; pristine operational care.*")

        md_lines.append("")
        md_lines.append("## 🧾 Authenticity & Proof of Purchase")
        if docs_out:
            md_lines.append("Original receipts and documents are available for inspection:")
            for d in docs_out:
                md_lines.append(f"- [{d.name}]({d.download_url}) ({d.type.replace('_', ' ').capitalize()})")
        else:
            md_lines.append("- *Proof of purchase maintained in personal digital archive.*")

        if product.notes:
            md_lines.append("")
            md_lines.append("## 💬 Seller Notes")
            md_lines.append(product.notes)

        formatted_md = "\n".join(md_lines)

        # Plain text description for Craigslist / Facebook Marketplace
        plain_lines = [
            listing_title,
            f"Price: ${suggested_price:,.2f}" if suggested_price else "Price: Make an offer",
            "",
            f"Brand: {product.brand or 'N/A'}",
            f"Model: {product.model_number or 'N/A'}",
            f"Condition: {(product.condition or 'good').capitalize()}",
            f"Purchased: {product.purchase_date.strftime('%Y-%m-%d')}",
            f"Warranty: {warranty_str}",
            "",
            "Maintenance & Service:",
        ]
        if repairs_out:
            for rep in repairs_out:
                plain_lines.append(f"- {rep.repair_date}: {rep.description or 'Service completed'}")
        else:
            plain_lines.append("- Never required repair. Fully functional.")

        if product.notes:
            plain_lines.append("")
            plain_lines.append(f"Notes: {product.notes}")

        plain_text = "\n".join(plain_lines)

        return ResaleListingPacketOut(
            product_id=product.id,
            title=listing_title,
            suggested_price=suggested_price,
            suggested_price_range=val.suggested_listing_price_range,
            condition=product.condition or "good",
            specifications=specs,
            repair_history=repairs_out,
            verified_documents=docs_out,
            formatted_markdown=formatted_md,
            plain_text_description=plain_text,
        )

    def sell_product(self, product_id: uuid.UUID, data: ProductSellIn) -> ProductValuationOut:
        """Marks product as sold, records realized revenue, and computes finalized net cost of ownership."""
        product = self.product_repo.get(product_id)
        if not product:
            raise NotFoundError("Product not found.")

        if not self.product_repo.can_edit_product(product):
            raise ForbiddenError("Viewers have read-only access to household products.")

        now_dt = utcnow()
        sale_dt = data.resale_date or now_dt
        if sale_dt.tzinfo is None:
            sale_dt = sale_dt.replace(tzinfo=timezone.utc)

        if sale_dt > now_dt:
            raise ValidationError("Sale date cannot be in the future.")

        product.status = ProductStatus.sold
        product.resale_price = data.resale_price
        product.resale_date = sale_dt
        product.resale_platform = data.resale_platform
        product.resale_notes = data.resale_notes
        if data.condition:
            product.condition = data.condition

        # Record timeline event
        platform_text = f" on {data.resale_platform}" if data.resale_platform else ""
        record_event(
            db=self.db,
            product_id=product.id,
            event_type=EventType.product_sold,
            title=f"Sold{platform_text} for ${data.resale_price:,.2f}",
            description=data.resale_notes,
            event_date=sale_dt.date(),
            metadata={
                "resale_price": data.resale_price,
                "platform": data.resale_platform,
                "sale_date": sale_dt.isoformat(),
            },
        )

        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)

        return self.calculate_valuation(product)

    def dispose_product(self, product_id: uuid.UUID, data: ProductDisposeIn) -> ProductValuationOut:
        """Marks product as recycled, donated, or archived."""
        product = self.product_repo.get(product_id)
        if not product:
            raise NotFoundError("Product not found.")

        if not self.product_repo.can_edit_product(product):
            raise ForbiddenError("Viewers have read-only access to household products.")

        now_dt = utcnow()
        disp_dt = data.disposal_date or now_dt
        if disp_dt.tzinfo is None:
            disp_dt = disp_dt.replace(tzinfo=timezone.utc)

        if disp_dt > now_dt:
            raise ValidationError("Disposal date cannot be in the future.")

        if data.disposal_type == "recycled":
            product.status = ProductStatus.recycled
            event_type = EventType.product_recycled
            title = "Product Recycled"
        elif data.disposal_type == "donated":
            product.status = ProductStatus.donated
            event_type = EventType.product_donated
            title = "Product Donated"
        else:
            product.status = ProductStatus.archived
            event_type = EventType.product_archived
            title = "Product Archived"

        product.resale_notes = data.notes
        product.resale_date = disp_dt

        record_event(
            db=self.db,
            product_id=product.id,
            event_type=event_type,
            title=title,
            description=data.notes,
            event_date=disp_dt.date(),
            metadata={
                "disposal_type": data.disposal_type,
                "date": disp_dt.isoformat(),
            },
        )

        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)

        return self.calculate_valuation(product)

    def update_condition(self, product_id: uuid.UUID, condition: str) -> ProductValuationOut:
        """Updates product condition and re-evaluates resale valuation."""
        product = self.product_repo.get(product_id)
        if not product:
            raise NotFoundError("Product not found.")

        if not self.product_repo.can_edit_product(product):
            raise ForbiddenError("Viewers have read-only access to household products.")

        cond_clean = condition.lower().strip()
        if cond_clean not in ("mint", "excellent", "good", "fair", "poor"):
            raise ValidationError(f"Invalid condition '{condition}'. Must be mint, excellent, good, fair, or poor.")

        product.condition = cond_clean
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)

        return self.calculate_valuation(product)

    def get_portfolio_analytics(self) -> PortfolioAnalyticsOut:
        """Aggregates whole portfolio valuation, depreciation, realized sales, and category breakdowns."""
        # Query all accessible non-deleted products
        products, _ = self.product_repo.list(page=1, page_size=500)

        total_count = len(products)
        active_count = sum(1 for p in products if p.status == ProductStatus.active)
        sold_count = sum(1 for p in products if p.status == ProductStatus.sold)
        disposed_count = sum(1 for p in products if p.status in (ProductStatus.recycled, ProductStatus.donated, ProductStatus.archived))

        total_purchase = sum(float(p.purchase_price) for p in products if p.purchase_price is not None)
        total_realized_sales = sum(float(p.resale_price) for p in products if p.resale_price is not None)

        category_groups: dict[str, list[Product]] = {}
        total_estimated_resale = 0.0
        total_net_cost = 0.0

        for p in products:
            val = self.calculate_valuation(p)
            if p.status == ProductStatus.active and val.estimated_resale_value is not None:
                total_estimated_resale += val.estimated_resale_value

            if val.net_cost_of_ownership is not None:
                total_net_cost += val.net_cost_of_ownership

            cat = (p.category or "other").lower()
            category_groups.setdefault(cat, []).append(p)

        cat_breakdowns: list[CategoryValueBreakdown] = []
        for cat_name, cat_prods in category_groups.items():
            cat_purch = sum(float(p.purchase_price) for p in cat_prods if p.purchase_price is not None)
            cat_resale = 0.0
            for p in cat_prods:
                v = self.calculate_valuation(p)
                if v.estimated_resale_value:
                    cat_resale += v.estimated_resale_value

            retention_pct = round((cat_resale / cat_purch * 100), 1) if cat_purch > 0 else 0.0
            cat_breakdowns.append(
                CategoryValueBreakdown(
                    category=cat_name,
                    product_count=len(cat_prods),
                    total_purchase_value=round(cat_purch, 2),
                    total_estimated_resale_value=round(cat_resale, 2),
                    retention_percent=retention_pct,
                )
            )

        # Sort category breakdown by total purchase value descending
        cat_breakdowns.sort(key=lambda c: c.total_purchase_value, reverse=True)

        avg_retention = (
            round((total_estimated_resale / total_purchase * 100), 1)
            if total_purchase > 0
            else 0.0
        )

        return PortfolioAnalyticsOut(
            total_products_count=total_count,
            active_products_count=active_count,
            sold_products_count=sold_count,
            disposed_products_count=disposed_count,
            total_purchase_value=round(total_purchase, 2),
            total_estimated_resale_value=round(total_estimated_resale, 2),
            total_realized_from_sales=round(total_realized_sales, 2),
            total_net_cost_of_ownership=round(total_net_cost, 2),
            average_value_retention_percent=avg_retention,
            categories_breakdown=cat_breakdowns,
        )
