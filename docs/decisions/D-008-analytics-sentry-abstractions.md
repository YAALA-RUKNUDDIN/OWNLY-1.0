# D-008: Analytics and Error-Tracking as Swappable, Fail-Open Integrations

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 2

## Context

Phase 2 needed product telemetry (funnel: signup → product → document → OCR →
Today) and error visibility for production, without committing to a vendor or
adding a hard dependency that could take the API down.

## Decision

- **Analytics is a provider abstraction** (`app/integrations/analytics/`),
  mirroring the existing OCR/storage/push layout: a tiny ABC, concrete
  providers (`log`, `noop`), and a settings-selected factory
  (`ANALYTICS_PROVIDER`). A vendor (PostHog/Amplitude) later = one new file
  plus one factory branch; call sites do not change.
- **Event names are a frozen, additive catalog**
  (`app/core/analytics_events.py::AnalyticsEvent`). Renaming is forbidden;
  additions only. Call sites pass the enum member, never a raw string.
- **`track()` is fail-open**: it wraps provider invocation in try/except and
  logs-and-drops on failure. Analytics can never turn a successful user action
  into a 500. This is enforced by a unit test that monkeypatches a provider
  which raises.
- **Sentry is opt-in by configuration only** (`SENTRY_DSN` empty = disabled,
  the default) and imports lazily: if `sentry-sdk` is not installed the
  backend logs a warning and continues. `send_default_pii=False` because
  OWNLY's promise is privacy-first — no user document data or identifiers
  leave the system by default. Traces sampling defaults to `0.0`.
- **Initial event set** (kept deliberately small and high-signal):
  `user_registered`, `user_logged_in`, `product_added`, `product_deleted`,
  `document_uploaded`, `ocr_extracted`, `today_viewed`,
  `subscription_activated`, `subscription_canceled`, `notification_sent`,
  plus `warranty_added`, `reminder_created`, `export_requested`,
  `account_deleted` reserved for the endpoints that own them.

## Alternatives Considered

| Option | Verdict |
|---|---|
| Call a vendor SDK directly in endpoints | Rejected: vendor lock-in inside business logic; a SDK outage becomes our outage |
| Queue events in the DB and ship via worker | Deferred: correct at scale, but adds a table + job before there is volume; the provider interface makes this a later swap |
| Sentry as a hard dependency | Rejected: a missing/broken SDK must not prevent startup |
| Log-only analytics forever | Rejected: no funnel product would ship without a real sink; the abstraction keeps that door open |

## Consequences

- Local development logs one structured JSON line per event (`ANALYTICS_PROVIDER=log`),
  so the funnel is inspectable without any external service.
- Tests run with the `noop` provider when set, and always assert the fail-open
  contract; a broken sink is invisible to users by design.
- Error tracking is one env var away in production and cannot fail silently:
  setting `SENTRY_DSN` without the SDK installed produces an explicit warning.
- Privacy review stays simple: only internal UUIDs and coarse properties
  (category, milestone, mime type) are attached to events.
