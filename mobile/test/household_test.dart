import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/authentication/auth_controller.dart';
import 'package:ownly/features/households/household_screen.dart';

class _FakeHouseholdRepository extends HouseholdRepository {
  final List<HouseholdItem> households;
  final Map<String, HouseholdDetailItem> details;
  final List<HouseholdInviteItem> invites = [];

  _FakeHouseholdRepository({
    required this.households,
    required this.details,
  }) : super(ApiClient(Dio()));

  @override
  Future<List<HouseholdItem>> listHouseholds() async => households;

  @override
  Future<HouseholdDetailItem> getHousehold(String id) async {
    final d = details[id];
    if (d != null) return d;
    throw Exception('Household not found: $id');
  }

  @override
  Future<HouseholdItem> createHousehold(String name) async {
    final item = HouseholdItem(
      id: 'h-new',
      name: name,
      createdBy: 'u1',
      memberCount: 1,
      role: 'admin',
      createdAt: DateTime.now(),
    );
    households.add(item);
    return item;
  }

  @override
  Future<HouseholdInviteItem> createInvite(
    String householdId, {
    String role = 'member',
    int expiresInDays = 7,
  }) async {
    final inv = HouseholdInviteItem(
      id: 'inv-1',
      householdId: householdId,
      code: 'OWN-TEST-CODE',
      role: role,
      expiresAt: DateTime.now().add(Duration(days: expiresInDays)),
      createdAt: DateTime.now(),
    );
    invites.add(inv);
    return inv;
  }

  @override
  Future<HouseholdDetailItem> joinHousehold(String inviteCode) async {
    if (inviteCode == 'OWN-TEST-CODE' && households.isNotEmpty) {
      return details[households.first.id]!;
    }
    throw Exception('Invalid or expired code');
  }
}

class _FakeAuthController extends StateNotifier<AsyncValue<UserAccount?>>
    implements AuthController {
  _FakeAuthController(UserAccount? user) : super(AsyncValue.data(user));

  @override
  Future<void> login(String email, String password) async {}

  @override
  Future<void> register(String name, String email, String password) async {}

  @override
  Future<void> logout() async {}
}

