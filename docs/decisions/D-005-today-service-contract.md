# D-005: Today Dashboard Contract & Severity Model

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 1

## Context

`app/services/dashboard_service.py` (the TodayService — "the heart of OWNLY")
was missing and had to be reconstructed. The contract is pinned by
`app/schemas/dashboard.py` and the test suite:
`GET /api/v1/dashboard/today` → `{greeting, attention[], upcoming[],
recently_added[], stats}`.

## Decision

- **Buckets:** `attention` (action needed) and `upcoming` (within 120 days,
  past the attention window). Not surfaced: long-expired warranties (> 30 days
  past) and closed return windows — they are history, not action.
- **Severity model:** `critical` (overdue / <= 7 days), `warning`
  (8–30 days), `info` (recently expired). Return windows: critical <= 2 days
  (per spec: "2 days remaining", "last day"), warning <= 5 days.
- **Thresholds** mirror the existing warranty service (`EXPIRING_SOON_DAYS =
  30`, `RETURN_EXPIRING_SOON_DAYS = 5`) so the Today screen, product cards,
  and notification milestones never disagree.
- **Classification is pure** (`classify_warranty/return/service/reminder`) —
  no DB access, independently unit-testable; the DB layer only feeds and sorts.
- **AttentionItem.product_id is optional** (schema change) because user-level
  custom reminders can exist without a product.
- **Sort:** severity → days remaining. Duplicate (product, kind, date) rows are
  de-duplicated so two warranties expiring the same day produce one item.

## Why

- The spec's example ("Warranty expires in 14 days" under NEEDS ATTENTION)
  requires the 14-day case to fall in attention → the 30-day window is the
  minimal honest choice that satisfies it.
- Pure classifiers can be tested without any database, keeping the most
  business-critical logic cheap to test and reason about.

## Alternatives Considered

| Option | Verdict |
|---|---|
| Single flat list sorted by date | Rejected: fails the "action vs noise" differentiator |
| Storing status in the DB (denormalized) | Rejected: statuses computed at read time can never be stale (trust principle) |
| Client-side bucketing | Rejected: priorities must be consistent across Today, notifications, and future surfaces |

## Consequences

- Mobile clients render buckets directly; no date math in the UI layer.
- Adding a new event type = one new pure classifier + one query feeding it.
