import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/core/network/token_storage.dart';
import 'package:ownly/core/router/ownly_router.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/authentication/login_screen.dart';
import 'package:ownly/features/authentication/onboarding_screen.dart';
import 'package:ownly/features/dashboard/today_screen.dart';

/// Repository stub — widget tests must never hit the backend.
/// (Constructing ApiClient/TokenStorage is side-effect free; no platform
/// channels are touched because every network method is overridden.)
class _FakeRepository extends OwnlyRepository {
  _FakeRepository()
      : super(ApiClient(Dio()), TokenStorage(const FlutterSecureStorage()));

  @override
  Future<TodayDashboard> today() async => TodayDashboard(
        greeting: 'Good morning',
        attention: const [],
        upcoming: const [],
        recentlyAdded: const [],
        stats: DashboardStats(
          totalProducts: 3,
          activeWarranties: 2,
          expiringWarranties: 1,
          documentsStored: 5,
        ),
      );

  @override
  Future<List<Product>> products({
    String? search,
    String? category,
    String? status,
    String? warrantyStatus,
    int? purchaseYear,
  }) async =>
      const [];

  @override
  Future<List<ReminderItem>> reminders({String? status}) async => const [];

  @override
  Future<List<NotificationPref>> notificationPrefs() async => const [];
}

/// Real router + fake repository: exercises onboarding/auth gates end-to-end.
class _TestApp extends ConsumerWidget {
  const _TestApp();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      theme: OwnlyTheme.light(),
      routerConfig: ref.watch(routerProvider),
    );
  }
}

Widget _appUnderTest({List<Override> overrides = const []}) => ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(_FakeRepository()), ...overrides],
      child: const _TestApp(),
    );

void main() {
  testWidgets('TodayScreen renders stats for a loaded dashboard', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(_FakeRepository())],
      child: MaterialApp(
        theme: OwnlyTheme.light(),
        home: const TodayScreen(),
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Products'), findsWidgets);
    expect(find.text('Good morning 👋'), findsOneWidget);
  });

  testWidgets('LoginScreen validates empty fields', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: LoginScreen())),
    );
    await tester.tap(find.byType(FilledButton));
    await tester.pump();
    expect(find.textContaining('Please enter'), findsWidgets);
  });

  testWidgets('First run routes to onboarding before anything else',
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(_appUnderTest());
    await tester.pumpAndSettle();
    expect(find.byType(OnboardingScreen), findsOneWidget);
    expect(find.text('Get started'), findsOneWidget);
  });

  testWidgets('Completing onboarding continues to the login gate',
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(_appUnderTest());
    await tester.pumpAndSettle();
    expect(find.byType(OnboardingScreen), findsOneWidget);

    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    // No session in tests → the auth gate takes over.
    expect(find.byType(LoginScreen), findsOneWidget);
  });

  testWidgets('Returning user without a session lands on login',
      (tester) async {
    SharedPreferences.setMockInitialValues({'ownly_onboarding_done': true});
    await tester.pumpWidget(_appUnderTest());
    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);
  });

  test('daysRemaining formatter', () {
    expect(Formatters.daysRemaining(0), 'today');
    expect(Formatters.daysRemaining(1), 'tomorrow');
    expect(Formatters.daysRemaining(7), 'in 7 days');
    expect(Formatters.daysRemaining(-2), '2 days ago');
  });
}