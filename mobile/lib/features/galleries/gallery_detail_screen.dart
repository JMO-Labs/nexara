/// @file gallery_detail_screen.dart
/// @brief Gallery thumbnail grid.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'gallery_models.dart';
import 'gallery_repository.dart';
import 'gallery_viewer_screen.dart';
import 'gallery_widgets.dart';

/// @brief Shows a gallery's items as a grid; tap opens the viewer.
class GalleryDetailScreen extends ConsumerWidget {
  const GalleryDetailScreen({super.key, required this.gallery});
  final Gallery gallery;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(galleryItemsProvider(gallery.id));
    return Scaffold(
      appBar: AppBar(title: Text(gallery.title)),
      body: state.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: e.toString(),
            onRetry: () => ref.invalidate(galleryItemsProvider(gallery.id))),
        data: (items) => items.isEmpty
            ? const EmptyView(message: 'This gallery is empty')
            : GridView.builder(
                padding: const EdgeInsets.all(4),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3, mainAxisSpacing: 4, crossAxisSpacing: 4),
                itemCount: items.length,
                itemBuilder: (_, i) => Semantics(
                  button: true,
                  label: items[i].caption ?? 'Photo ${i + 1}',
                  child: InkWell(
                    key: ValueKey('thumb-${items[i].id}'),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => GalleryViewerScreen(items: items, initialIndex: i))),
                    child: MediaImage(mediaId: items[i].mediaId, thumb: true, fit: BoxFit.cover),
                  ),
                ),
              ),
      ),
    );
  }
}
