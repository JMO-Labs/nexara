/// @file auth_service_test.dart
/// @brief Tests login, logout, refresh, 2FA and biometric unlock.
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/api/api_client.dart';
import 'package:nexara_mobile/core/auth/auth_service.dart';

class Mem implements TokenStore {
  String? access, refresh;
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
  Future<void> clear() async => access = refresh = null;
}

class ThrowingAdapter extends Adapter {
  ThrowingAdapter() : super((_) => (200, {}, {}));
  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? c) async =>
      throw DioException.connectionError(requestOptions: o, reason: 'offline');
}

class Adapter implements HttpClientAdapter {
  Adapter(this.h);
  final (int, Object, Map<String, List<String>>) Function(RequestOptions) h;
  final seen = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? c) async {
    seen.add(o);
    final (st, b, hd) = h(o);
    return ResponseBody.fromString(jsonEncode(b), st,
        headers: {
          Headers.contentTypeHeader: ['application/json'],
          ...hd
        });
  }

  @override
  void close({bool force = false}) {}
}

const cookie = {
  'set-cookie': ['refresh_token=r1; Path=/api/v1/auth; HttpOnly']
};

(AuthService, Mem, Adapter) make(Adapter a, {bool bio = true, bool bioOk = true}) {
  final t = Mem();
  final c = ApiClient(baseUrl: 'http://x/api/v1', tokens: t, refresher: () async => false);
  c.dio.httpClientAdapter = a;
  return (
    AuthService(api: c, tokens: t, biometric: FakeBio(bio, bioOk)),
    t,
    a
  );
}

class FakeBio implements BiometricAuthenticator {
  FakeBio(this.available, this.ok);
  final bool available, ok;
  @override
  Future<bool> isAvailable() async => available;
  @override
  Future<bool> authenticate(String reason) async => ok;
}

void main() {
  test('login stores access and refresh tokens', () async {
    final (s, t, a) = make(Adapter((o) => (200, {'access_token': 'a1', 'expires_in': 900}, cookie)));
    final r = await s.login('u@x.io', 'pw');
    expect(r.requires2fa, isFalse);
    expect(t.access, 'a1');
    expect(t.refresh, 'r1');
    expect(a.seen.single.path, '/auth/login');
    expect(a.seen.single.data, {'email': 'u@x.io', 'password': 'pw'});
  });

  test('login with 2FA stores nothing, then verify2FA completes', () async {
    final (s, t, _) = make(Adapter((o) => o.path == '/auth/login'
        ? (200, {'requires_2fa': true, 'two_factor_token': 'tft'}, {})
        : (200, {'access_token': 'a2', 'expires_in': 900}, cookie)));
    final r = await s.login('u@x.io', 'pw');
    expect(r.requires2fa, isTrue);
    expect(t.access, isNull);
    await s.verify2FA('123456');
    expect(t.access, 'a2');
    expect(t.refresh, 'r1');
  });

  test('verify2FA without pending login throws', () async {
    final (s, _, _) = make(Adapter((_) => (200, {}, {})));
    expect(() => s.verify2FA('123456'), throwsStateError);
  });

  test('loginMagicLink posts email', () async {
    final (s, _, a) = make(Adapter((_) => (200, {'message': 'ok'}, {})));
    await s.loginMagicLink('u@x.io');
    expect(a.seen.single.path, '/auth/magic-link/request');
  });

  test('completeMagicLink stores tokens', () async {
    final (s, t, _) = make(Adapter((_) => (200, {'access_token': 'm', 'expires_in': 1}, cookie)));
    await s.completeMagicLink('tok');
    expect(t.access, 'm');
  });

  test('logout clears tokens even if server call fails', () async {
    final (s, t, _) = make(Adapter((_) => (500, {}, {})));
    t.access = 'a';
    t.refresh = 'r';
    await s.logout();
    expect(t.access, isNull);
    expect(t.refresh, isNull);
  });

  test('refreshToken sends cookie, saves new access, returns true', () async {
    final (s, t, a) = make(Adapter((_) => (200, {'access_token': 'n', 'expires_in': 1}, cookie)));
    t.refresh = 'r0';
    expect(await s.refreshToken(), isTrue);
    expect(a.seen.single.headers['Cookie'], 'refresh_token=r0');
    expect(t.access, 'n');
    expect(t.refresh, 'r1');
  });

  test('refreshToken false without refresh token', () async {
    final (s, _, a) = make(Adapter((_) => (200, {}, {})));
    expect(await s.refreshToken(), isFalse);
    expect(a.seen, isEmpty);
  });

  test('refreshToken false and clears tokens on failure', () async {
    final (s, t, _) = make(Adapter((_) => (401, {}, {})));
    t.refresh = 'bad';
    expect(await s.refreshToken(), isFalse);
    expect(t.refresh, isNull);
  });

  test('refreshToken keeps tokens on connection error', () async {
    final (s, t, _) = make(ThrowingAdapter());
    t.access = 'a';
    t.refresh = 'r';
    expect(await s.refreshToken(), isFalse);
    expect(t.access, 'a');
    expect(t.refresh, 'r');
  });

  test('refreshToken keeps tokens on 500', () async {
    final (s, t, _) = make(Adapter((_) => (500, {}, {})));
    t.refresh = 'r';
    expect(await s.refreshToken(), isFalse);
    expect(t.refresh, 'r');
  });

  test('loginOIDC url-encodes provider', () {
    final (s, _, _) = make(Adapter((_) => (200, {}, {})));
    expect(s.loginOIDC('a/b c'), 'http://x/api/v1/oauth/a%2Fb%20c/login');
  });

  test('biometricUnlock true only with session and successful auth', () async {
    final (s, t, _) = make(Adapter((_) => (200, {}, {})));
    expect(await s.biometricUnlock(), isFalse); // no session
    t.refresh = 'r';
    expect(await s.biometricUnlock(), isTrue);
  });

  test('biometricUnlock false when unavailable or rejected', () async {
    final (s1, t1, _) = make(Adapter((_) => (200, {}, {})), bio: false);
    t1.refresh = 'r';
    expect(await s1.biometricUnlock(), isFalse);
    final (s2, t2, _) = make(Adapter((_) => (200, {}, {})), bioOk: false);
    t2.refresh = 'r';
    expect(await s2.biometricUnlock(), isFalse);
  });
}
