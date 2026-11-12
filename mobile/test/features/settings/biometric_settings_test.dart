/// @file biometric_settings_test.dart
/// @brief Unit tests for AuthBiometricSettings delegating to AuthService.
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/api/api_client.dart';
import 'package:nexara_mobile/core/auth/auth_service.dart';
import 'package:nexara_mobile/features/settings/providers.dart';

class _Tokens implements TokenStore {
  @override
  Future<String?> readAccess() async => null;
  @override
  Future<String?> readRefresh() async => 'r';
  @override
  Future<void> save({required String access, String? refresh}) async {}
  @override
  Future<void> clear() async {}
}

class _Pref implements BiometricPrefStore {
  _Pref(this.value);
  bool value;
  @override
  Future<bool> read() async => value;
  @override
  Future<void> write(bool v) async => value = v;
}

class _Bio implements BiometricAuthenticator {
  _Bio(this.ok);
  final bool ok;
  int prompts = 0;
  @override
  Future<bool> isAvailable() async => true;
  @override
  Future<bool> authenticate(String reason) async {
    prompts++;
    return ok;
  }
}

(AuthBiometricSettings, AuthService, _Bio, _Pref) make({bool ok = true, bool enabled = false}) {
  final t = _Tokens();
  final bio = _Bio(ok);
  final pref = _Pref(enabled);
  final auth = AuthService(
      api: ApiClient(baseUrl: 'http://x', tokens: t, refresher: () async => false),
      tokens: t,
      biometric: bio,
      biometricPref: pref);
  return (AuthBiometricSettings(auth), auth, bio, pref);
}

void main() {
  test('enabling with failed prompt leaves it disabled', () async {
    final (s, auth, bio, _) = make(ok: false);
    expect(await s.setEnabled(true), isFalse);
    expect(await s.isEnabled(), isFalse);
    expect(bio.prompts, 1);
    expect(await auth.biometricUnlock(), isFalse);
  });

  test('enabling with successful prompt enables unlock', () async {
    final (s, auth, _, pref) = make();
    expect(await s.setEnabled(true), isTrue);
    expect(pref.value, isTrue);
    expect(await auth.biometricUnlock(), isTrue);
  });

  test('disabling skips the prompt and turns unlock off', () async {
    final (s, auth, bio, _) = make(enabled: true);
    expect(await s.setEnabled(false), isFalse);
    expect(bio.prompts, 0);
    expect(await s.isEnabled(), isFalse);
    expect(await auth.biometricUnlock(), isFalse);
    expect(bio.prompts, 0);
  });
}
