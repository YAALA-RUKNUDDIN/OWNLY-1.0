# OWNLY

> **"What do I need to do about the things I own today?"**
>
> A privacy-first, post-purchase digital ownership assistant. OWNLY remembers what consumers forget after buying a product: expiring warranties, closing return windows, invoices, service schedules, maintenance alerts, and repairs.

---

## 🌟 Key Highlights & Capabilities

- **Daily Attention Dashboard ("Today"):** Urgency-ranked post-purchase feed surfacing actions that matter now (action items, upcoming events within 30 days, recent purchases, and aggregate portfolio value).
- **Document & Receipt Vault:** Multi-format document uploads (PDF, PNG, JPEG, WebP) stored in isolated object storage and served exclusively via short-lived, HMAC-signed download URLs.
- **Warranty & Return Tracker:** Continuous, computed-at-read time lifecycle tracking (no stale dates) supporting manufacturer, extended, store, and third-party warranties.
- **Receipt OCR Draft Pipeline:** Image receipt text extraction with pre-filled product draft generation. Extracted data is always presented as an editable draft—**nothing auto-saves without user consent**.
- **Push Notifications & Deep Linking:** End-to-end device token registration (`POST /users/me/devices`), background worker scheduling, and notification tap-through routing directly to the target product or reminder (`ownly:///products/{id}`).
- **Cross-Platform Flutter Mobile Client:** State-of-the-art mobile experience built with Flutter 3.x, Riverpod state management, GoRouter declarative navigation, offline-tolerant HTTP client with automatic token refreshing, and responsive design adhering to the slate/emerald design system.
- **Household & Family Sharing:** Multi-user shared vaults with role-based access control (`admin`, `member`, `viewer`), time-bound invite code generation (`OWN-XXXX-XXXX`), and safe unlinking cascades that preserve personal product vaults.
- **Honest Monetization:** Tiered subscription enforcement (Free tier capped at 10 items; Unlimited Premium) evaluated strictly server-side.
- **Data Sovereignty & Privacy-First:** Full GDPR-grade data export (`GET /users/me/export`) and irreversible account deletion (`DELETE /users/me`) that cascades across all database records and storage files.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   OWNLY Flutter Mobile Application                     │
│    (Riverpod State Management, GoRouter, Secure Storage, Local Push)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS + JWT (15-min Access / 30-day Rotating Refresh)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       FastAPI Modular Monolith                         │
│                                                                        │
│  API Layer (app/api/*)          Strict route handlers & validation      │
│  Service Layer (app/services/*) Business logic, Today engine, warranty │
│  Repository Layer (app/repos/*) Database queries with user_id scoping  │
│  Integrations (app/integrations) Provider abstractions                 │
│    ├── OCR Engine               Tesseract (Local) / Google Cloud Vision │
│    ├── Storage Engine           Local Filesystem (HMAC) / S3 / R2       │
│    └── Push Engine              No-Op (Dev/CI) / Firebase Cloud Push    │
│  Worker Layer (app/workers/*)   Daily scan, scheduler & RQ background   │
└───────────────────┬───────────────────────────────┬────────────────────┘
                    │                               │
                    ▼                               ▼
       ┌────────────────────────┐      ┌────────────────────────┐
       │     PostgreSQL 16      │      │        Redis 7         │
       │  (Alembic Migrations)  │      │  (Job Queue & Locking) │
       └────────────────────────┘      └────────────────────────┘
```

---

## 🚀 Quickstart Options

### Option 1: Full-Stack Docker Compose (Recommended for Production / Staging)

Boot the entire stack (PostgreSQL, Redis, FastAPI backend with Alembic migrations, and background scheduler) with a single command:

```bash
# From the repository root
docker compose up -d
```

Verify services are healthy:
```bash
docker compose ps
```

- **API Base:** `http://localhost:8000`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`
- **Postgres:** `localhost:5433` (mapped from container 5432 to prevent host port conflicts)
- **Redis:** `localhost:6379`

To stop all services:
```bash
docker compose down
```

---

### Option 2: One-Click Local Launcher (Zero Setup / SQLite)

If you don't have Docker installed, you can run locally with SQLite:

1. **Double-click `start_ownly.bat`** (Windows) in the root directory.
2. The script provisions a virtual environment, installs dependencies, and boots the API at `http://localhost:8000`.
3. To stop, run `stop_ownly.bat` or close the server terminal window.

---

### Option 3: Manual Backend Setup

```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements-local.txt
python run_local.py
```

---

## 📱 Mobile App Setup (Flutter)

The mobile client is built with Flutter 3.x and supports iOS and Android.

### Prerequisites
- [Flutter SDK](https://docs.flutter.dev/get-started/install) (3.24+ recommended)
- Android Studio / Xcode

### Running the App
```bash
cd mobile
flutter pub get

# Run on connected device or emulator (defaults to http://10.0.2.2:8000/api/v1 for Android emulator)
flutter run

# To target a local physical device on the same Wi-Fi:
flutter run --dart-define=OWNLY_API_URL=http://<YOUR_LOCAL_IP>:8000/api/v1
```

### Deep-Link Scheme
The mobile application registers and handles the `ownly://` URL scheme:
- `ownly:///products/{id}` → Opens specific product details and document vault
- `ownly:///today` → Opens the Today attention screen
- `ownly:///notifications` → Opens notification history

---

## 📖 API Reference

Base path: `/api/v1`. All endpoints return standard HTTP status codes and a uniform error envelope on failure:

```json
{
  "error": {
    "code": "not_found",
    "message": "Product not found.",
    "details": {}
  }
}
```

| Domain | Method & Endpoint | Description |
|---|---|---|
| **Auth** | `POST /auth/register` | Register new user account; returns access + refresh tokens |
| | `POST /auth/login` | Authenticate with email & password |
| | `POST /auth/refresh` | Refresh access token with token-family reuse detection |
| | `POST /auth/logout` | Revoke refresh token and terminate session |
| | `GET /auth/me` | Fetch authenticated user profile |
| **Products** | `GET /products` | List user products (search, categories, warranty status, pagination) |
| | `POST /products` | Create a new product (validates categories & return window) |
| | `GET /products/{id}` | Get product details with computed return & warranty status |
| | `PATCH /products/{id}` | Update product attributes |
| | `DELETE /products/{id}` | Soft-delete product (frees subscription quota) |
| **Warranties** | `POST /products/{id}/warranty` | Create warranty (supports duration in months or explicit date) |
| | `GET /products/{id}/warranty` | Get current warranty status |
| | `PATCH /warranties/{id}` | Extend or update warranty details |
| | `DELETE /warranties/{id}` | Remove warranty from product |
| **Documents** | `POST /products/{id}/documents` | Upload invoice/receipt (PDF, JPEG, PNG, WebP) |
| | `GET /products/{id}/documents` | List documents attached to product |
| | `GET /documents/{id}/download` | Generate short-lived HMAC-signed download URL |
| | `PATCH /documents/{id}` | Rename document |
| | `DELETE /documents/{id}` | Delete document and remove physical file from storage |
| **Reminders** | `POST /reminders` | Schedule reminder (service due, warranty expiry, custom) |
| | `GET /reminders` | List upcoming reminders |
| | `PATCH /reminders/{id}` | Update or dismiss reminder |
| | `DELETE /reminders/{id}` | Delete reminder |
| **Timeline** | `GET /products/{id}/timeline` | Retrieve chronological audit trail of product events |
| **Repairs** | `POST /products/{id}/repairs` | Log repair history with cost and service provider |
| | `GET /products/{id}/repairs` | List repairs for product |
| **Today** | `GET /dashboard/today` | Fetch urgency feed (attention items, upcoming, recent, stats) |
| | `GET /today` | Alias matching `/dashboard/today` |
| **OCR** | `POST /ocr/extract` | Extract invoice draft from image without saving to database |
| **Devices** | `POST /users/me/devices` | Register FCM push device token |
| | `DELETE /users/me/devices/{token}` | Unregister device token |
| **Notifications** | `POST /notifications/test` | Dispatch test push notification with deep-link metadata |
| | `GET /notifications` | Paginated notification history with category filters |
| **Households** | `GET /households` | List caller's households |
| | `POST /households` | Create a new household vault |
| | `GET /households/{id}` | Detailed household view with member list and roles |
| | `PATCH /households/{id}` | Rename household (admin only) |
| | `DELETE /households/{id}` | Delete household and safely unlink products (admin only) |
| | `POST /households/{id}/invites` | Generate invite code with role & expiration (admin only) |
| | `GET /households/{id}/invites` | List active invite codes (admin only) |
| | `POST /households/join` | Join household via 12-char invite code |
| | `DELETE /households/{id}/members/{user_id}` | Remove member (admin or self) |
| | `POST /products/{id}/share` | Share product with household vault or revert to personal |
| **Preferences** | `GET /users/me/prefs` | Get notification lead-time and category preferences |
| | `PATCH /users/me/prefs` | Update notification preferences |
| **Subscription** | `GET /subscription` | Current tier, usage count, and product limit |
| | `POST /subscription/activate` | Activate premium subscription |
| | `POST /subscription/cancel` | Cancel subscription (entitlement retained until period end) |
| **Privacy** | `GET /users/me/export` | Full GDPR data export (JSON bundle of all user data) |
| | `DELETE /users/me` | Permanent account deletion cascading all files and records |

---

## 🔒 Security & Data Privacy

1. **Strict Multi-Tenant Isolation:** Repositories mandate `user_id` filtering on every query. Cross-tenant access attempts return HTTP 404 Not Found to prevent resource enumeration.
2. **Cryptographic Token Family Revocation:** Refresh tokens use single-use rotation. If an already-rotated token is presented (potential token theft), the entire refresh token family is invalidated immediately.
3. **Signed Download URLs:** Documents are stored in private storage. Downloads are mediated by HMAC-SHA256 signatures with 10-minute expiry timestamps. Expired or tampered signatures are rejected with HTTP 401 Unauthorized.
4. **Permanent Right to Erasure:** Deleting an account initiates a cascading purge: product records, warranties, reminders, notifications, and physical files from object storage are permanently deleted.
5. **Safe RBAC & Cascade Unlinking:** Household vaults distinguish `admin`, `member`, and `viewer` roles. Deleting a household automatically resets `Product.household_id` to `NULL`, returning shared items to their owner's personal vault without data loss.

---

## 🧪 Testing & Quality Assurance

### Test Suite Execution

#### Backend Pytest Suite
Run the full test suite (132 tests covering auth, security, user isolation, warranty math, today urgency, push notifications, cloud integrations, household sharing & RBAC, and full end-to-end journey):

```bash
cd backend
# With virtual environment activated:
pytest -v
```

#### Household Sharing & RBAC Suite
```bash
pytest tests/test_households.py -v
```

#### End-to-End User Journey & Security Suite
```bash
pytest tests/test_e2e_journey.py -v
```

#### Production Cloud Integrations Suite
```bash
pytest tests/test_cloud_integrations.py -v
```

#### Flutter Mobile Test Suite
Run component, state, and widget tests:

```bash
cd mobile
flutter test
flutter analyze
```

#### Live Smoke Test
Verify against a live running backend server (checks 20 distinct API endpoints):

```bash
cd backend
python smoke_test.py http://localhost:8000/api/v1
```

---

## 📋 Definition of Done Verification Matrix

| Area | Requirement | Status | Verification Evidence |
|---|---|---|---|
| **Architecture** | FastAPI modular monolith + Flutter mobile client | ✅ Complete | Clean separation: `api/` → `services/` → `repositories/` |
| **Database** | PostgreSQL 16 + Alembic migrations + UUID PKs | ✅ Complete | Migrations verified round-trip (`upgrade head` / `downgrade base`) |
| **Authentication** | JWT access + rotating refresh with family revocation | ✅ Complete | Verified in `test_auth.py` and `test_e2e_journey.py` |
| **Ownership Core** | Product catalog + Return windows + Warranty tracking | ✅ Complete | Read-time computation tested in `test_warranty.py` |
| **Document Vault** | Private storage + HMAC-signed expiring URLs | ✅ Complete | Path traversal & signature tampering verified in `test_e2e_journey.py` |
| **OCR Pipeline** | Receipt extraction returning non-persisting draft | ✅ Complete | Verified in `test_e2e_journey.py` (saves nothing automatically) |
| **Notifications** | Push dispatch + device lifecycle + deep linking | ✅ Complete | Verified in `test_push.py` and mobile `notification_test.dart` |
| **Mobile App** | Riverpod + GoRouter + Responsive UI + Offline handling | ✅ Complete | 24 mobile tests green, 0 `flutter analyze` issues |
| **Household Sharing** | Multi-user vaults, RBAC (admin/member/viewer), invite codes | ✅ Complete | 6 tests in `test_households.py`, 6 tests in `household_test.dart` |
| **Containerization** | Docker Compose orchestration with healthchecks | ✅ Complete | Root `docker-compose.yml` validated with persistent volumes |
| **Cloud Integrations** | AWS S3/R2, Google Vision OCR dual auth, FCM HTTP v1 | ✅ Complete | 18 integration tests passing in `test_cloud_integrations.py` |
| **Documentation** | Production README + Architecture Decision Records | ✅ Complete | ADRs D-001 through D-013 recorded in `docs/decisions/` |