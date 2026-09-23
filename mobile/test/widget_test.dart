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
import 'package:ownly/features/notifications/notification_history_screen.dart';
import 'package:ownly/features/products/repairs_tab.dart';
import 'package:ownly/features/profile/data_export_screen.dart';
import 'package:ownly/features/subscription/subscription_screen.dart';

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

  @override
  Future<SubscriptionInfo> subscription() async => SubscriptionInfo(
        tier: 'premium',
        status: 'active',
        provider: 'manual',
        expiresAt: DateTime(2030, 1, 1),
        features: const ['ocr', 'data_export'],
        usedProducts: 3,
      );

  @override
  Future<NotificationPage> notifications({
    String? category,
    int page = 1,
    int pageSize = 20,
  }) async =>
      NotificationPage(
        items: [
          NotificationItem(
            id: 'n1',
            category: 'warranty',
            subjectType: 'warranty',
            subjectId: 's1',
            milestone: '30_days',
            dueDate: DateTime(2026, 10, 1),
            title: 'Warranty ending soon',
            body: 'Your vacuum warranty ends in 30 days.',
            deliveryStatus: 'sent',
            sentAt: DateTime(2026, 9, 1),
          ),
        ],
        total: 42,
        page: page,
        pageSize: pageSize,
      );

  @override
  Future<List<RepairEntry>> repairs(String productId) async => [
        RepairEntry(
          id: 'r1',
          productId: productId,
          repairDate: DateTime(2026, 8, 1),
          description: 'Replaced battery',
          provider: 'FixIt',
          cost: 49.99,
        ),
      ];

  @override
  Future<Map<String, dynamic>> exportData() async => {
        'products': [1, 2],
        'documents': [1],
        'user': {'id': 'u1'},
      };

  @override
  Future<void> registerDevice(String fcmToken, {String platform = 'unknown'}) async {}

  @override
  Future<void> unregisterDevice(String fcmToken) async {}

  @override
  Future<Map<String, dynamic>> sendTestNotification({
    String title = 'OWNLY Test Alert',
    String body = 'This is a test notification from OWNLY.',
    String route = '/today',
    String? deepLink,
  }) async =>
      {
        'message': 'Test notification dispatched.',
        'recipient_count': 1,
        'tokens': ['mock_token'],
        'route': route,
        'deep_link': deepLink ?? 'ownly://$route',
      };
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

  testWidgets('SubscriptionScreen shows plan, usage and cancel action',
      (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(_FakeRepository())],
      child: const MaterialApp(home: SubscriptionScreen()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Subscription'), findsOneWidget);
    expect(find.text('Premium'), findsOneWidget);
    expect(find.textContaining('3 products used'), findsOneWidget);
    expect(find.text('Cancel plan'), findsOneWidget);
  });

  testWidgets('NotificationHistoryScreen lists history entries',
      (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(_FakeRepository())],
      child: const MaterialApp(home: NotificationHistoryScreen()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Notification history'), findsOneWidget);
    expect(find.text('Warranty ending soon'), findsOneWidget);
    // Load-more shows paging progress against the server-side total.
    expect(find.textContaining('of 42'), findsOneWidget);
  });

  testWidgets('DataExportScreen summarizes export sections', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(_FakeRepository())],
      child: const MaterialApp(home: DataExportScreen()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Export my data'), findsOneWidget);
    expect(find.text('products'), findsOneWidget);
    expect(find.text('2 items'), findsOneWidget);
  });

  testWidgets('RepairsTab lists repair history with add action', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(_FakeRepository())],
      child: const MaterialApp(
        home: Scaffold(body: RepairsTab(productId: 'p1')),
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Replaced battery'), findsOneWidget);
    expect(find.text('Add repair'), findsOneWidget);
    expect(find.textContaining('FixIt'), findsOneWidget);
  });
}