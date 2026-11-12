/// @file gallery_widgets.dart
/// @brief Shared widgets for gallery screens: media image, error and empty views.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'gallery_repository.dart';

/// @brief Authenticated network image for a media id (`thumb` selects thumbnail).
class MediaImage extends ConsumerWidget {
  const MediaImage({super.key, required this.mediaId, this.thumb = false, this.fit});
  final String mediaId;
  final bool thumb;
  final BoxFit? fit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final headers = ref.watch(imageHeadersProvider).valueOrNull ?? const {};
    final url = '$apiBaseUrl/media/$mediaId/${thumb ? 'thumbnail' : 'file'}';
    return Image.network(
      url,
      headers: headers,
      fit: fit,
      errorBuilder: (_, __, ___) => const ColoredBox(
        color: Colors.black12,
        child: Center(child: Icon(Icons.broken_image_outlined)),
      ),
    );
  }
}

/// @brief Message with retry button for failed loads.
class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.error_outline, size: 48),
          const SizedBox(height: 8),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 8),
          FilledButton(onPressed: onRetry, child: const Text('Retry')),
        ]),
      );
}

/// @brief Centered empty-state message.
class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.message});
  final String message;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.photo_library_outlined, size: 48),
          const SizedBox(height: 8),
          Text(message),
        ]),
      );
}
