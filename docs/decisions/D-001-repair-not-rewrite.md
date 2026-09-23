# D-001: Repair the Existing Backend Instead of Rewriting

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 1

## Context

Phase 0 inspection found a prior build: FastAPI modular monolith (13 routers,
12 models, provider abstractions for OCR/storage/push, JWT with refresh
rotation + reuse detection, 47 tests). It was however non-functional: two
corrupted/truncated files, a stale dependency conflict, and ~30 failing tests.

## Decision

Repair and complete the existing codebase; do not rewrite from zero.

## Why

- The architecture already matches the target spec (API → Service → Repository
  → DB, provider abstractions, user isolation enforced at repository level).
- Rewriting would discard working, tested functionality (auth rotation,
  idempotent notification worker, signed-URL document flow) and re-introduce
  regressions the existing tests are designed to catch.
- The broken state was confined: 2 broken source files + dependency drift +
  test-infra bugs. Repair is hours, rewrite is weeks, for identical outcomes.

## Alternatives Considered

| Option | Verdict |
|---|---|
| Rewrite backend from zero | Rejected: destroys verified behavior, higher risk, no user-visible gain |
| Rewrite only the broken files | Accepted — this is the essence of the repair approach taken |
| Freeze and document as-is | Rejected: product would ship broken |

## Consequences

- Some pre-existing patterns (e.g., enum re-exports, SQLite/PG dual mode) are
  retained even where a fresh build might differ slightly.
- The test suite is now the regression contract; every phase must keep it green.
