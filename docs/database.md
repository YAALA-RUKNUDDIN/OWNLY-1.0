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
replaced | archived. `return_days` = 0 disables return tracking.
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
run can never re-send a push (notification-fatigue protection).

---

## Relationships (cascades)

```
users 1─┬─N products 1─┬─N warranties        (CASCADE)
        │              ├─N documents         (CASCADE)
        │              ├─N reminders         (CASCADE)
        │              ├─N service_records   (CASCADE)
        │              ├─N repairs           (CASCADE)
        │              └─N timeline_events   (CASCADE)
        ├─N refresh_tokens                 (CASCADE)
        ├─N device_tokens                  (CASCADE)
        └─N notification_preferences       (CASCADE)
documents.user_id → users.id                (CASCADE)
```

Deleting a user (account deletion) cascades everything — no orphaned data.
Deleting a product soft-deletes it; hard delete happens only via account
deletion, preserving the audit story.

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
