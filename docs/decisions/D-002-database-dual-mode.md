# D-002: Keep SQLite/PostgreSQL Dual-Mode Database Support

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 1

## Context

The backend supports two DATABASE_URL targets: SQLite (local dev, tests, and
the one-click `start_ownly.bat` launcher) and PostgreSQL 16 (production,
Docker). The spec mandates PostgreSQL as the production database.

## Decision

Keep both. SQLite is the zero-setup local/dev/test path; PostgreSQL is the
production path. Alembic migrations target PostgreSQL; `create_all` bootstraps
SQLite for dev/test.

## Why

- **Onboarding speed:** a new developer (or the founder) runs the product with
  no Docker/Postgres install — critical for an early-stage startup.
- **CI/test speed:** SQLite file DB keeps the 47-test suite at ~3s; spinning
  Postgres containers per run adds latency and fragility (Docker daemon was
  down during Phase 1 — tests still ran).
- **No production compromise:** `GUID` type decorator gives native UUID on PG,
  CHAR(36) on SQLite; engine pools tuned per dialect.

## Alternatives Considered

| Option | Verdict |
|---|---|
| PostgreSQL-only (spec-literal) | Rejected: kills the one-click local run and slows CI |
| SQLite-only | Rejected: no concurrent-write safety, no native UUID/JSONB for production scale |
| SQLite dev + Postgres prod (chosen) | Keeps dev loop fast, prod safe |

## Consequences

- Datetime handling must tolerate naive (SQLite) vs aware (PG) values —
  centralized in `app/core/datetime_utils.py::as_aware` (used by auth
  refresh-expiry checks, warranty date comparisons, and the reminder worker).
  `resolve_end_date` now always returns an aware UTC value.
- Alembic migrations must be validated on PostgreSQL before release; SQLite
  schema is bootstrapped via `Base.metadata.create_all`.
- PostgreSQL keeps native ENUM types after their tables are dropped, so
  `downgrade()` in each migration must drop the enum types explicitly
  (dialect-guarded) to keep `upgrade → downgrade → upgrade` idempotent.
  Verified for the baseline migration on both engines.
- Some PG-specific features (JSONB, partial indexes) are avoided in ORM so the
  schema remains portable.
