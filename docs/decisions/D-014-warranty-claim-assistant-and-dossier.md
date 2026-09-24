# D-014: Warranty Claim Assistant, Brand Support Directory & Claim Dossiers

**Status:** Accepted · **Date:** 2026-09-24 · **Phase:** 9

## Context

A core promise of OWNLY is answering *"What do I need to do about the things I own today?"* Prior to Phase 9, OWNLY effectively tracked when warranties and return windows expire, logged repairs, and stored invoices. However, when an appliance, laptop, or gadget actually broke, users faced high friction:
1. **Scattered Proof of Purchase:** Locating serial numbers, purchase dates, and invoices across emails and file systems.
2. **Opaque Manufacturer Support Channels:** Hunting for official warranty claim portals, hotlines, or serial check tools amidst third-party ad links.
3. **No Claim Lifecycle Tracking:** Once a claim is filed or unit shipped for RMA repair, users lacked a structured way to track status (draft, submitted, in review, approved, replaced, closed) and covered repair expenses.
4. **Tedious Manual Claim Assembly:** Repair centers and warranty providers require proof-of-purchase dossiers with serial numbers, retailer info, defect descriptions, and invoices.

## Decision

- **Data Model & Invariants (`app/models/claim.py` & `app/models/timeline_event.py`):**
  - Added `ClaimStatus` enum (`draft`, `submitted`, `in_review`, `approved`, `repaired`, `replaced`, `rejected`, `closed`).
  - Added `WarrantyClaim` model linking `product_id` (cascade delete), `user_id`, and optional `warranty_id`.
  - Added `claim_reference` (e.g. RMA or support case number), `title`, `issue_description`, `incident_date`, `resolution_notes`, `claim_cost_covered`, and contact details.
  - Added `claims` relationship to `Product` model with `cascade="all, delete-orphan"`.
  - Added `claim_filed`, `claim_updated`, and `claim_resolved` events to `EventType`.
  - Invariant: A claim's incident date cannot be set in the future.
  - Invariant: Household viewers receive `403 Forbidden` if attempting to file, edit, or delete a claim on a shared product.

- **Brand Support Directory (`app/services/brand_support_service.py`):**
  - Curated, searchable directory covering top consumer brands (Apple, Samsung, Sony, Dell, HP, Lenovo, LG, Bose, Dyson, Microsoft, Google, Nintendo, ASUS, Whirlpool, KitchenAid, Canon, Logitech).
  - Supplies verified support hotlines, official support portals, claim/RMA URLs, serial number lookup tools, and operating hours.
  - Auto-attaches to claims based on `product.brand`.

- **One-Click Claim Dossier Generation (`ClaimService.generate_dossier`):**
  - Generates a structured packet combining product metadata, serial numbers, active warranty status, attached documents with HMAC-signed download URLs, repair history, and user contact details.
  - Generates ready-to-print/copy formatted Markdown suitable for pasting into email submissions or manufacturer support portals.

- **API Strategy (`app/api/claims.py`):**
  - `GET /claims/support-directory` & `GET /claims/support-directory/{brand}`
  - `POST /products/{product_id}/claims` (201 Created)
  - `GET /products/{product_id}/claims`
  - `GET /claims` (filterable by status, paginated)
  - `GET /claims/{id}`
  - `PATCH /claims/{id}`
  - `DELETE /claims/{id}` (204 No Content)
  - `GET /claims/{id}/dossier`

- **Mobile Implementation (Flutter & Riverpod):**
  - Models: `BrandSupportItem`, `WarrantyClaimItem`, `ClaimDossierItem`.
  - Repository: `ClaimRepository` with provider `claimRepositoryProvider`.
  - UI Screens & Modals:
    - `ClaimsScreen` with filter chips (`All`, `Draft`, `Submitted`, `In Review`, `Approved`, `Closed`) and status cards.
    - `ClaimDetailScreen` with status tracker, manufacturer support hotline copy/call, and RMA management.
    - `ClaimsTab` integrated into `ProductDetailScreen` with quick "File Claim" button and brand support banner.
    - `FileClaimDialog` modal bottom sheet with incident date picker and validation.
    - `ClaimDossierModal` bottom sheet with structured claim packet preview and markdown copy action.
    - Added `/claims` and `/claims/:id` routes in `ownly_router.dart` and `OwnlyRoutes.claims`.
    - Added "Warranty claims" navigation tile under Account in `ProfileScreen`.

- **Alembic Migration & Dual Database Parity:**
  - Added revision `c9f61b8e4a22_add_warranty_claims.py` chained from `b8e52a9c3d41`.
  - Tested on SQLite test database and PostgreSQL migration chain.

## Consequences

- Users can file, track, and resolve warranty claims in under 60 seconds with auto-filled product and warranty data.
- Manufacturer contact details and claim portals are surfaced contextually without leaving the app.
- Full privacy preservation and GDPR export: claims are included in `/users/me/export` and cascading account deletion.
- 143 backend tests and 30 mobile tests passing with 0 lint/analysis issues.
