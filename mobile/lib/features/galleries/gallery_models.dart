/// @file gallery_models.dart
/// @brief Plain models for galleries and gallery items.

/// @brief A gallery summary as returned by `GET /galleries`.
class Gallery {
  const Gallery({
    required this.id,
    required this.title,
    this.description,
    this.coverMediaId,
    this.itemCount = 0,
  });

  factory Gallery.fromJson(Map<String, dynamic> j) => Gallery(
        id: j['id'] as String,
        title: j['title'] as String,
        description: j['description'] as String?,
        coverMediaId: j['cover_media_id'] as String?,
        itemCount: (j['item_count'] as num?)?.toInt() ?? 0,
      );

  final String id;
  final String title;
  final String? description;
  final String? coverMediaId;
  final int itemCount;
}

/// @brief A media item inside a gallery.
class GalleryItem {
  const GalleryItem({required this.id, required this.mediaId, this.caption});

  factory GalleryItem.fromJson(Map<String, dynamic> j) => GalleryItem(
        id: j['id'] as String,
        mediaId: j['media_id'] as String,
        caption: j['caption'] as String?,
      );

  final String id;
  final String mediaId;
  final String? caption;
}
