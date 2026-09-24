# OWNLY — Database Documentation

Dual-mode: **PostgreSQL 16** (production, Alembic-managed) and **SQLite**
(local dev/tests, bootstrapped by `Base.metadata.create_all`). All primary
keys are UUIDs (`GUID` type: native `uuid` on PG, `CHAR(36)` elsewhere).
Timestamps are `TIMESTAMP WITH TIME ZONE` defaulting to `now()`.

Constraint naming is centralized (`database.NAMING_CONVENTION`) so Alembic
autogenerate produces stable, droppable names.

---

## Tables

### users
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | varchar(120) | |
| email | varchar(255) | unique, indexed |
| password_hash | varchar(255) | bcrypt |
| profile_image_url | varchar(500) | nullable |
| is_admin | bool | default false |
| created_at / updated_at | timestamptz | |

Relationships: `products`, `refresh_tokens` (CASCADE).

### refresh_tokens
Hashed refresh tokens. `token_family` groups one login session; rotation keeps
the family, **reuse of a revoked token revokes the family** (theft detection).
Indexed: `token_hash` (unique), `token_family`, `user_id`.

### device_tokens
FCM registration tokens per user (`fcm_token` unique). The worker deletes
invalid tokens reported by the push provider.

### notification_preferences
One row per (user, category). `category` enum: warranty | return_window |
service | custom. `lead_days` stores a JSON list of day-milestones, e.g.
`[90, 30, 7, 1, 0]`.

### products
Ownership record. Soft delete via `deleted_at` (indexed) — never hard-deleted
without explicit account deletion. `status` enum: active | sold | lost |
replaced | archived | recycled | donated. `condition` enum: mint | excellent | good |
fair | poor (default `good`). `resale_price` (numeric 12,2), `resale_date` (timestamptz),
`resale_platform` (varchar 100), `resale_notes` (text). `return_days` = 0 disables return tracking.
Indexes: `ix_products_user_status(user_id, status)`, `ix_products_category`,
`user_id`, `deleted_at`.

### warranties
`warranty_type` enum: manufacturer | extended | store | third_party.
`end_date` may be derived from `duration_months` (`resolve_end_date`).
Index: `ix_warranties_end_date` (the daily scan queries by proximity).

### documents
`file_url` stores the **storage key** — never a public URL; downloads go
through `GET /documents/{id}/download` which issues a short-lived signed URL.
`document_type` enum: invoice | receipt | warranty_card | insurance |
service_document | repair_receipt | manual | other.
Index: `ix_documents_product_user`.

### reminders
`reminder_type`: warranty_expiry | return_expiry | service_due | custom.
`status`: upcoming | completed | dismissed. `recurrence_months` (null =
one-off). Index: `ix_reminders_user_date_status`.

### service_records
Completed service + optional `next_service_date` (feeds TodayService and the
reminder worker). Creating one auto-creates the next `service_due` reminder.

### repairs
Repair journal entries (vendor, cost, notes).

### timeline_events
Append-only ownership journal — inserted, never updated. `event_type` enum
(product_added, warranty_started, warranty_extended, document_uploaded,
service_completed, …). Index: `ix_timeline_product_date`.

### notification_log
Idempotency guard for the daily worker: unique
`(user_id, subject_type, subject_id, milestone, due_date)` — a duplicate scan
run can never re-send a push (notification-fatigue protection). It also backs
the user-facing history endpoint (`GET /notifications`), so no separate table
is needed.

### subscriptions
One row per user (created lazily by `subscription_service.get_or_create`, so
existing accounts need no backfill). `tier` enum: free | premium.
`status` enum: active | canceled | expired. `provider` records how the tier
was granted (`none` default, `manual` for dev/admin grants, store identifiers
later); `provider_ref` holds the receipt/transaction id.
`expires_at` null on a premium row = non-expiring grant.

