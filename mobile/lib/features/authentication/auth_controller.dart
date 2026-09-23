import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/core/notifications/notification_service.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

class AuthController extends StateNotifier<AsyncValue<UserAccount?>> {
  final OwnlyRepository _repo;
  final NotificationService? _notifs;
  StreamSubscription<SessionExpired>? _sub;

  AuthController(this._repo, SessionEvents sessionEvents, [this._notifs])
      : super(const AsyncValue.loading()) {
    _restore();
    _sub = sessionEvents.stream.listen((_) async {
      // Access + refresh both dead → back to login.
      await _notifs?.unregisterDeviceToken(_repo);
      await _repo.logout();
      state = const AsyncValue.data(null);
    });
  }

  Future<void> _restore() async {
    try {
      final resp = await _repo.api.dio.get('/auth/me');
      final user = UserAccount.fromJson(resp.data as Map<String, dynamic>);
      state = AsyncValue.data(user);
      unawaited(_notifs?.registerDeviceToken(_repo));
    } catch (_) {
      state = const AsyncValue.data(null);
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final user = await _repo.login(email, password);
      state = AsyncValue.data(user);
      unawaited(_notifs?.registerDeviceToken(_repo));
    } on ApiException catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }

  Future<void> register(String name, String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final user = await _repo.register(name, email, password);
      state = AsyncValue.data(user);
      unawaited(_notifs?.registerDeviceToken(_repo));
    } on ApiException catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }

  Future<void> logout() async {
    await _notifs?.unregisterDeviceToken(_repo);
    await _repo.logout();
    state = const AsyncValue.data(null);
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

/// Auth session state: null when logged out.
final authStateProvider = StateNotifierProvider<AuthController, AsyncValue<UserAccount?>>(
  (ref) => AuthController(
    ref.watch(repositoryProvider),
    ref.watch(sessionEventsProvider),
    ref.watch(notificationServiceProvider),
  ),
);