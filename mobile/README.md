# OWNLY mobile (Flutter)

Flutter client for the OWNLY Phase-2 FastAPI backend.

## Layout

- `lib/core/` — theme, HTTP (`api_client.dart` + JWT refresh interceptor), secure
  token storage, route constants, `router/` (single GoRouter).
- `lib/data/` — `models.dart` (mirrors of the backend contracts),
  `repositories.dart` (every HTTP call lives here).
- `lib/features/` — one folder per feature: Riverpod controllers + screens.
- `test/` — widget/router tests against a fake repository (no network).

## Run

1. Start the backend: `start_ownly.bat` (or `uvicorn app.main:app --app-dir backend`)
   → `http://127.0.0.1:8000`.
2. API base URL defaults to `http://10.0.2.2:8000/api/v1` (Android emulator → host).
   Override per machine:
   `flutter run --dart-define=OWNLY_API_URL=http://<host>:8000/api/v1`
3. `flutter pub get && flutter run`

## Verify

```powershell
flutter analyze   # 0 issues
flutter test      # 6/6 — dashboard, login validation, onboarding gate, session gate, formatter
```

## Navigation & deep links

Single GoRouter (`lib/core/router/ownly_router.dart`) with two redirect gates:

1. **Onboarding** — first run shows `/onboarding` until "Get started"
   (persisted in SharedPreferences); the session gate never applies there.
2. **Session** — `/login` when logged out; the redirect *holds* while `/auth/me`
   restores, so signed-in users never see a login flash and the login form
   keeps its submitting state on errors.

Tabs use `StatefulShellRoute.indexedStack` (per-branch state preserved). Deep
links use the `ownly://` scheme (`ownly:///products/<id>`, …): Android
intent-filter and iOS URL types are wired; Phase 5 notification taps route
through the same table.

## Notification preferences

Profile → Notifications loads `GET /users/me/prefs` and persists each toggle
via `PATCH /users/me/prefs` (categories: `warranty`, `return_window`,
`service`, `custom`).
