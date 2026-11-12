/// @file api_client_test.dart
/// @brief Tests auth header injection, 401 refresh+retry and error mapping.
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/api/api_client.dart';

/// Scripted adapter: handler gets the request and returns (status, body).
class FakeAdapter implements HttpClientAdapter {
  FakeAdapter(this.handler);
  final (int, Object?) Function(RequestOptions) handler;
  final List<RequestOptions> seen = [];

  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s,
      Future<void>? c) async {
    seen.add(o);
    final (status, body) = handler(o);
    return ResponseBody.fromString(jsonEncode(body ?? {}), status,
        headers: {
          Headers.contentTypeHeader: ['application/json']
        });
  }

  @override
  void close({bool force = false}) {}
}

class MemTokens implements TokenStore {
  String? access;
  String? refresh;
  @override
  Future<String?> readAccess() async => access;
  @override
  Future<String?> readRefresh() async => refresh;
  @override
  Future<void> save({required String access, String? refresh}) async {
    this.access = access;
    if (refresh != null) this.refresh = refresh;
  }

  @override
  Future<void> clear() async {
    access = null;
    refresh = null;
  }
}

ApiClient build(FakeAdapter a, MemTokens t,
    {Future<bool> Function()? refresher}) {
  final c = ApiClient(
      baseUrl: 'http://x/api/v1', tokens: t, refresher: refresher ?? () async => false);
  c.dio.httpClientAdapter = a;
  return c;
}

void main() {
  test('injects bearer token', () async {
    final t = MemTokens()..access = 'abc';
    final a = FakeAdapter((_) => (200, {'ok': true}));
    await build(a, t).dio.get('/me');
    expect(a.seen.single.headers['Authorization'], 'Bearer abc');
  });

  test('no header when no token', () async {
    final a = FakeAdapter((_) => (200, {}));
    await build(a, MemTokens()).dio.get('/me');
    expect(a.seen.single.headers.containsKey('Authorization'), isFalse);
  });

  test('refreshes on 401 and retries once with new token', () async {
    final t = MemTokens()..access = 'old';
    final a = FakeAdapter((o) =>
        o.headers['Authorization'] == 'Bearer new' ? (200, {'ok': 1}) : (401, {}));
    final c = build(a, t, refresher: () async {
      t.access = 'new';
      return true;
    });
    final r = await c.dio.get('/me');
    expect(r.statusCode, 200);
    expect(a.seen.length, 2);
  });

  test('does not loop when retry still 401', () async {
    final t = MemTokens()..access = 'old';
    final a = FakeAdapter((_) => (401, {}));
    final c = build(a, t, refresher: () async => true);
    await expectLater(c.dio.get('/me'),
        throwsA(isA<DioException>().having((e) => e.error, 'error', isA<UnauthorizedError>())));
    expect(a.seen.length, 2);
  });

  test('failed refresh surfaces UnauthorizedError', () async {
    final a = FakeAdapter((_) => (401, {}));
    await expectLater(build(a, MemTokens()..access = 'x').dio.get('/me'),
        throwsA(isA<DioException>().having((e) => e.error, 'error', isA<UnauthorizedError>())));
  });

  for (final c in <(int, Type)>[
    (403, ForbiddenError),
    (404, NotFoundError),
    (500, ServerError),
    (503, ServerError),
  ]) {
    test('maps ${c.$1} to ${c.$2}', () async {
      final a = FakeAdapter((_) => (c.$1, {
            'error': {'code': 'X', 'message': 'Nope'}
          }));
      try {
        await build(a, MemTokens()).dio.get('/z');
        fail('should throw');
      } on DioException catch (e) {
        expect(e.error.runtimeType, c.$2);
        expect((e.error as AppError).message, 'Nope');
      }
    });
  }

  test('uses friendly message when body has no envelope', () async {
    final a = FakeAdapter((_) => (500, null));
    try {
      await build(a, MemTokens()).dio.get('/z');
      fail('should throw');
    } on DioException catch (e) {
      expect((e.error as AppError).message, isNot(contains('500')));
    }
  });
}
