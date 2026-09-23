# OWNLY — Implementation Plan

> Product: **OWNLY** — "What do I need to do about the things I own today?"
> A privacy-first, post-purchase ownership assistant.
> Name is centralized in `backend/app/core/config.py` (`APP_NAME`) and
> `mobile/lib/core/constants/api_constants.dart` — never hardcoded at call sites.

---

## 1. Architecture

```
Flutter App (Riverpod, GoRouter)              ← mobile/
        │ HTTPS + JWT (15 min access / rotating 30-day refresh)
        ▼
FastAPI Backend (modular monolith)            backend/
  API layer          app/api/*       route handlers only — no business logic
  Service layer      app/services/*  business rules (TodayService, warranty math…)
  Repository layer   app/repositories/*  ALL queries, user-isolation boundary
  Models             app/models/*    SQLAlchemy ORM (UUID PKs)
  Integrations       app/integrations/*  provider abstractions:
    ├ OCR      tesseract | google_vision      (OCR_PROVIDER env)
    ├ Storage  local signed-URL | S3/R2/MinIO (STORAGE_PROVIDER env)
    └ Push     noop | FCM                     (PUSH_PROVIDER env)
  Workers            app/workers/*   daily scan + RQ + scheduler
        │
        ├── SQLite  (dev/test/one-click launcher)
        └── PostgreSQL 16 (production, Alembic-migrated)
```

Strict rule: **API → Service → Repository → DB.** Route handlers never query
the database directly; repositories scope every query by `user_id`.

## 2. Folder Structure

```
OWNLY/
├── backend/
│   ├── app/
│   │   ├── api/            13 routers (auth, products, warranties, documents,
│   │   │                   reminders, timeline, repairs, users, ocr, files,
│   │   │                   dashboard, admin, deps)
│   │   ├── core/           config, security, database, errors
│   │   ├── models/         12 models + enums
│   │   ├── schemas/        Pydantic request/response contracts
│   │   ├── repositories/   5 repositories (user-isolation boundary)
│   │   ├── services/       warranty math, timeline, dashboard (TodayService),
│   │   │                   export, user
│   │   ├── integrations/   ocr/ storage/ push/ provider abstractions
│   │   └── workers/        jobs (idempotent daily scan), rq_worker, scheduler
│   ├── migrations/         Alembic (baseline + future revisions)
│   ├── tests/              47+ pytest tests
│   ├── alembic.ini · requirements*.txt · Dockerfile · run_local.py
├── mobile/                 Flutter (lib/core, lib/features, lib/data)
├── docs/                   this plan, database.md, decisions/D-00x-*.md
├── docker-compose.yml      postgres + redis (+ backend, storage — Phase 6)
├── start_ownly.bat         one-click local run (SQLite, zero setup)
└── .env.example            all required variables, no secrets
```

## 3. Database Schema

Full detail in `docs/database.md`. Tables: users, refresh_tokens,
device_tokens, notification_preferences, products (soft-delete), warranties,
documents, reminders, service_records, repairs, timeline_events,
notification_log (idempotency guard). UUID PKs everywhere; statuses computed
at read time; cascade deletes from users/products.

## 4. API Strategy (base path `/api/v1`, uniform error envelope)

```
{"error": {"code": "...", "message": "...", "details": {}}}
```

| Group | Endpoints |
|---|---|
| Auth | POST register/login/refresh/logout, GET me |
| Products | GET/POST /products, GET/PATCH/DELETE /products/{id} (filters) |
| Warranty | POST/GET /products/{id}/warranty, PATCH/DELETE /warranties/{id} |
| Documents | POST/GET /products/{id}/documents, GET /documents/{id}/download (signed) |
| Reminders | GET/POST /reminders, PATCH/DELETE /reminders/{id} |
| Timeline | GET /products/{id}/timeline |
| Service/Repairs | POST/GET /products/{id}/service-records, /repairs |
| **Today** | GET /dashboard/today (alias GET /today) — attention / upcoming / recently_added / stats |
| OCR | POST /ocr/extract — returns editable draft, **saves nothing** |
| User | PATCH /users/me, prefs, devices, GET export, DELETE account |
| Subscription | GET /subscription, POST /subscription/activate, POST /subscription/cancel |
| Notifications | GET /notifications (history, filters, pagination) |
| Admin | GET /admin/stats |

Shipped in Phase 2: subscriptions + feature gating, notification history
endpoint, `/today` alias, analytics event sink, Sentry wiring.

## 5. Development Phases

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo inspection, gap analysis, this plan | ✅ done |
| 1 | Repair backend, tests green (64/64 on SQLite **and** PostgreSQL), Alembic baseline (round-trip verified on PG), docs, git | ✅ done |
| 2 | Subscriptions/feature gating, notification history, analytics + Sentry abstractions | ✅ done |
| 3 | Mobile foundation: platform scaffolding, GoRouter + deep links, onboarding, notification prefs | ✅ done |
| 4 | Mobile features: add-product (scan/upload/manual), OCR review, documents vault, detail/timeline | pending |
| 5 | Push end-to-end: FCM registration, deep-link tap-through | pending |
| 6 | Full-stack Docker, security review, E2E, README, deployment readiness | pending |

Every phase ends with: tests run → failures fixed → decision records → docs
updated → git commit.

## 6. Dependencies

Backend core: fastapi, uvicorn, sqlalchemy 2.0, alembic, pydantic v2,
pydantic-settings, python-jose, bcrypt, python-multipart, slowapi,
email-validator, httpx, pytest. Optional (lazy-imported): pytesseract/Pillow,
google-cloud-vision, boto3, redis/rq, APScheduler, firebase-admin.

Mobile: flutter_riverpod, dio, go_router, flutter_secure_storage, intl,
image_picker, file_picker, flutter_local_notifications, permission_handler.

## 7. Security Plan

- JWT access (15 min) + rotating refresh (30 days) with token-family reuse
  detection — reuse of a rotated token revokes the entire family.
- bcrypt hashing, cost 12 (env-tunable), never reversible.
- User isolation enforced in repositories, verified by tests per resource.
- Private object storage; document access only via short-lived signed URLs.
- Rate limiting on auth endpoints; error envelope never exposes internals.
- Secrets only via environment variables; `.env.example` documents all;
  real `.env` git-ignored.

## 8. Testing Plan

- Unit (pure): TodayService classifiers — buckets, severity, date math.
- Integration: auth rotation/reuse, user isolation per resource, product
  filters, warranty conflicts, signed-URL round-trip, worker idempotency,
  OCR content-type rejection, export/account deletion.
- Run: `python _check_import.py` (SQLite) or set `TEST_DATABASE_URL` to a
  Dockerized Postgres for production-parity runs.
- Mobile (Phase 3+): controller/state tests, navigation, critical flows.
- E2E (Phase 6): signup → product → document → OCR draft → confirm →
  reminder → notification-log (extends `smoke_test.py`).