void main() {
  group('Phase 8: Household Models JSON Deserialization', () {
    test('HouseholdItem deserializes correctly', () {
      final json = {
        'id': 'h-123',
        'name': 'Family Home',
        'created_by': 'u-456',
        'member_count': 3,
        'role': 'admin',
        'created_at': '2026-09-24T00:00:00.000Z',
      };
      final item = HouseholdItem.fromJson(json);
      expect(item.id, 'h-123');
      expect(item.name, 'Family Home');
      expect(item.createdBy, 'u-456');
      expect(item.memberCount, 3);
      expect(item.role, 'admin');
    });

    test('HouseholdDetailItem and members deserialize correctly', () {
      final json = {
        'id': 'h-123',
        'name': 'Family Home',
        'created_by': 'u-456',
        'role': 'admin',
        'product_count': 5,
        'created_at': '2026-09-24T00:00:00.000Z',
        'members': [
          {
            'user_id': 'u-456',
            'user_name': 'Alice Smith',
            'user_email': 'alice@example.com',
            'role': 'admin',
            'joined_at': '2026-09-24T00:00:00.000Z',
          },
          {
            'user_id': 'u-789',
            'user_name': 'Bob Smith',
            'user_email': 'bob@example.com',
            'role': 'member',
            'joined_at': '2026-09-24T01:00:00.000Z',
          },
        ],
      };
      final detail = HouseholdDetailItem.fromJson(json);
      expect(detail.id, 'h-123');
      expect(detail.productCount, 5);
      expect(detail.members.length, 2);
      expect(detail.members[0].userName, 'Alice Smith');
      expect(detail.members[1].role, 'member');
    });

    test('HouseholdInviteItem deserializes correctly', () {
      final json = {
        'id': 'inv-1',
        'household_id': 'h-123',
        'code': 'OWN-A1B2-C3D4',
        'role': 'member',
        'expires_at': '2026-10-01T00:00:00.000Z',
        'used_at': null,
        'created_at': '2026-09-24T00:00:00.000Z',
      };
      final invite = HouseholdInviteItem.fromJson(json);
      expect(invite.code, 'OWN-A1B2-C3D4');
      expect(invite.role, 'member');
      expect(invite.usedAt, isNull);
    });

    test('Product model parses household_id and is_shared correctly', () {
      final json = {
        'id': 'prod-1',
        'name': 'Coffee Maker',
        'category': 'appliances',
        'purchase_date': '2026-01-15T00:00:00.000Z',
        'currency': 'USD',
        'status': 'active',
        'return_days': 30,
        'warranty': {'status': 'active', 'days_remaining': 120},
        'return_window': {'tracked': false, 'status': 'none'},
        'created_at': '2026-01-15T00:00:00.000Z',
        'household_id': 'h-123',
        'is_shared': true,
      };
      final prod = Product.fromJson(json);
      expect(prod.householdId, 'h-123');
      expect(prod.isShared, isTrue);
    });
  });

  group('Phase 8: HouseholdScreen Widget Tests', () {
    testWidgets('Renders empty state when user has no households', (tester) async {
      final fakeRepo = _FakeHouseholdRepository(households: [], details: {});

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            householdRepositoryProvider.overrideWithValue(fakeRepo),
            authStateProvider.overrideWith((ref) => _FakeAuthController(
                  UserAccount(id: 'u-1', name: 'Alice', email: 'alice@example.com', isAdmin: false),
                )),
          ],
          child: MaterialApp(
            theme: OwnlyTheme.light(),
            home: const HouseholdScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('No Households Yet'), findsOneWidget);
      expect(find.text('Create Household'), findsOneWidget);
      expect(find.text('Join with Code'), findsOneWidget);
    });

    testWidgets('Renders household details with members and invite button', (tester) async {
      final house = HouseholdItem(
        id: 'h-1',
        name: 'The Residence',
        createdBy: 'u-1',
        memberCount: 2,
        role: 'admin',
        createdAt: DateTime(2026, 9, 20),
      );
      final detail = HouseholdDetailItem(
        id: 'h-1',
        name: 'The Residence',
        createdBy: 'u-1',
        role: 'admin',
        productCount: 4,
        createdAt: DateTime(2026, 9, 20),
        members: [
          HouseholdMemberItem(
            userId: 'u-1',
            userName: 'Alice Smith',
            userEmail: 'alice@example.com',
            role: 'admin',
            joinedAt: DateTime(2026, 9, 20),
          ),
          HouseholdMemberItem(
            userId: 'u-2',
            userName: 'Charlie Brown',
            userEmail: 'charlie@example.com',
            role: 'viewer',
            joinedAt: DateTime(2026, 9, 22),
          ),
        ],
      );

      final fakeRepo = _FakeHouseholdRepository(
        households: [house],
        details: {'h-1': detail},
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            householdRepositoryProvider.overrideWithValue(fakeRepo),
            authStateProvider.overrideWith((ref) => _FakeAuthController(
                  UserAccount(id: 'u-1', name: 'Alice Smith', email: 'alice@example.com', isAdmin: false),
                )),
          ],
          child: MaterialApp(
            theme: OwnlyTheme.light(),
            home: const HouseholdScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Check header info
      expect(find.text('The Residence'), findsOneWidget);
      expect(find.text('4 shared products · 2 members'), findsOneWidget);
      expect(find.text('Invite Member'), findsOneWidget);

      // Check member rows
      expect(find.text('Alice Smith'), findsOneWidget);
      expect(find.text('(You)'), findsOneWidget);
      expect(find.text('Charlie Brown'), findsOneWidget);
      expect(find.text('charlie@example.com'), findsOneWidget);
    });
  });
}
