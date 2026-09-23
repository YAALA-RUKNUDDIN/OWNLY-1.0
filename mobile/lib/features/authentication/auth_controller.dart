import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

class AuthController extends StateNotifier<AsyncValue<UserAccount?>> {
  final OwnlyRepository _repo;
  StreamSubscription<SessionExpired>? _sub;

  AuthController(this._repo, SessionEvents sessionEvents)
      : super(const AsyncValue.loading()) {
    _restore();
    _sub = sessionEvents.stream.listen((_) async {
      // Access + refresh both dead → back to login.
      await _repo.logout();
      state = const AsyncValue.data(null);
    });
  }

  Future<void> _restore() async {
    try {
      final resp = await _repo.api.dio.get('/auth/me');
      state = AsyncValue.data(UserAccount.fromJson(resp.data as Map<String, dynamic>));
    } catch (_) {
      state = const AsyncValue.data(null);
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final user = await _repo.login(email, password);
      state = AsyncValue.data(user);
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
    } on ApiException catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }

  Future<void> logout() async {
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
  ),
);