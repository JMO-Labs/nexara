/// @file providers.dart
/// @brief Providers for settings API and biometric unlock preference.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_service.dart';
import '../../core/providers.dart';
import 'settings_api.dart';

/// @brief Biometric unlock preference (device-local).
abstract class BiometricSettings {
  Future<bool> isAvailable();
  Future<bool> isEnabled();

  /// @return resulting enabled state (enabling requires a successful prompt).
  Future<bool> setEnabled(bool value);
}

class AuthBiometricSettings implements BiometricSettings {
  AuthBiometricSettings(this._auth);
  final AuthService _auth;

  @override
  Future<bool> isAvailable() => _auth.biometricAvailable();
  @override
  Future<bool> isEnabled() => _auth.biometricEnabled();
  @override
  Future<bool> setEnabled(bool value) => _auth.setBiometricEnabled(value);
}

final settingsApiProvider =
    Provider<SettingsApi>((ref) => HttpSettingsApi(ref.watch(apiClientProvider)));

final biometricSettingsProvider = Provider<BiometricSettings>((ref) =>
    AuthBiometricSettings(ref.watch(authServiceProvider)));
