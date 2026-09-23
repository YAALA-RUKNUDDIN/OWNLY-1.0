# D-010: Push Notification Lifecycle & Deep-Link Dispatch

**Status:** Accepted · **Date:** 2026-09-24 · **Phase:** 5

## Context

OWNLY notifies users about critical post-purchase milestones: warranty expiration
notices (90d, 30d, 7d, 1d, 0d), closing return windows, and scheduled service
or custom reminders. In Phase 2, backend notification history and idempotency
guards were established in `notification_log`. In Phase 3 and 4, the mobile
app established `ownly://` deep-link URL scheme handlers and GoRouter redirect
gates. Phase 5 requires closing the loop: end-to-end device token registration,
push payload delivery with deep-link metadata, local notification display, and
tap-through routing on foreground, background, and cold start.

## Decision

- **Provider-Agnostic Push Architecture:**
  - Backend: `PushProvider` abstraction (`base.py`, `noop.py`, `fcm.py`).
    In local development, CI, and environments without Google service account
    credentials, `PUSH_PROVIDER=noop` logs payload deliveries and tracks events.
    In production, `PUSH_PROVIDER=fcm` sends HTTP v1 messages with high priority.
  - Client: `NotificationService` encapsulates `FlutterLocalNotificationsPlugin`,
    configuring high-importance notification channel `ownly_alerts` on Android
    and native sound/alert presentation on iOS.
- **Device Token Lifecycle:**
  - Token persistence: Stable client device tokens are persisted securely in
    `TokenStorage` (Keystore / Keychain).
  - Registration: Upon user login or session restoration (`/auth/me`),
    `AuthController` calls `NotificationService.registerDeviceToken()`, which
    sends `POST /users/me/devices`.
  - Reassignment: If a device token is re-registered by a different user
    (e.g. device transfer or account switch), the backend reassigns the token
    to the active user rather than failing.
  - Unregistration: When a user logs out (`/auth/logout`), the device token is
    unregistered via `DELETE /users/me/devices/{fcm_token}`. Invalid tokens
    reported by FCM during dispatch are automatically purged.
- **Enriched Notification Payload Contract:**
  - Backend worker jobs (`run_daily_scan`) and test dispatch endpoints pass
    structured metadata in the push `data` payload:
    ```json
    {
      "route": "/products/<product_id>",
      "deep_link": "ownly:///products/<product_id>",
      "product_id": "<product_id>",
      "subject_type": "warranty|return|reminder|test",
      "subject_id": "<subject_id>"
    }
    ```
- **Uniform Deep-Link Tap-Through:**
  - `NotificationPayload.parse()` normalizes both JSON payloads and schemed
    deep links (`ownly:///...`, `/products/...`).
  - Active/Foreground: `NotificationService.onNotificationTapped` notifies
    `routerProvider`, which calls `router.go(payload.route)` without losing
    navigation history or state.
  - Cold Start: `NotificationService.getNotificationAppLaunchDetails()` stores
    the launch payload. When the onboarding and session redirect gates resolve
    successfully, GoRouter dispatches directly to the destination screen.
- **Testability & Manual Verification:**
  - Added `POST /notifications/test` for authenticated users to send a test
    push to their registered devices with custom title, body, and route.
  - Added a "Send test notification" button in `NotificationHistoryScreen`
    allowing instantaneous local and backend verification on physical devices
    and emulators.

## Alternatives Considered

| Option | Verdict |
|---|---|
| Hardcode Firebase Messaging SDK directly without fallback | Rejected: would crash builds and tests when running locally or in environments lacking `google-services.json` |
| Route notification taps via imperative Navigator pushes | Rejected: breaks GoRouter's single source of truth and causes gate race conditions |
| Separate deep-link routes for push notifications | Rejected: unified with `ownly://` route table (D-009) to avoid code duplication |

## Consequences

- Full notification loop functions out-of-the-box in zero-configuration local
  setups as well as full FCM cloud deployments.
- Notifications deep-link directly into product details, reminders, and history
  with zero route flashes.
- Users can test and verify push notifications directly from the UI.
