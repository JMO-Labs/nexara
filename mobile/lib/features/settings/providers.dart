/// @file providers.dart
/// @brief Providers for settings API and biometric unlock preference.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_service.dart';
import '../../core/providers.dart';
import '../../core/storage/local_storage.dart';
import 'settings_api.dart';

/// @brief Biometric unlock preference (device-local).
abstract class BiometricSettings {
  Future<bool> isAvailable();
  Future<bool> isEnabled();

  /// @return resulting enabled state (enabling requires a successful prompt).
  Future<bool> setEnabled(bool value);
}

class AuthBiometricSettings implements BiometricSettings {
  AuthBiometricSettings(this._auth, this._store);
  final AuthService _auth;
  final LocalStorage _store;
  static const _key = 'biometric_enabled';

  @override
  Future<bool> isAvailable() => _auth.biometricAvailable();
  @override
  Future<bool> isEnabled() async => (await _store.get(_key)) == true;
  @override
  Future<bool> setEnabled(bool value) async {
    if (value && !await _auth.biometricConfirm()) return false;
    await _store.cache(_key, value);
    return value;
  }
}

final settingsApiProvider =
    Provider<SettingsApi>((ref) => HttpSettingsApi(ref.watch(apiClientProvider)));

final biometricSettingsProvider = Provider<BiometricSettings>((ref) =>
    AuthBiometricSettings(ref.watch(authServiceProvider), ref.watch(localStorageProvider)));
