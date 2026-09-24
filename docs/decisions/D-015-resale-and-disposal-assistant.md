# D-015: Resale & Disposal Assistant, Dynamic Valuation & Portfolio Analytics

**Status:** Accepted · **Date:** 2026-09-24 · **Phase:** 10

## Context

Throughout the post-purchase lifecycle, OWNLY tracks warranties, invoices, service records, and warranty claims. However, every product eventually reaches its exit point: selling second-hand, recycling responsibly, donating, or retiring.

Prior to Phase 10:
1. **No Resale Valuation Guidance:** Users had no visibility into what their gadgets, appliances, or tools are currently worth or how quickly they are depreciating.
2. **Hidden Net Cost of Ownership:** True ownership cost (`purchase price + repairs - resale recovery`) was invisible, leaving users unable to assess cost-per-day or ROI across brands and categories.
3. **Friction in Creating Marketplace Listings:** Listing an item on eBay, Swappa, Facebook Marketplace, or Craigslist required re-typing specs, finding original purchase dates, and digging up repair receipts.
4. **Untracked Lifecycle Exits:** When a product was sold, recycled, or donated, users had to either delete the item (losing history) or leave it active.

## Decision

- **Data Model & Invariants (`app/models/product.py` & `app/models/timeline_event.py`):**
  - Added `ProductCondition` enum (`mint`, `excellent`, `good`, `fair`, `poor`), defaulting to `good`.
  - Extended `ProductStatus` enum with `recycled` and `donated`.
  - Added product columns: `condition`, `resale_price`, `resale_date`, `resale_platform`, and `resale_notes`.
  - Added timeline event types: `product_sold`, `product_recycled`, and `product_donated`.
  - Invariant: A product marked sold must include a non-negative `resale_price`.
  - Invariant: Household viewers receive `403 Forbidden` if attempting to sell or dispose of a shared household product.

- **Dynamic Valuation & Net Ownership Cost Engine (`app/services/resale_service.py`):**
  - Category-calibrated annual depreciation curves (e.g. 25% for electronics/computing, 15% for appliances/tools, 20% for audio/gaming, 12% for furniture).
  - Condition multiplier factors (`mint`: 1.12x, `excellent`: 1.05x, `good`: 1.00x, `fair`: 0.82x, `poor`: 0.60x).
  - Calculates:
    - `estimated_resale_value` & `value_retention_percent`.
    - Suggested listing price range (`low` for quick sale, `fair` for market rate, `high` for patient sale).
    - `net_cost_of_ownership` (`purchase_price + total_repairs_cost - estimated_or_actual_resale`).
    - `cost_per_day` over `days_owned`.

- **One-Click Marketplace Resale Listing Packet Generator (`ResaleService.generate_resale_packet`):**
  - Compiles optimized listing title, recommended asking price and negotiation range, specifications, certified repair and maintenance history, and attached invoice/document proofs.
  - Generates ready-to-copy Markdown and plain text descriptions for rapid listing on eBay, Swappa, Craigslist, Facebook Marketplace, or specialized forums.

- **Portfolio-Wide Analytics (`GET /portfolio/analytics`):**
  - Aggregates user portfolio purchase value, estimated secondary market value, value retention %, realized gains from sales, and category-level retention breakdowns.

- **API Strategy (`app/api/resale.py`):**
  - `GET /products/{id}/valuation`
  - `PATCH /products/{id}/condition`
  - `GET /products/{id}/resale-packet`
  - `POST /products/{id}/sell`
  - `POST /products/{id}/dispose`
  - `GET /portfolio/analytics`

- **Mobile Implementation (Flutter & Riverpod):**
  - Models: `ProductValuationItem`, `PriceRangeItem`, `ResaleListingPacketItem`, `ResaleRepairItem`, `ResaleDocumentItem`, `PortfolioAnalyticsItem`, `CategoryValueBreakdownItem`.
  - Repository: `ResaleRepository` with provider `resaleRepositoryProvider`.
  - UI Components:
    - `ResaleTab` in `ProductDetailScreen` featuring valuation hero card, condition chips selector, and action buttons.
    - `ResaleListingModal` bottom sheet with verified repair history, buyer trust dossier, and one-click clipboard copy.
    - `MarkAsSoldDialog` with realized net cost calculator, selling platform dropdown, and condition selection.
    - `MarkAsDisposedDialog` with exit method selector (`recycled`, `donated`, `archived`).
    - `PortfolioAnalyticsScreen` with category breakdown chips, active/sold/disposed counters, and retention metrics.
    - Registered `/portfolio` route in `ownly_router.dart` and `OwnlyRoutes.portfolio`.

- **Alembic Migration & Dual Database Parity:**
  - Added revision `d0a71c8e5f33_add_resale_fields_to_products.py` chained from `c9f61b8e4a22`.
  - PostgreSQL enum upgrade statements: `ALTER TYPE product_status ADD VALUE IF NOT EXISTS 'recycled'/'donated'`.
  - Full round-trip parity on SQLite and PostgreSQL.

## Consequences

- 10 new pytest tests in `backend/tests/test_resale.py` (total 153 backend tests passing).
- 7 new Flutter unit and widget tests in `mobile/test/resale_test.dart` (total 37 mobile tests passing, 0 analysis issues).
- Full product lifecycle closed: from purchase and warranty to maintenance, claims, and second-hand exit.
