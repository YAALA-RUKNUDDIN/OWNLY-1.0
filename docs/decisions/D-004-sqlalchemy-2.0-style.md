# D-004: SQLAlchemy 2.0 Execution Style Everywhere

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 1

## Context

The repaired `product_repo.py` mixed legacy 1.x lazy execution
(`Query.first()/.all()` on `Select`) with 2.0-style `db.execute(...)`. With
SQLAlchemy 2.0.40+, lazy execution raises, and `Result` objects produced by
queries with joined eager loads against collections require an explicit
`.unique()` before `.scalars()`.

## Decision

Standardize all repository code on explicit 2.0 execution:
`db.execute(select(...)).unique().scalars().first()/.all()`.

## Why

- `.unique()` is mandatory whenever a joinedload targets a collection
  (e.g., `Product.warranties`); omitting it raises `InvalidRequestError`.
- Explicit execution makes the SQL surface visible and greppable, and
  matches the documentation SQLAlchemy itself maintains.
- The repository layer is the user-isolation boundary; uniform style makes
  review of every query trivial.

## Alternatives Considered

| Option | Verdict |
|---|---|
| `selectinload` instead of `joinedload` | Used selectively (dashboard) to avoid row multiplication; kept joinedload where one row is fetched |
| Global `unique` in a helper | Rejected: hides the requirement; explicitness wins at the isolation boundary |

## Consequences

- All future repositories must follow this pattern (code-review checklist).
- Tests that exercise eager-loaded paths now pass deterministically.
