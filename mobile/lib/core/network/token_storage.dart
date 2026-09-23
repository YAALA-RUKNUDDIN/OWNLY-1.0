import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure token persistence (Keychain / Keystore via flutter_secure_storage).
class TokenStorage {
  static const _accessKey = 'ownly_access_token';
  static const _refreshKey = 'ownly_refresh_token';

  final FlutterSecureStorage _storage;

  TokenStorage(this._storage);

  Future<String?> getAccessToken() =>
      _storage.read(key: _accessKey);

  Future<String?> getRefreshToken() =>
      _storage.read(key: _refreshKey);

  Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  // ── Device token (Phase 5) ───────────────────────────────────
  static const _deviceTokenKey = 'ownly_device_token';

  Future<String> getOrCreateDeviceToken() async {
    final existing = await _storage.read(key: _deviceTokenKey);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final newToken =
        'dev_token_${DateTime.now().millisecondsSinceEpoch}_${(1000 + (DateTime.now().microsecond % 9000))}';
    await _storage.write(key: _deviceTokenKey, value: newToken);
    return newToken;
  }
}

final tokenStorageProvider = Provider<TokenStorage>(
  (ref) => TokenStorage(const FlutterSecureStorage()),
);