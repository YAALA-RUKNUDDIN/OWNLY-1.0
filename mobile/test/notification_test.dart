import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:ownly/core/constants/api_constants.dart';
import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/core/network/token_storage.dart';
import 'package:ownly/core/notifications/notification_payload.dart';
import 'package:ownly/core/notifications/notification_service.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/notifications/notification_history_screen.dart';

class _RecordingRepository extends OwnlyRepository {
  final List<String> registeredTokens = [];
  final List<String> unregisteredTokens = [];
  int testNotificationCalls = 0;

  _RecordingRepository()
      : super(ApiClient(Dio()), TokenStorage(const FlutterSecureStorage()));

  @override
  Future<TodayDashboard> today() async => TodayDashboard(
        greeting: 'Good morning',
        attention: const [],
        upcoming: const [],
        recentlyAdded: const [],
        stats: DashboardStats(
          totalProducts: 1,
          activeWarranties: 1,
          expiringWarranties: 0,
          documentsStored: 1,
        ),
      );

  @override
  Future<List<Product>> products({
    String? search,
    String? category,
    String? status,
    String? warrantyStatus,
    int? purchaseYear,
    String? scope,
  }) async =>
      const [];

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
            subjectId: 'prod-456',
            milestone: '30d',
            dueDate: DateTime(2026, 12, 1),
            title: 'Warranty reminder',
            body: 'Expires soon',
            deliveryStatus: 'sent',
            sentAt: DateTime(2026, 9, 20),
          ),
        ],
        total: 1,
        page: page,
        pageSize: pageSize,
      );

  @override
  Future<void> registerDevice(String fcmToken, {String platform = 'unknown'}) async {
    registeredTokens.add(fcmToken);
  }

  @override
  Future<void> unregisterDevice(String fcmToken) async {
    unregisteredTokens.add(fcmToken);
  }

  @override
  Future<Map<String, dynamic>> sendTestNotification({
    String title = 'OWNLY Test Alert',
    String body = 'This is a test notification from OWNLY.',
    String route = '/today',
    String? deepLink,
  }) async {
    testNotificationCalls++;
    return {
      'message': 'Test notification dispatched.',
      'recipient_count': 1,
      'tokens': ['mock_token'],
      'route': route,
      'deep_link': deepLink ?? 'ownly://$route',
    };
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('NotificationPayload Parser', () {
    test('parses empty and null strings to default today route', () {
      final p1 = NotificationPayload.parse(null);
      expect(p1.route, OwnlyRoutes.today);

      final p2 = NotificationPayload.parse('');
      expect(p2.route, OwnlyRoutes.today);

      final p3 = NotificationPayload.parse('   ');
      expect(p3.route, OwnlyRoutes.today);
    });

    test('normalizes schemed deep links with triple and double slashes', () {
      final p1 = NotificationPayload.parse('ownly:///products/p-123');
      expect(p1.route, '/products/p-123');
      expect(p1.deepLink, 'ownly:///products/p-123');

      final p2 = NotificationPayload.parse('ownly://reminders');
      expect(p2.route, '/reminders');

      final p3 = NotificationPayload.parse('ownly:///dashboard');
      expect(p3.route, OwnlyRoutes.today);
    });

    test('parses plain relative routes', () {
      final p1 = NotificationPayload.parse('/products/456');
      expect(p1.route, '/products/456');

      final p2 = NotificationPayload.parse('products/456');
      expect(p2.route, '/products/456');
    });

    test('parses JSON payloads with deep link, route, and subject metadata', () {
      const jsonStr = '''
      {
        "route": "/products/drone-99",
        "deep_link": "ownly:///products/drone-99",
        "title": "Drone Warranty",
        "body": "Warranty expires today",
        "subject_type": "warranty",
        "subject_id": "war-001",
        "product_id": "drone-99"
      }
      ''';
      final p = NotificationPayload.parse(jsonStr);
      expect(p.route, '/products/drone-99');
      expect(p.deepLink, 'ownly:///products/drone-99');
      expect(p.title, 'Drone Warranty');
      expect(p.body, 'Warranty expires today');
      expect(p.subjectType, 'warranty');
      expect(p.subjectId, 'war-001');
      expect(p.productId, 'drone-99');
    });

    test('parses JSON fallback using product_id when route is omitted', () {
      const jsonStr = '{"product_id": "prod-xyz", "subject_type": "return"}';
      final p = NotificationPayload.parse(jsonStr);
      expect(p.route, '/products/prod-xyz');
      expect(p.productId, 'prod-xyz');
      expect(p.subjectType, 'return');
    });
  });

  group('NotificationService lifecycle', () {
    test('registers and unregisters device token with repository', () async {
      FlutterSecureStorage.setMockInitialValues({});
      final tokenStorage = TokenStorage(const FlutterSecureStorage());
      final service = NotificationService(tokenStorage: tokenStorage);
      final repo = _RecordingRepository();

      await service.registerDeviceToken(repo);
      expect(repo.registeredTokens.length, 1);
      final token = repo.registeredTokens.first;
      expect(token, startsWith('dev_token_'));

      await service.unregisterDeviceToken(repo);
      expect(repo.unregisteredTokens.length, 1);
      expect(repo.unregisteredTokens.first, token);

      service.dispose();
    });

    test('cold start launch payload consumption is one-shot', () {
      FlutterSecureStorage.setMockInitialValues({});
      final service = NotificationService(
        tokenStorage: TokenStorage(const FlutterSecureStorage()),
      );

      expect(service.consumeLaunchPayload(), isNull);
      service.dispose();
    });
  });

  group('Notification tap-through navigation', () {
    testWidgets('NotificationHistoryScreen dispatches test notification',
        (tester) async {
      SharedPreferences.setMockInitialValues({'ownly_onboarding_done': true});
      FlutterSecureStorage.setMockInitialValues({});

      final repo = _RecordingRepository();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            repositoryProvider.overrideWithValue(repo),
          ],
          child: MaterialApp(
            theme: OwnlyTheme.light(),
            home: const NotificationHistoryScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.text('Notification history'), findsOneWidget);
      expect(find.text('Warranty reminder'), findsOneWidget);

      // Tap test notification action in app bar
      final testButton = find.byTooltip('Send test notification');
      expect(testButton, findsOneWidget);
      await tester.tap(testButton);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.textContaining('Test notification dispatched'), findsOneWidget);
      expect(repo.testNotificationCalls, 1);
    });
  });
}
