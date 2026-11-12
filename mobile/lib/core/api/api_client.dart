/// @file api_client.dart
/// @brief Dio HTTP client with token injection, transparent refresh and error mapping.
import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// @brief Persistence for the JWT access token and refresh token.
abstract class TokenStore {
  Future<String?> readAccess();
  Future<String?> readRefresh();
  Future<void> save({required String access, String? refresh});
  Future<void> clear();
}

/// @brief TokenStore backed by the platform keychain / keystore.
class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? s]) : _s = s ?? const FlutterSecureStorage();
  final FlutterSecureStorage _s;
  static const _a = 'access_token';
  static const _r = 'refresh_token';

  @override
  Future<String?> readAccess() => _s.read(key: _a);
  @override
  Future<String?> readRefresh() => _s.read(key: _r);
  @override
  Future<void> save({required String access, String? refresh}) async {
    await _s.write(key: _a, value: access);
    if (refresh != null) await _s.write(key: _r, value: refresh);
  }

  @override
  Future<void> clear() async {
    await _s.delete(key: _a);
    await _s.delete(key: _r);
  }
}

/// @brief User-friendly application error mapped from an HTTP failure.
class AppError implements Exception {
  AppError(this.message, {this.code, this.status});
  final String message;
  final String? code;
  final int? status;
  @override
  String toString() => message;
}

class UnauthorizedError extends AppError {
  UnauthorizedError(super.message, {super.code}) : super(status: 401);
}

class ForbiddenError extends AppError {
  ForbiddenError(super.message, {super.code}) : super(status: 403);
}

class NotFoundError extends AppError {
  NotFoundError(super.message, {super.code}) : super(status: 404);
}

class ServerError extends AppError {
  ServerError(super.message, {super.code, super.status});
}

class NetworkError extends AppError {
  NetworkError(super.message);
}

/// @brief Maps a failed request to an AppError, using the backend error envelope if present.
AppError mapError(DioException e) {
  final status = e.response?.statusCode;
  final data = e.response?.data;
  String? msg, code;
  if (data is Map && data['error'] is Map) {
    msg = data['error']['message']?.toString();
    code = data['error']['code']?.toString();
  }
  switch (status) {
    case 401:
      return UnauthorizedError(msg ?? 'Please sign in again.', code: code);
    case 403:
      return ForbiddenError(msg ?? 'You do not have permission to do that.', code: code);
    case 404:
      return NotFoundError(msg ?? 'We could not find what you asked for.', code: code);
    case final s? when s >= 500:
      return ServerError(msg ?? 'Something went wrong on our side. Try again later.',
          code: code, status: s);
    case null:
      return NetworkError('Cannot reach the server. Check your connection.');
  }
  return AppError(msg ?? 'Request failed. Please try again.', code: code, status: status);
}

/// @brief Injects `Authorization: Bearer <access>` when a token exists.
class TokenInterceptor extends Interceptor {
  TokenInterceptor(this._tokens);
  final TokenStore _tokens;

  @override
  Future<void> onRequest(RequestOptions o, RequestInterceptorHandler h) async {
    final t = await _tokens.readAccess();
    if (t != null && t.isNotEmpty) o.headers['Authorization'] = 'Bearer $t';
    h.next(o);
  }
}

/// @brief On 401 refreshes the token (single-flight) and retries the request once.
class RefreshInterceptor extends Interceptor {
  RefreshInterceptor(this._dio, this._refresher);
  final Dio _dio;
  final Future<bool> Function() _refresher;
  Future<bool>? _inflight;
  static const _retried = 'retried';

  @override
  Future<void> onError(DioException e, ErrorInterceptorHandler h) async {
    final o = e.requestOptions;
    if (e.response?.statusCode != 401 || o.extra[_retried] == true || o.extra['noRefresh'] == true) {
      return h.next(e);
    }
    final ok = await (_inflight ??= _refresher().whenComplete(() => _inflight = null));
    if (!ok) return h.next(e);
    o.extra[_retried] = true;
    o.headers.remove('Authorization'); // re-injected by TokenInterceptor
    try {
      h.resolve(await _dio.fetch(o));
    } on DioException catch (err) {
      h.next(err);
    }
  }
}

/// @brief Maps failures to AppError (stored in DioException.error).
class ErrorMapInterceptor extends Interceptor {
  @override
  void onError(DioException e, ErrorInterceptorHandler h) {
    if (e.error is AppError) return h.next(e);
    h.next(e.copyWith(error: mapError(e)));
  }
}

/// @brief Configured Dio wrapper. Interceptor order: token, refresh, error map.
class ApiClient {
  ApiClient({
    required String baseUrl,
    required TokenStore tokens,
    required Future<bool> Function() refresher,
    Duration timeout = const Duration(seconds: 15),
  }) : dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: timeout,
          receiveTimeout: timeout,
          sendTimeout: timeout,
        )) {
    dio.interceptors.addAll([
      TokenInterceptor(tokens),
      RefreshInterceptor(dio, refresher),
      ErrorMapInterceptor(),
    ]);
  }
  final Dio dio;
}
