/// @file offline_cache.dart
/// @brief Typed cache of recent posts, messages and events over LocalStorage.
import '../storage/local_storage.dart';

enum CacheKind { posts, messages, events }

class OfflineCache {
  OfflineCache(this._s);
  final LocalStorage _s;

  String _k(CacheKind k) => 'cache.${k.name}';

  Future<void> putList(CacheKind k, List<Map<String, dynamic>> items) => _s.cache(_k(k), items);

  /// @return cached list, or null when nothing cached.
  Future<List<Map<String, dynamic>>?> getList(CacheKind k) async {
    final v = await _s.get(_k(k));
    return (v as List?)?.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<void> clear(CacheKind k) => _s.clear(_k(k));
}
