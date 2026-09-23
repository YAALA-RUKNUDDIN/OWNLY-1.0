# D-009: One Stable GoRouter with Declarative Redirect Gates

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 3

## Context

The mobile app needs onboarding, an auth gate, tab navigation and `ownly://`
deep links (also the landing point for Phase 5 notification taps). The first
draft watched Riverpod state directly inside the router provider — every
auth/onboarding change would recreate the `GoRouter`, resetting the back stack
and flashing intermediate screens during cold start and login.

## Decision

- **Single `GoRouter` instance** created once in `routerProvider`
  (`mobile/lib/core/router/ownly_router.dart`), consumed via
  `MaterialApp.router`. State changes re-run `redirect` through
  `refreshListenable` (a `ChangeNotifier` fed by `ref.listen` on
  `authStateProvider` + `onboardingDoneProvider`) — the router object and its
  navigation state survive login/logout.
- **Two ordered redirect gates, each holding while unresolved:**
  1. Onboarding (SharedPreferences-backed `AsyncNotifier`): first run →
     `/onboarding`; while the flag is loading, redirect returns `null` (cold
     start resolves in milliseconds). A prefs read *failure* is treated as
     onboarded so the user can never be trapped.
  2. Session (`authStateProvider`): logged out → `/login`, but only *outside*
     `/onboarding` (the explainer is public) and while `/auth/me` is in flight
     the redirect holds — no login flash for signed-in users, and the login
     form keeps its submitting/error state.
- **Tabs are a `StatefulShellRoute.indexedStack`** (`HomeShell`): each branch
  keeps its own stack and scroll state; re-tapping the active tab pops to the
  branch root.
- **Deep links are declared at the platform edge only** — Android
  `intent-filter` (`ownly` scheme) and iOS `CFBundleURLTypes` — and land in the
  same route table as in-app navigation; no separate link-handling path.
- **Tests drive the real router** with a fake repository and
  `SharedPreferences.setMockInitialValues`: first-run → onboarding → login,
  returning user → login, dashboard render, login validation.

## Alternatives Considered

| Option | Verdict |
|---|---|
| `ref.watch` auth/onboarding inside `routerProvider` | Rejected: recreates `GoRouter` per state change — loses back stack, causes route flashes |
| Imperative `Navigator.push` for gates (conditional `home:`) | Rejected: deep links and tab branches would need parallel hand-rolled handling |
| Splash screen until both gates resolve | Deferred: `refreshListenable` holding already removes visible flashes; a splash can be added later without touching the route table |
| App Links / Universal Links (https domain) | Deferred: requires owning a domain + assetlinks/ASA; custom `ownly://` scheme ships now, same route table |

## Consequences

- Cold start, first run, login, logout and notification tap-through all flow
  through one route table — Phase 5 only adds an FCM token + payload parse.
- Gate logic is unit-tested as navigation outcomes (which screen is shown),
  not as conditionals, so regressions surface as failing widget tests.
- Adding a screen = one `GoRoute` + (if tabbed) one branch; no shell edits.
- When a domain is available, App Links can be added beside the custom scheme
  without changing any Dart code beyond accepting `https` hosts.