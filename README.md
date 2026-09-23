# OWNLY

> **What do I need to do about the things I own today?**
>
> A privacy-first digital ownership assistant. OWNLY remembers what consumers forget after buying a product: warranties, return windows, invoices, service schedules, and repairs.

---

## 🚀 Run it right now (no Docker, no setup)

**Double-click `start_ownly.bat`** (in this folder). Then open:

- **API:** http://localhost:8000
- **Interactive docs:** http://localhost:8000/docs ← try every feature here

First run creates the Python environment automatically (~1 minute); every run
after that starts in ~5 seconds. Your data lives in `backend/ownly_local.db`
(SQLite) and survives restarts.

**Stop:** close the server window, or run `stop_ownly.bat`.

### Trying the API (2 minutes)

1. Open http://localhost:8000/docs
2. `POST /api/v1/auth/register` → "Try it out" → name/email/password → Execute
3. Copy the `access_token` from the response
4. Click **Authorize** (top right) → paste the token
5. Now use `POST /products`, `POST /products/{id}/warranty`,
   `GET /dashboard/today`, and everything else.

---

## Architecture

```
Flutter App (Android/iOS, Riverpod)
        │  HTTPS + JWT (access 15 min / rotating refresh 30 days)
        ▼
FastAPI Backend (modular monolith)
  ├── SQLite (local zero-setup)  │  PostgreSQL 16 (production, SQLAlchemy + Alembic)
  ├── Storage layer  (Local signed-URL mode │ S3 / R2 / MinIO)
  ├── OCR layer      (Tesseract local │ Google Cloud Vision)
  └── Push layer     (No-op dev │ Firebase Cloud Messaging)
```

Key guarantees:
- **User isolation** — every repository query is scoped by `user_id`; tested for products, warranties, documents, reminders, and timelines.
- **Computed, never stale** — warranty/return status is derived from dates at read time.
- **No duplicate notifications** — `notification_log` unique constraint makes the daily scan idempotent.
- **OCR is a draft** — extraction is returned for user review/editing; nothing auto-saves.
- **Privacy-first** — private storage + signed URLs, full data export, permanent account & document deletion.

## Manual start (backend)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt
python run_local.py          # → http://localhost:8000  (SQLite, zero setup)
```

`run_local.py` accepts `--check` to verify the installation. All settings are
environment variables (see `.env.example`) — for production point
`DATABASE_URL` at PostgreSQL and set a strong `JWT_SECRET`.

## Docker (production path)

```bash
cd backend
docker compose up -d          # PostgreSQL + Redis
docker build -t ownly-backend .
docker run -d --name ownly-api --network backend_default -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg2://ownly:ownly_secret@postgres:5432/ownly \
  ownly-backend
python -m app.workers.scheduler   # daily notification worker (needs Redis)
```

## Tests

Backend: 62 pytest tests (auth rotation/reuse detection, user isolation,
warranty boundary math, dashboard, documents signed-URL round-trip, export,
account deletion, worker idempotency). Run with PostgreSQL available:

```bash
pytest
```

## Mobile app (Flutter)

1. Install the [Flutter SDK](https://docs.flutter.dev/get-started/install/windows).
2. `cd mobile && flutter pub get`
3. Android emulator reaches this API by default (`http://10.0.2.2:8000/api/v1`).
   Physical device: `flutter run --dart-define=OWNLY_API_URL=http://<YOUR_PC_IP>:8000/api/v1`

## API overview

Base path `/api/v1`. Uniform error envelope:
```json
{"error": {"code": "not_found", "message": "Product not found.", "details": {}}}
```

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me` |
| Products | `GET/POST /products`, `GET/PATCH/DELETE /products/{id}` (search, category, status, warranty_status, purchase_year filters) |
| Warranty | `POST/GET /products/{id}/warranty`, `PATCH/DELETE /warranties/{id}` |
| Documents | `POST/GET /products/{id}/documents`, `GET /documents/{id}/download`, `PATCH/DELETE /documents/{id}` |
| Repairs/Service | `POST/GET /products/{id}/repairs`, `POST/GET /products/{id}/service-records` |
| Timeline | `GET /products/{id}/timeline` |
| Reminders | `GET/POST /reminders`, `PATCH/DELETE /reminders/{id}` |
| Today | `GET /dashboard/today` — attention / upcoming / recently added / stats |
| OCR | `POST /ocr/extract` — returns editable draft, saves nothing |
| User | `PATCH /users/me`, `GET/PATCH /users/me/prefs`, `POST /users/me/devices`, `GET /users/me/export`, `DELETE /users/me` |
| Admin | `GET /admin/stats` (admin-only aggregate stats) |

## Verification status (re-executed 2026-09-23, this machine)

- ✅ **`pytest`: 63/63 passed** (SQLite runner: `backend/_check_import.py`). Covers auth
  rotation + reuse detection, user isolation, warranty boundary math, documents
  signed-URL round-trip, export, account deletion, worker idempotency, and 16 new
  unit tests for the TodayService classifiers (buckets, severity, date math).
- ✅ **Live server boot verified**: `uvicorn app.main:app` → `/health` returns
  `{"status":"ok","app":"OWNLY"}`; live register → create product →
  `GET /dashboard/today` flow executed successfully.
- ✅ **Alembic baseline migration** (`migrations/versions/5c72b958547c_baseline.py`)
  verified: `upgrade head → downgrade base → upgrade head` round-trip passes.
- ✅ **Import audit**: every module under `app/` imports cleanly (SQLite mode).
- ⚠ Flutter codebase requires the Flutter SDK (not installed on this machine) to
  build/run — platform scaffolding is scheduled for Phase 3.
- 🐳 Docker daemon was unavailable during this run; PostgreSQL-parity test runs
  (`TEST_DATABASE_URL=...`) should be executed when Docker is available.

## Roadmap (designed-for, not yet built)

- Email invoice import, retailer integrations, automatic warranty detection
- Family/household sharing
- Insurance document intelligence