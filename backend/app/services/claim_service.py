"""Warranty claim business logic, dossier compiling, and event logging."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.integrations.storage import get_storage
from app.models import EventType, Product, User, Warranty, WarrantyClaim
from app.models.claim import ClaimStatus
from app.repositories.claim_repo import ClaimRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.claim import BrandSupportOut, ClaimDossierOut, ClaimOut
from app.services.brand_support_service import BrandSupportService
from app.services.timeline_service import record_event
from app.services.warranty_service import compute_warranty_status


class ClaimService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.claim_repo = ClaimRepository(db, user.id)
        self.product_repo = ProductRepository(db, user.id)

    def file_claim(
        self,
        product_id: uuid.UUID,
        title: str,
        issue_description: str,
        incident_date: datetime,
        warranty_id: Optional[uuid.UUID] = None,
        claim_reference: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
    ) -> WarrantyClaim:
        product = self.product_repo.get(product_id)
        if not product:
            raise NotFoundError("Product not found.")

        if not self.product_repo.can_edit_product(product):
            raise ForbiddenError("Viewers have read-only access to household products.")

        # If incident_date is naive, make it aware (or ensure valid comparison)
        now_dt = datetime.now(timezone.utc)
        chk_incident = incident_date if incident_date.tzinfo else incident_date.replace(tzinfo=timezone.utc)
        if chk_incident > now_dt:
            raise ValidationError("Incident date cannot be in the future.")

        # Resolve warranty
        resolved_warranty_id = warranty_id
        if resolved_warranty_id:
            w_exists = any(w.id == resolved_warranty_id for w in product.warranties)
            if not w_exists:
                raise ValidationError("Specified warranty does not belong to this product.")
        elif product.warranties:
            # Pick first active or recent warranty
            resolved_warranty_id = product.warranties[0].id

        email = (contact_email or self.user.email or "").strip()
        claim = self.claim_repo.create(
            product_id=product_id,
            warranty_id=resolved_warranty_id,
            title=title.strip(),
            issue_description=issue_description.strip(),
            incident_date=incident_date,
            claim_reference=claim_reference.strip() if claim_reference else None,
            contact_email=email or None,
            contact_phone=contact_phone.strip() if contact_phone else None,
        )

        record_event(
            self.db,
            product_id=product.id,
            event_type=EventType.claim_filed,
            title=f"Warranty claim filed: {claim.title}",
            description=f"Status: {claim.status.value}. Ref: {claim.claim_reference or 'Draft'}. Issue: {claim.issue_description[:120]}",
            event_date=incident_date.date() if hasattr(incident_date, "date") else datetime.now().date(),
            metadata={"claim_id": str(claim.id), "status": claim.status.value},
        )
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def update_claim(self, claim_id: uuid.UUID, **fields) -> WarrantyClaim:
        claim = self.claim_repo.get(claim_id)
        if not claim:
            raise NotFoundError("Claim not found.")

        product = self.product_repo.get(claim.product_id)
        if not product or not self.product_repo.can_edit_product(product):
            raise ForbiddenError("You do not have permission to modify this claim.")

        old_status = claim.status.value
        new_status = fields.get("status")

        updated = self.claim_repo.update(claim, **fields)

        if new_status and new_status != old_status:
            ev_type = (
                EventType.claim_resolved
                if new_status in ("approved", "repaired", "replaced", "closed")
                else EventType.claim_updated
            )
            record_event(
                self.db,
                product_id=product.id,
                event_type=ev_type,
                title=f"Claim status updated: {new_status}",
                description=f"Claim '{claim.title}' updated from {old_status} to {new_status}.",
                metadata={"claim_id": str(claim.id), "old_status": old_status, "new_status": new_status},
            )

        self.db.commit()
        self.db.refresh(updated)
        return updated

    def delete_claim(self, claim_id: uuid.UUID) -> None:
        claim = self.claim_repo.get(claim_id)
        if not claim:
            raise NotFoundError("Claim not found.")

        product = self.product_repo.get(claim.product_id)
        if not product:
            raise NotFoundError("Product not found.")

        role = self.product_repo.get_user_role_for_product(product)
        if role not in ("owner", "admin") and claim.user_id != self.user.id:
            raise ForbiddenError("Only the claim owner or household admin can delete this claim.")

        self.claim_repo.delete(claim)
        self.db.commit()

    def format_claim_out(self, claim: WarrantyClaim) -> ClaimOut:
        prod = claim.product
        brand_info = BrandSupportService.get_brand_support(prod.brand)
        support_out = None
        if brand_info:
            support_out = BrandSupportOut(
                brand=brand_info.brand,
                category=brand_info.category,
                support_phone=brand_info.support_phone,
                support_url=brand_info.support_url,
                claim_portal_url=brand_info.claim_portal_url,
                warranty_check_url=brand_info.warranty_check_url,
                serial_lookup_url=brand_info.serial_lookup_url,
                support_hours=brand_info.support_hours,
                notes=brand_info.notes,
            )

        return ClaimOut(
            id=claim.id,
            product_id=claim.product_id,
            product_name=prod.name,
            product_brand=prod.brand,
            product_serial=prod.serial_number,
            warranty_id=claim.warranty_id,
            warranty_provider=claim.warranty.provider if claim.warranty else None,
            claim_reference=claim.claim_reference,
            title=claim.title,
            issue_description=claim.issue_description,
            status=claim.status.value,
            incident_date=claim.incident_date,
            resolution_notes=claim.resolution_notes,
            claim_cost_covered=float(claim.claim_cost_covered) if claim.claim_cost_covered is not None else None,
            contact_email=claim.contact_email,
            contact_phone=claim.contact_phone,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            brand_support=support_out,
        )

    def generate_dossier(self, claim_id: uuid.UUID) -> ClaimDossierOut:
        claim = self.claim_repo.get(claim_id)
        if not claim:
            raise NotFoundError("Claim not found.")

        product = self.product_repo.get_with_documents(claim.product_id)
        if not product:
            raise NotFoundError("Product not found.")

        storage = get_storage()
        doc_list = []
        for doc in product.documents:
            try:
                download_url = storage.signed_url(doc.file_url, expires_in_seconds=3600)
            except Exception:
                download_url = doc.file_url
            doc_list.append({
                "id": str(doc.id),
                "name": doc.document_name,
                "type": doc.document_type.value,
                "download_url": download_url,
            })

        repair_list = [
            {
                "id": str(r.id),
                "vendor": r.vendor,
                "cost": float(r.cost) if r.cost is not None else 0.0,
                "notes": r.notes,
                "created_at": r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
            }
            for r in product.repairs
        ]

        w_dict = None
        if claim.warranty:
            status_str, days_rem = compute_warranty_status(claim.warranty.end_date)
            w_dict = {
                "id": str(claim.warranty.id),
                "provider": claim.warranty.provider or product.brand or "Manufacturer",
                "type": claim.warranty.warranty_type.value,
                "start_date": claim.warranty.start_date.isoformat() if hasattr(claim.warranty.start_date, "isoformat") else str(claim.warranty.start_date),
                "end_date": claim.warranty.end_date.isoformat() if hasattr(claim.warranty.end_date, "isoformat") else str(claim.warranty.end_date),
                "duration_months": claim.warranty.duration_months,
                "status": status_str,
                "days_remaining": days_rem,
            }

        brand_info = BrandSupportService.get_brand_support(product.brand)
        support_out = None
        if brand_info:
            support_out = BrandSupportOut(
                brand=brand_info.brand,
                category=brand_info.category,
                support_phone=brand_info.support_phone,
                support_url=brand_info.support_url,
                claim_portal_url=brand_info.claim_portal_url,
                warranty_check_url=brand_info.warranty_check_url,
                serial_lookup_url=brand_info.serial_lookup_url,
                support_hours=brand_info.support_hours,
                notes=brand_info.notes,
            )

        claim_out = self.format_claim_out(claim)

        # Build clean formatted markdown packet
        inc_str = claim.incident_date.strftime("%Y-%m-%d") if hasattr(claim.incident_date, "strftime") else str(claim.incident_date)[:10]
        purch_str = product.purchase_date.strftime("%Y-%m-%d") if hasattr(product.purchase_date, "strftime") else str(product.purchase_date)[:10]

        md_lines = [
            f"# WARRANTY CLAIM DOSSIER",
            f"**Claim Reference:** {claim.claim_reference or 'Pending Assignment'}",
            f"**Current Status:** {claim.status.value.upper()}",
            f"**Dossier Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            "## 1. Product Identification & Purchase Details",
            f"- **Product:** {product.name}",
            f"- **Manufacturer / Brand:** {product.brand or 'N/A'}",
            f"- **Model Number:** {product.model_number or 'N/A'}",
            f"- **Serial Number / Service Tag:** {product.serial_number or 'N/A'}",
            f"- **IMEI / Device ID:** {product.imei_number or 'N/A'}",
            f"- **Purchase Date:** {purch_str}",
            f"- **Purchase Price:** {product.currency} {product.purchase_price or 0.00:.2f}",
            f"- **Retailer / Seller:** {product.seller or 'N/A'}",
            f"- **Purchase Location:** {product.purchase_location or 'N/A'}",
            "",
            "## 2. Warranty Coverage",
        ]

        if w_dict:
            md_lines.extend([
                f"- **Warranty Type:** {w_dict['type'].title()} Warranty",
                f"- **Coverage Provider:** {w_dict['provider']}",
                f"- **Coverage Window:** {w_dict['start_date'][:10]} to {w_dict['end_date'][:10]} ({w_dict['duration_months'] or 'N/A'} months)",
                f"- **Warranty Status:** {w_dict['status'].upper()} ({w_dict['days_remaining']} days remaining)",
            ])
        else:
            md_lines.append("- *No warranty certificate formally linked; claim filed under statutory / implied merchantability.*")

        md_lines.extend([
            "",
            "## 3. Incident & Defect Description",
            f"- **Incident / Failure Date:** {inc_str}",
            f"- **Issue Summary:** {claim.title}",
            f"- **Detailed Description:**",
            f"  {claim.issue_description}",
            "",
            "## 4. Claimant Information",
            f"- **Name:** {self.user.name}",
            f"- **Contact Email:** {claim.contact_email or self.user.email}",
            f"- **Contact Phone:** {claim.contact_phone or 'N/A'}",
            "",
            "## 5. Verified Documents & Invoices Attached",
        ])

        if doc_list:
            for d in doc_list:
                md_lines.append(f"- [{d['type'].replace('_', ' ').title()}] {d['name']} — [View/Download Record]({d['download_url']})")
        else:
            md_lines.append("- *No uploaded invoices or receipts on file for this product.*")

        if repair_list:
            md_lines.extend([
                "",
                "## 6. Prior Service & Repair History",
            ])
            for r in repair_list:
                md_lines.append(f"- **{r['created_at'][:10]}** | Vendor: {r['vendor'] or 'Independent'} | Cost: ${r['cost']:.2f} | Notes: {r['notes'] or 'N/A'}")

        if support_out:
            md_lines.extend([
                "",
                "## 7. Official Brand Support Contacts",
                f"- **Support Phone:** {support_out.support_phone}",
                f"- **Official Portal:** {support_out.support_url}",
                f"- **Warranty Claim / RMA URL:** {support_out.claim_portal_url}",
                f"- **Service Hours:** {support_out.support_hours}",
            ])

        formatted_markdown = "\n".join(md_lines)

        return ClaimDossierOut(
            dossier_id=claim.id,
            generated_at=datetime.now(timezone.utc),
            claim=claim_out,
            product={
                "id": str(product.id),
                "name": product.name,
                "brand": product.brand,
                "model_number": product.model_number,
                "serial_number": product.serial_number,
                "imei_number": product.imei_number,
                "purchase_date": purch_str,
                "purchase_price": float(product.purchase_price) if product.purchase_price is not None else 0.0,
                "currency": product.currency,
                "seller": product.seller,
                "category": product.category,
            },
            warranty=w_dict,
            documents=doc_list,
            repairs=repair_list,
            brand_support=support_out,
            claimant={
                "name": self.user.name,
                "email": claim.contact_email or self.user.email,
                "phone": claim.contact_phone,
            },
            formatted_markdown=formatted_markdown,
        )