**Entitlement is never stored as a boolean** — it is computed at read time by
`effective_tier(tier, status, expires_at)`, so an elapsed premium period
degrades to free automatically and can never serve stale access.
Index: `ix_subscriptions_user_id` (unique).

### households
Multi-user shared vaults for family or co-habitants.
`id` (UUID PK), `name` (varchar(120)), `created_by_user_id` (UUID FK -> users.id CASCADE).
Relationships: `creator` (User), `members` (HouseholdMember, cascade delete-orphan),
`invites` (HouseholdInvite, cascade delete-orphan), `products` (Product).

### household_members
Membership join table with RBAC.
`role` enum: admin | member | viewer.
Unique constraint: `(household_id, user_id)`. Index: `ix_household_members_user`.

### household_invites
Time-bound 12-character invite codes (`OWN-XXXX-XXXX`).
`code` (varchar(32), unique, indexed), `role` (HouseholdRole), `expires_at` (timestamptz),
`max_uses` (int), `uses_count` (int).

### warranty_claims
Full lifecycle tracking of manufacturer and third-party warranty claims.
`product_id` (UUID FK -> products.id CASCADE), `warranty_id` (UUID FK -> warranties.id SET NULL),
`user_id` (UUID FK -> users.id CASCADE).
`claim_reference` (varchar(100), e.g. RMA or manufacturer case ID), `title` (varchar(200)),
`issue_description` (text), `incident_date` (timestamptz, future dates rejected),
`status` enum: draft | submitted | in_review | approved | repaired | replaced | rejected | closed (default draft).
`resolution_notes` (text), `claim_cost_covered` (numeric(12,2)), `contact_email`, `contact_phone`.
Indexes: `ix_warranty_claims_product_id`, `ix_warranty_claims_user_id`, `ix_warranty_claims_status`.

---

## Relationships (cascades)

```
users 1─┬─N products 1─┬─N warranties        (CASCADE)
        │              ├─N documents         (CASCADE)
        │              ├─N reminders         (CASCADE)
        │              ├─N service_records   (CASCADE)
        │              ├─N repairs           (CASCADE)
        │              ├─N timeline_events   (CASCADE)
        │              └─N warranty_claims   (CASCADE)
        ├─N refresh_tokens                 (CASCADE)
        ├─N device_tokens                  (CASCADE)
        ├─N notification_preferences       (CASCADE)
        ├─1 subscriptions                  (CASCADE)
        ├─N household_members              (CASCADE)
        └─N warranty_claims                (CASCADE)
households 1─┬─N household_members         (CASCADE)
             ├─N household_invites         (CASCADE)
             └─N products                  (SET NULL on delete — safe personal unlinking)
documents.user_id → users.id                (CASCADE)
```

Deleting a user (account deletion) cascades everything — no orphaned data.
Deleting a product soft-deletes it; hard delete happens only via account
deletion, preserving the audit story. SQLite runs with `PRAGMA foreign_keys=ON`
(engine-level, `database.py`) so those cascades are genuinely enforced in
dev/test exactly as in PostgreSQL.

## Design Decisions

1. **UUID PKs** — non-guessable (no enumeration API leaks), safe to expose in
   URLs, merge-friendly for future sync/family sharing.
2. **Computed status** — warranty/return status derived from dates at read
   time; nothing can go stale (trust principle).
3. **Soft delete for products** — supports undo and the lifecycle states
   (sold/archived) without data loss; hard delete only on account deletion.
4. **Append-only timeline** — the ownership story is auditable; mistakes are
   corrected by new events, not edits.
5. **notification_log as idempotency table** — the unique constraint, not
   application memory, guarantees no duplicate pushes; worker is re-run safe.
6. **JSON-as-text `lead_days`** — portable across SQLite/PG; upgrade path to
   JSONB when PG-only.
7. **`GUID` type decorator** — native PG `uuid` (compact, indexable), CHAR(36)
   on SQLite; application code never sees the difference.
