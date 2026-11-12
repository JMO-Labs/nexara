/// @file gallery_viewer_screen.dart
/// @brief Full-screen swipeable media viewer.
import 'package:flutter/material.dart';

import 'gallery_models.dart';
import 'gallery_widgets.dart';

/// @brief Swipe between gallery items with pinch zoom.
class GalleryViewerScreen extends StatefulWidget {
  const GalleryViewerScreen({super.key, required this.items, this.initialIndex = 0});
  final List<GalleryItem> items;
  final int initialIndex;

  @override
  State<GalleryViewerScreen> createState() => _GalleryViewerScreenState();
}

class _GalleryViewerScreenState extends State<GalleryViewerScreen> {
  late final PageController _c = PageController(initialPage: widget.initialIndex);
  late int _i = widget.initialIndex;

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(
          backgroundColor: Colors.black,
          foregroundColor: Colors.white,
          title: Text('${_i + 1} / ${widget.items.length}'),
        ),
        body: PageView.builder(
          controller: _c,
          itemCount: widget.items.length,
          onPageChanged: (i) => setState(() => _i = i),
          itemBuilder: (_, i) => Column(children: [
            Expanded(
              child: InteractiveViewer(
                child: MediaImage(mediaId: widget.items[i].mediaId, fit: BoxFit.contain),
              ),
            ),
            if (widget.items[i].caption != null)
              Padding(
                padding: const EdgeInsets.all(12),
                child: Text(widget.items[i].caption!,
                    style: const TextStyle(color: Colors.white)),
              ),
          ]),
        ),
      );
}
