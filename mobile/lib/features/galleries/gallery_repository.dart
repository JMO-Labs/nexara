/// @file gallery_repository.dart
/// @brief Gallery API access and Riverpod providers.
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/providers.dart';
import 'gallery_models.dart';

/// @brief Reads galleries through the shared ApiClient.
class GalleryRepository {
  GalleryRepository(this._api);
  final ApiClient _api;

  Future<T> _guard<T>(Future<T> Function() f) async {
    try {
      return await f();
    } on DioException catch (e) {
      throw e.error is AppError ? e.error! : mapError(e);
    }
  }

  /// @brief List galleries visible to the viewer.
  Future<List<Gallery>> list() => _guard(() async {
        final r = await _api.dio.get('/galleries');
        final items = (r.data['items'] as List?) ?? const [];
        return items.map((e) => Gallery.fromJson(e as Map<String, dynamic>)).toList();
      });

  /// @brief List media items of a gallery.
  Future<List<GalleryItem>> items(String galleryId) => _guard(() async {
        final r = await _api.dio.get('/galleries/$galleryId/items');
        return (r.data as List)
            .map((e) => GalleryItem.fromJson(e as Map<String, dynamic>))
            .toList();
      });
}

final galleryRepositoryProvider =
    Provider<GalleryRepository>((ref) => GalleryRepository(ref.watch(apiClientProvider)));

final galleriesProvider = FutureProvider.autoDispose<List<Gallery>>(
    (ref) => ref.watch(galleryRepositoryProvider).list());

final galleryItemsProvider = FutureProvider.autoDispose.family<List<GalleryItem>, String>(
    (ref, id) => ref.watch(galleryRepositoryProvider).items(id));

/// @brief Auth headers for loading protected media images.
final imageHeadersProvider = FutureProvider<Map<String, String>>((ref) async {
  final t = await ref.watch(tokenStoreProvider).readAccess();
  return t == null ? const {} : {'Authorization': 'Bearer $t'};
});
