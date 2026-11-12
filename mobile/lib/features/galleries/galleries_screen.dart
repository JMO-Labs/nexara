/// @file galleries_screen.dart
/// @brief Galleries list screen.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'gallery_detail_screen.dart';
import 'gallery_repository.dart';
import 'gallery_widgets.dart';

/// @brief Lists galleries; tap opens GalleryDetailScreen.
class GalleriesScreen extends ConsumerWidget {
  const GalleriesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(galleriesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Galleries')),
      body: state.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            ErrorView(message: e.toString(), onRetry: () => ref.invalidate(galleriesProvider)),
        data: (list) => list.isEmpty
            ? const EmptyView(message: 'No galleries yet')
            : ListView.builder(
                itemCount: list.length,
                itemBuilder: (_, i) {
                  final g = list[i];
                  return ListTile(
                    leading: SizedBox(
                      width: 56,
                      height: 56,
                      child: g.coverMediaId == null
                          ? const Icon(Icons.photo_library_outlined)
                          : MediaImage(mediaId: g.coverMediaId!, thumb: true, fit: BoxFit.cover),
                    ),
                    title: Text(g.title),
                    subtitle: Text('${g.itemCount} items'),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => GalleryDetailScreen(gallery: g))),
                  );
                },
              ),
      ),
    );
  }
}
