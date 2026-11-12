/// @file biometric_pref.dart
/// @brief Persisted biometric-unlock preference (survives app restarts).
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// @brief Read/write the biometric-unlock enabled flag.
abstract class BiometricPrefStore {
  /// @return true when biometric unlock is enabled (default false).
  Future<bool> read();

  /// @param value new enabled state.
  Future<void> write(bool value);
}

/// @brief BiometricPrefStore backed by the platform keychain / keystore.
class SecureBiometricPrefStore implements BiometricPrefStore {
  SecureBiometricPrefStore([FlutterSecureStorage? s]) : _s = s ?? const FlutterSecureStorage();
  final FlutterSecureStorage _s;
  static const _key = 'biometric_enabled';

  @override
  Future<bool> read() async => await _s.read(key: _key) == 'true';
  @override
  Future<void> write(bool value) => _s.write(key: _key, value: value.toString());
}
