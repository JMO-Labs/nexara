/// @file auth_service.dart
/// @brief Login, 2FA, magic link, OIDC, refresh, logout and biometric unlock.
import 'package:dio/dio.dart';
import 'package:local_auth/local_auth.dart';

import '../api/api_client.dart';

/// @brief Outcome of a password login.
class LoginResult {
  const LoginResult({this.requires2fa = false});
  final bool requires2fa;
}

/// @brief Biometric abstraction (testable wrapper over local_auth).
abstract class BiometricAuthenticator {
  Future<bool> isAvailable();
  Future<bool> authenticate(String reason);
}

class LocalAuthBiometric implements BiometricAuthenticator {
  final _a = LocalAuthentication();
  @override
  Future<bool> isAvailable() async =>
      await _a.canCheckBiometrics && await _a.isDeviceSupported();
  @override
  Future<bool> authenticate(String reason) =>
      _a.authenticate(localizedReason: reason, options: const AuthenticationOptions(biometricOnly: true));
}

class AuthService {
  AuthService({required this.api, required this.tokens, BiometricAuthenticator? biometric})
      : _bio = biometric ?? LocalAuthBiometric();
  final ApiClient api;
  final TokenStore tokens;
  final BiometricAuthenticator _bio;
  String? _twoFactorToken;

  static final _cookieRe = RegExp(r'refresh_token=([^;]+)');
  Options get _noRefresh => Options(extra: {'noRefresh': true});

  /// Stores access token and the refresh token from the Set-Cookie header.
  Future<void> _store(Response<dynamic> r) async {
    final d = r.data as Map;
    String? refresh;
    for (final c in r.headers['set-cookie'] ?? const <String>[]) {
      refresh = _cookieRe.firstMatch(c)?.group(1) ?? refresh;
    }
    await tokens.save(access: d['access_token'] as String, refresh: refresh);
  }

  /// @brief POST /auth/login. Tokens are stored unless 2FA is required.
  Future<LoginResult> login(String email, String password) async {
    final r = await api.dio.post('/auth/login',
        data: {'email': email, 'password': password}, options: _noRefresh);
    final d = r.data as Map;
    if (d['requires_2fa'] == true) {
      _twoFactorToken = d['two_factor_token'] as String?;
      return const LoginResult(requires2fa: true);
    }
    await _store(r);
    return const LoginResult();
  }

  /// @brief Completes a 2FA-pending login with a TOTP/backup code.
  Future<void> verify2FA(String code) async {
    final t = _twoFactorToken;
    if (t == null) throw StateError('No pending 2FA login');
    final r = await api.dio.post('/auth/2fa/login',
        data: {'two_factor_token': t, 'code': code}, options: _noRefresh);
    _twoFactorToken = null;
    await _store(r);
  }

  /// @brief Requests a magic link email.
  Future<void> loginMagicLink(String email) =>
      api.dio.post('/auth/magic-link/request', data: {'email': email}, options: _noRefresh);

  /// @brief Exchanges the token from a magic-link deep link for a session.
  Future<void> completeMagicLink(String token) async =>
      _store(await api.dio.get('/auth/magic-link/verify',
          queryParameters: {'token': token}, options: _noRefresh));

  /// @brief Returns the provider login URL to open in an external browser/custom tab.
  String loginOIDC(String provider) => '${api.dio.options.baseUrl}/oauth/$provider/login';

  /// @brief Exchanges the code received via deep link after OIDC login.
  Future<void> completeOIDC(String code) async => _store(await api.dio
      .post('/oauth/exchange', data: {'code': code}, options: _noRefresh));

  /// @brief Best-effort server logout, always clears local tokens.
  Future<void> logout() async {
    try {
      final rt = await tokens.readRefresh();
      await api.dio.post('/auth/logout',
          options: Options(
              headers: {if (rt != null) 'Cookie': 'refresh_token=$rt'},
              extra: {'noRefresh': true}));
    } catch (_) {
      // Server unreachable or session already invalid: still sign out locally.
    } finally {
      await tokens.clear();
    }
  }

  /// @brief Rotates tokens via the refresh cookie. Returns false (and signs out) on failure.
  Future<bool> refreshToken() async {
    final rt = await tokens.readRefresh();
    if (rt == null) return false;
    try {
      final r = await api.dio.post('/auth/refresh',
          options: Options(headers: {'Cookie': 'refresh_token=$rt'}, extra: {'noRefresh': true}));
      await _store(r);
      return true;
    } on DioException {
      await tokens.clear();
      return false;
    }
  }

  /// @brief Unlocks the app with biometrics when a session exists.
  Future<bool> biometricUnlock() async {
    if (await tokens.readRefresh() == null) return false;
    if (!await _bio.isAvailable()) return false;
    return _bio.authenticate('Unlock Nexara');
  }
}
