# D-011: Full-Stack Dockerization, End-to-End Retention Suite & Production Readiness

**Status:** Accepted · **Date:** 2026-09-24 · **Phase:** 6

## Context

OWNLY has reached its production MVP milestone. Over Phases 1 through 5, the core platform was engineered:
- Phase 1: Modular monolith backend with PostgreSQL, SQLAlchemy 2.0, Alembic migrations, JWT authentication with refresh token family rotation, product catalog with return window calculations, document storage with signed URLs, and privacy-first local file serving.
- Phase 2: Retention engine with warranty tracking, timeline event recording, automated reminder engine, TodayService urgency evaluator, tiered subscription gating, privacy data export, and event-driven analytics.
- Phase 3 & 4: Mobile Flutter application built with Flutter 3.x, Riverpod state management, GoRouter declarative routing, responsive UI adhering to the design system (inter font, slate palette, semantic status badges), and offline-tolerant HTTP client.
- Phase 5: Push notification lifecycle with device token registration, test push dispatch, local notification display, and uniform deep-link tap-through routing.

Phase 6 completes the Definition of Done: containerizing the full stack for zero-friction deployment, validating the end-to-end user retention journey and security boundaries in automated tests, expanding live smoke tests, and providing production documentation.

## Decision

- **Docker Multi-Container Orchestration (`docker-compose.yml`):**
  - Managed services:
    - `postgres`: PostgreSQL 16 Alpine with persistent volume `ownly_pgdata`, mapped to host port `5433:5432` to eliminate port collisions with native Windows/Linux developer Postgres instances (D-006). Configured with `pg_isready` healthcheck.
    - `redis`: Redis 7 Alpine with persistent volume `ownly_redisdata`, mapped to `6379:6379`. Configured with `redis-cli ping` healthcheck.
    - `api`: FastAPI application running on Uvicorn, port `8000:8000`. Container image installs `tesseract-ocr` for document receipt scanning, automatically executes `alembic upgrade head` on container boot, mounts persistent document storage, and exposes `/health` with a container healthcheck.
    - `scheduler`: Background worker container running `app.workers.scheduler`, executing recurring warranty and reminder milestone scans.
  - Development and production parity: Identical container architecture and environment configurations across root `docker-compose.yml` and `backend/docker-compose.yml`.

- **Comprehensive End-to-End Retention Suite (`backend/tests/test_e2e_journey.py`):**
  - Added full user journey test `test_complete_e2e_ownership_journey` covering 14 consecutive phases of the OWNLY user lifecycle:
    1. User registration & JWT authentication
    2. Manual product creation with return window calculation
    3. Document receipt upload & HMAC-signed URL generation
    4. Receipt OCR extraction returning an editable draft without auto-saving
    5. User draft confirmation & product creation
    6. Warranty creation & automated timeline milestone logging
    7. Reminder scheduling
    8. TodayService urgency evaluation & dashboard stats aggregation
    9. FCM device token registration & test push notification dispatch
    10. Notification history audit log inspection
    11. Product editing & soft deletion
    12. Subscription tier limits (Free 10-item cap) & upgrade to Unlimited Premium
    13. Data portability: Full JSON export of user profile, products, warranties, reminders, and history
    14. Account deletion: Complete cascade deletion of all user records and storage files

- **Automated Security Controls & Isolation Audit (`test_security_audit_controls`):**
  - Strict tenant boundary isolation: User B receives HTTP 404 (never 200, never leaking metadata) when attempting to access User A's products, documents, signed download URLs, or reminders.
  - Cryptographic download protection: Validates that HMAC-SHA256 signature tampering fails with HTTP 401 (`Invalid signature`), and expired URL tokens fail with HTTP 401 (`Signed URL expired`).
  - Auth perimeter: Protected endpoints reject requests without valid Bearer tokens with HTTP 401 (`Unauthorized`).
  - Refresh token reuse revocation: Replaying an already-used refresh token revokes the entire token family.

- **Live Smoke Test Extension (`backend/smoke_test.py`):**
  - Expanded live smoke testing suite from 16 to 20 automated checks, verifying device registration, push test dispatch, device unregistration, and user notification preference management against running servers.

- **Production Documentation & Verification (`README.md`):**
  - Updated root documentation with architectural overview, quickstart instructions, environment variable matrix, API endpoint directory, test execution guide, and DoD verification matrix.

## Consequences

- Any developer or CI/CD runner can boot the complete OWNLY stack with `docker compose up -d` in seconds.
- Every release candidate is verified by a 14-step E2E journey test asserting core product invariants.
- Security and data isolation standards are continuously validated against regression.
