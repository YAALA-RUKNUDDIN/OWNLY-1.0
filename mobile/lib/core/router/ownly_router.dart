import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:ownly/core/constants/api_constants.dart';
import 'package:ownly/core/notifications/notification_service.dart';
import 'package:ownly/features/authentication/auth_controller.dart';
import 'package:ownly/features/authentication/login_screen.dart';
import 'package:ownly/features/authentication/onboarding_screen.dart';
import 'package:ownly/features/dashboard/today_screen.dart';
import 'package:ownly/features/households/household_screen.dart';
import 'package:ownly/features/notifications/notification_history_screen.dart';
import 'package:ownly/features/products/add_product_screen.dart';
import 'package:ownly/features/products/product_detail_screen.dart';
import 'package:ownly/features/products/products_screen.dart';
import 'package:ownly/features/profile/data_export_screen.dart';
import 'package:ownly/features/profile/profile_screen.dart';
import 'package:ownly/features/reminders/reminders_screen.dart';
import 'package:ownly/features/shell/home_shell.dart';
import 'package:ownly/features/subscription/subscription_screen.dart';
import 'package:ownly/features/claims/claims_screen.dart';
import 'package:ownly/features/claims/claim_detail_screen.dart';

/// Global navigator key for notification tap-through and dialogs outside BuildContext.
final rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');

/// Re-runs `GoRouter.redirect` whenever auth or onboarding state changes.
/// Using `refreshListenable` (instead of `ref.watch` inside the provider)
/// keeps one stable router instance, so navigation state — current branch,
/// back stack — survives login/logout instead of resetting to the root.
class _GateRefresh extends ChangeNotifier {
  _GateRefresh(Ref ref) {
    ref.listen(authStateProvider, (_, __) => notifyListeners());
    ref.listen(onboardingDoneProvider, (_, __) => notifyListeners());
  }
}

/// OWNLY router: single source of truth for navigation + deep links.
///
/// Routes:
/// - `/onboarding` — first-run explainer (gated until completed).
/// - `/today` — primary dashboard (default location).
/// - `/products`, `/products/:id`, `/add`, `/reminders`, `/profile` — tabs.
/// - `/login` — authentication entry (gated when logged out).
///
/// Redirect gates, in order:
/// 1. Onboarding flag still loading → hold current screen (cold-start ms).
/// 2. Not onboarded → `/onboarding`; completing it → `/today`.
/// 3. Session (`/auth/me`) still restoring → hold, so signed-in users never
///    see a login flash and LoginScreen keeps its submitting state.
/// 4. Logged out → `/login`; logged in while on `/login` → `/today`.
/// 5. Cold-start notification launch → target deep-link route (Phase 5).
///
/// Deep links use the `ownly://` scheme, e.g. `ownly:///products/<id>`
/// (Android intent-filter / iOS URL types — notification taps in Phase 5
/// route through the same table).
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _GateRefresh(ref);

  final router = GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: OwnlyRoutes.today,
    refreshListenable: refresh,
    redirect: (context, state) {
      final onboarding = ref.read(onboardingDoneProvider);
      final auth = ref.read(authStateProvider);
      final location = state.matchedLocation;
      final onOnboarding = location == OwnlyRoutes.onboarding;
      final onLogin = location == OwnlyRoutes.login;

      // Gate 1 — first run. While the flag resolves, hold the current screen.
      if (!onboarding.hasValue && !onboarding.hasError) return null;
      // Prefs read failure → treat as onboarded so the user is never trapped.
      final onboarded = onboarding.valueOrNull ?? true;
      if (!onboarded && !onOnboarding) return OwnlyRoutes.onboarding;
      if (onboarded && onOnboarding) return OwnlyRoutes.today;

      // Gate 2 — session. Onboarding is public: while on it, don't gate.
      if (onOnboarding) return null;
      // While /auth/me is in flight, hold.
      if (!auth.hasValue && !auth.hasError) return null;
      final signedIn = auth.valueOrNull != null;
      if (!signedIn && !onLogin) return OwnlyRoutes.login;
      if (signedIn && onLogin) return OwnlyRoutes.today;

      // Gate 3 — Cold-start notification launch dispatch (Phase 5).
      if (signedIn && location == OwnlyRoutes.today) {
        final launch =
            ref.read(notificationServiceProvider).consumeLaunchPayload();
        if (launch != null && launch.route != OwnlyRoutes.today) {
          return launch.route;
        }
      }

      return null;
    },
    routes: [
      GoRoute(
        path: OwnlyRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: OwnlyRoutes.login,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: OwnlyRoutes.subscription,
        builder: (context, state) => const SubscriptionScreen(),
      ),
      GoRoute(
        path: OwnlyRoutes.notifications,
        builder: (context, state) => const NotificationHistoryScreen(),
      ),
      GoRoute(
        path: OwnlyRoutes.dataExport,
        builder: (context, state) => const DataExportScreen(),
      ),
      GoRoute(
        path: OwnlyRoutes.households,
        builder: (context, state) => const HouseholdScreen(),
      ),
      GoRoute(
        path: OwnlyRoutes.claims,
        builder: (context, state) => const ClaimsScreen(),
      ),
      GoRoute(
        path: '/claims/:id',
        builder: (context, state) => ClaimDetailScreen(
          claimId: state.pathParameters['id']!,
        ),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => HomeShell(shell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(
              path: OwnlyRoutes.today,
              builder: (context, state) => const TodayScreen(),
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: OwnlyRoutes.products,
              builder: (context, state) => const ProductsScreen(),
              routes: [
                GoRoute(
                  path: ':id',
                  builder: (context, state) => ProductDetailScreen(
                    productId: state.pathParameters['id']!,
                  ),
                ),
              ],
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: OwnlyRoutes.addProduct,
              builder: (context, state) => const AddProductScreen(),
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: OwnlyRoutes.reminders,
              builder: (context, state) => const RemindersScreen(),
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: OwnlyRoutes.profile,
              builder: (context, state) => const ProfileScreen(),
            ),
          ]),
        ],
      ),
    ],
  );

  final notifSub = ref.read(notificationServiceProvider).onNotificationTapped.listen((payload) {
    final auth = ref.read(authStateProvider);
    if (auth.valueOrNull != null) {
      router.go(payload.route);
    }
  });

  ref.onDispose(notifSub.cancel);
  ref.onDispose(router.dispose);
  ref.onDispose(refresh.dispose);
  return router;
});
