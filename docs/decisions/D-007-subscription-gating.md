# D-007: Server-Side Plan Gating with Computed Entitlement

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 2

## Context

OWNLY monetizes with a free tier (capped number of products) and a premium
tier (unlimited products + extra features). Two design questions had to be
settled before writing any billing code:

1. **Where is entitlement decided** — client or server?
2. **How is a subscription represented** — a stored "is_premium" flag, or
   derived from dates?

Store billing (Apple/Google receipts) is not implemented yet, so the model had
to work today without a PSP while not blocking a real one later.

## Decision

- **Entitlement is computed, never stored.** `subscription_service.effective_tier`
  derives the tier from `(tier, status, expires_at)` on every read. A premium
  row whose `expires_at` has passed reads as free immediately; no cron job or
  webhook is required for access to lapse correctly — the same "computed, never
  stale" principle as warranty status (D-005).
- **Enforcement lives server-side** and is centralized in one function,
  `enforce_product_quota(db, user)`, called by `POST /products`. It raises a
  typed `PlanLimitError` (403, code `plan_limit_reached`) carrying
  `{tier, limit, used}` so any client can render an upgrade prompt without
  guessing.
- **One `subscriptions` row per user**, created lazily by `get_or_create` — no
  data backfill for the accounts that already exist, and tests/dev starts stay
  simple.
- **Soft-deleted products do not count** toward the cap (users may replace an
  item without being punished for it).
- **`POST /subscription/activate` is an explicitly documented dev/admin stub**:
  it grants `provider="manual"` premium and is refused when
  `ENVIRONMENT=production`, where only verified store receipts may grant a
  tier. Real receipt verification will replace the stub body without changing
  the read model or any client contract.

## Alternatives Considered

| Option | Verdict |
|---|---|
| Client-side gating only | Rejected: trivially bypassed; the cap is the business model |
| Stored `user.is_premium` boolean flipped by cron | Rejected: introduces an "access is stale" failure mode and a job that must never miss |
| Separate `plans`/`features`/`entitlements` tables (full RBAC-style billing) | Rejected for now: over-modeled for two tiers; would slow Phase 2 without user-visible gain |
| Limit only in the mobile app | Rejected: same as client-side gating |
| Computed tier + lazy row + server enforcement (chosen) | Smallest model that is honest, bypass-proof, and PSP-ready |

## Consequences

- Clients must read `GET /subscription` (tier, limits, usage) rather than
  assuming; the payload is the single source of gating truth for the app.
- Adding a tier means extending `PlanTier`, `limits_for()` and one enum in
  Alembic — no schema restructuring.
- `subscriptions.user_id` is unique + indexed and cascades on account deletion;
  the ORM relationship is `uselist=False` with `delete-orphan` so
  `DELETE /users/me` cannot leave a dangling entitlement.
- Analytics events `subscription_activated` / `subscription_canceled` are
  emitted from these endpoints, so funnel metrics never disagree with the DB.
- SQLite now runs with `PRAGMA foreign_keys=ON` (see D-002) so the cascade in
  the deletion test proves real behavior rather than an untested claim.
