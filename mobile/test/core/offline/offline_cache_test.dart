/// @file offline_cache_test.dart
/// @brief Typed cache over LocalStorage: cache, retrieve, clear.
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/offline/offline_cache.dart';
import 'package:nexara_mobile/core/storage/local_storage.dart';

void main() {
  test('cache, retrieve, clear', () async {
    final c = OfflineCache(MemoryLocalStorage());
    expect(await c.getList(CacheKind.posts), isNull);
    await c.putList(CacheKind.posts, [{'id': 1}]);
    expect(await c.getList(CacheKind.posts), [{'id': 1}]);
    await c.clear(CacheKind.posts);
    expect(await c.getList(CacheKind.posts), isNull);
  });
}
