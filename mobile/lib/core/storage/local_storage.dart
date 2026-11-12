/// @file local_storage.dart
/// @brief Key/value offline cache for posts, messages and events.
import 'dart:convert';

/// @brief Offline cache contract: cache(key, data), get(key), clear(key).
abstract class LocalStorage {
  Future<void> cache(String key, Object data);
  Future<Object?> get(String key);
  Future<void> clear(String key);
}

/// @brief In-memory implementation (JSON round-tripped); used until the Isar
/// backed store lands with offline mode (SCALE-T28).
class MemoryLocalStorage implements LocalStorage {
  final Map<String, String> _m = {};
  @override
  Future<void> cache(String key, Object data) async => _m[key] = jsonEncode(data);
  @override
  Future<Object?> get(String key) async {
    final v = _m[key];
    return v == null ? null : jsonDecode(v);
  }

  @override
  Future<void> clear(String key) async => _m.remove(key);
}
