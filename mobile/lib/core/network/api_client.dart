import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/constants/api_constants.dart';
import 'package:ownly/core/network/token_storage.dart';

/// Uniform API error surfaced to the UI layer.
class ApiException implements Exception {
  final String code;
  final String message;
  ApiException(this.code, this.message);

  @override
  String toString() => message;
}

/// Emitted when refresh fails and the user must log in again.
class SessionExpired {}

/// Global broadcast of session-expiry events.
class SessionEvents {
  final _controller = StreamController<SessionExpired>.broadcast();
  Stream<SessionExpired> get stream => _controller.stream;
  void emit(SessionExpired e) => _controller.add(e);
}

final sessionEventsProvider = Provider<SessionEvents>((ref) => SessionEvents());

class AuthInterceptor extends Interceptor {
  final TokenStorage _tokens;
  final Ref _ref;

  AuthInterceptor(this._tokens, this._ref);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final access = await _tokens.getAccessToken();
    if (access != null && !options.path.contains('/auth/')) {
      options.headers['Authorization'] = 'Bearer $access';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final isAuthPath = err.requestOptions.path.contains('/auth/');
    if (err.response?.statusCode == 401 && !isAuthPath) {
      final refreshed = await _tryRefresh(original: err.requestOptions);
      if (refreshed != null) {
        handler.resolve(refreshed);
        return;
      }
      await _tokens.clear();
      _ref.read(sessionEventsProvider).emit(SessionExpired());
    }
    handler.next(err);
  }

  Future<Response<dynamic>?> _tryRefresh({required RequestOptions original}) async {
    try {
      final refresh = await _tokens.getRefreshToken();
      if (refresh == null) return null;
      final dio = Dio(BaseOptions(baseUrl: ApiConstants.baseUrl));
      final resp = await dio.post('/auth/refresh', data: {'refresh_token': refresh});
      final tokens = resp.data as Map<String, dynamic>;
      await _tokens.saveTokens(
        tokens['access_token'] as String,
        tokens['refresh_token'] as String,
      );
      original.headers['Authorization'] = 'Bearer ${tokens['access_token']}';
      return await dio.fetch<dynamic>(original);
    } catch (_) {
      return null;
    }
  }
}

class ApiClient {
  final Dio dio;
  ApiClient(this.dio);

  /// Extract the API error envelope into an ApiException.
  static ApiException toError(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['error'] is Map) {
      final err = data['error'] as Map;
      return ApiException(
        (err['code'] ?? 'unknown') as String,
        (err['message'] ?? 'Something went wrong.') as String,
      );
    }
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout) {
      return ApiException('network', 'Cannot reach OWNLY servers. Check your connection.');
    }
    return ApiException('unknown', 'Something went wrong. Please try again.');
  }
}

final apiClientProvider = Provider<ApiClient>((ref) {
  final tokens = ref.watch(tokenStorageProvider);
  final dio = Dio(BaseOptions(
    baseUrl: ApiConstants.baseUrl,
    connectTimeout: ApiConstants.connectTimeout,
    receiveTimeout: ApiConstants.receiveTimeout,
  ));
  dio.interceptors.add(AuthInterceptor(tokens, ref));
  return ApiClient(dio);
});