import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/core/network/token_storage.dart';
import 'package:ownly/data/models.dart';

/// Repository for auth + products + documents + reminders + dashboard.
class OwnlyRepository {
  final ApiClient api;
  final TokenStorage tokens;
  OwnlyRepository(this.api, this.tokens);

  // ── Auth ────────────────────────────────────────────────────
  Future<UserAccount> register(String name, String email, String password) async {
    try {
      final resp = await api.dio.post('/auth/register', data: {
        'name': name, 'email': email, 'password': password,
      });
      final body = resp.data as Map<String, dynamic>;
      await tokens.saveTokens(
        body['tokens']['access_token'] as String,
        body['tokens']['refresh_token'] as String,
      );
      return UserAccount.fromJson(body['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<UserAccount> login(String email, String password) async {
    try {
      final resp = await api.dio.post('/auth/login', data: {
        'email': email, 'password': password,
      });
      final body = resp.data as Map<String, dynamic>;
      await tokens.saveTokens(
        body['tokens']['access_token'] as String,
        body['tokens']['refresh_token'] as String,
      );
      return UserAccount.fromJson(body['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<void> logout() async {
    try {
      final refresh = await tokens.getRefreshToken();
      if (refresh != null) {
        await api.dio.post('/auth/logout', data: {'refresh_token': refresh});
      }
    } catch (_) {/* best effort */}
    await tokens.clear();
  }

  // ── Dashboard ───────────────────────────────────────────────
  Future<TodayDashboard> today() async {
    try {
      final resp = await api.dio.get('/dashboard/today');
      return TodayDashboard.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  // ── Products ────────────────────────────────────────────────
  Future<List<Product>> products({
    String? search, String? category, String? status,
    String? warrantyStatus, int? purchaseYear,
  }) async {
    try {
      final resp = await api.dio.get('/products', queryParameters: {
        if (search != null && search.isNotEmpty) 'search': search,
        if (category != null && category.isNotEmpty) 'category': category,
        if (status != null && status.isNotEmpty) 'status': status,
        if (warrantyStatus != null && warrantyStatus.isNotEmpty) 'warranty_status': warrantyStatus,
        if (purchaseYear != null) 'purchase_year': purchaseYear,
        'page_size': 100,
      });
      final items = (resp.data['items'] as List).cast<Map<String, dynamic>>();
      return items.map(Product.fromJson).toList();
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<Product> product(String id) async {
    try {
      final resp = await api.dio.get('/products/$id');
      return Product.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<Product> createProduct(Map<String, dynamic> body) async {
    try {
      final resp = await api.dio.post('/products', data: body);
      return Product.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<void> deleteProduct(String id) async {
    try {
      await api.dio.delete('/products/$id');
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  // ── Warranty / repairs / service / reminders ────────────────
  Future<void> addWarranty(String productId, Map<String, dynamic> body) async {
    try {
      await api.dio.post('/products/$productId/warranty', data: body);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<void> addRepair(String productId, Map<String, dynamic> body) async {
    try {
      await api.dio.post('/products/$productId/repairs', data: body);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<List<RepairEntry>> repairs(String productId) async {
    try {
      final resp = await api.dio.get('/products/$productId/repairs');
      return (resp.data as List)
          .cast<Map<String, dynamic>>()
          .map(RepairEntry.fromJson)
          .toList();
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<void> addServiceRecord(String productId, Map<String, dynamic> body) async {
    try {
      await api.dio.post('/products/$productId/service-records', data: body);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<List<ReminderItem>> reminders({String? status}) async {
    try {
      final resp = await api.dio.get('/reminders', queryParameters: {
        if (status != null) 'status': status,
      });
      return (resp.data as List).cast<Map<String, dynamic>>().map(ReminderItem.fromJson).toList();
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<void> updateReminder(String id, Map<String, dynamic> body) async {
    try {
      await api.dio.patch('/reminders/$id', data: body);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  // ── Timeline & documents ────────────────────────────────────
  Future<List<TimelineEvent>> timeline(String productId) async {
    try {
      final resp = await api.dio.get('/products/$productId/timeline');
      final events = (resp.data['events'] as List).cast<Map<String, dynamic>>();
      return events.map(TimelineEvent.fromJson).toList();
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<List<DocumentFile>> documents(String productId) async {
    try {
      final resp = await api.dio.get('/products/$productId/documents');
      return (resp.data as List).cast<Map<String, dynamic>>().map(DocumentFile.fromJson).toList();
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<DocumentFile> uploadDocument(
      String productId, String filePath, String name, String type) async {
    try {
      final form = FormData.fromMap({
        'document_name': name,
        'document_type': type,
        'file': await MultipartFile.fromFile(filePath),
      });
      final resp = await api.dio.post('/products/$productId/documents', data: form);
      return DocumentFile.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<String> documentDownloadUrl(String documentId) async {
    try {
      final resp = await api.dio.get('/documents/$documentId/download');
      final url = resp.data['download_url'] as String;
      // Local-storage URLs are API-relative; S3 URLs are absolute.
      if (url.startsWith('/')) {
        final base = api.dio.options.baseUrl.substring(0, api.dio.options.baseUrl.indexOf('/api'));
        return '$base$url';
      }
      return url;
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  // ── OCR ─────────────────────────────────────────────────────
  Future<OcrDraft> ocrExtract(String imagePath) async {
    try {
      final form = FormData.fromMap({
        'file': await MultipartFile.fromFile(imagePath),
      });
      final resp = await api.dio.post('/ocr/extract', data: form);
      return OcrDraft.fromJson((resp.data['draft'] ?? {}) as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  // ── Account ─────────────────────────────────────────────────
  // ── Notification preferences ────────────────────────────────
  Future<List<NotificationPref>> notificationPrefs() async {
    try {
      final resp = await api.dio.get('/users/me/prefs');
      return _parsePrefs(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<List<NotificationPref>> updateNotificationPref(
    String category, {
    required bool enabled,
    required List<int> leadDays,
  }) async {
    try {
      final resp = await api.dio.patch('/users/me/prefs', data: {
        category: {'enabled': enabled, 'lead_days': leadDays},
      });
      return _parsePrefs(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  static List<NotificationPref> _parsePrefs(Map<String, dynamic> body) =>
      ((body['preferences'] ?? const <dynamic>[]) as List)
          .cast<Map<String, dynamic>>()
          .map(NotificationPref.fromJson)
          .toList();

  // ── Subscription ────────────────────────────────────────────────────────
  Future<SubscriptionInfo> subscription() async {
    try {
      final resp = await api.dio.get('/subscription');
      return SubscriptionInfo.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  /// Dev/manual activation — store-receipt verification replaces this (D-007).
  Future<SubscriptionInfo> activateSubscription(
      {int months = 12, String? providerRef}) async {
    try {
      final resp = await api.dio.post('/subscription/activate', data: {
        'months': months,
        if (providerRef != null) 'provider_ref': providerRef,
      });
      return SubscriptionInfo.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<SubscriptionInfo> cancelSubscription() async {
    try {
      final resp = await api.dio.post('/subscription/cancel');
      return SubscriptionInfo.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  // ── Notification history ────────────────────────────────────────────────
  Future<NotificationPage> notifications({
    String? category,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final resp = await api.dio.get('/notifications', queryParameters: {
        if (category != null && category.isNotEmpty) 'category': category,
        'page': page,
        'page_size': pageSize,
      });
      return NotificationPage.fromJson(resp.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<Map<String, dynamic>> exportData() async {
    try {
      final resp = await api.dio.get('/users/me/export');
      return resp.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }

  Future<void> deleteAccount() async {
    try {
      await api.dio.delete('/users/me');
      await tokens.clear();
    } on DioException catch (e) {
      throw ApiClient.toError(e);
    }
  }
}

final repositoryProvider = Provider<OwnlyRepository>(
  (ref) => OwnlyRepository(ref.watch(apiClientProvider), ref.watch(tokenStorageProvider)),
);