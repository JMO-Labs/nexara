/// @file post_detail_screen.dart
/// @brief Single post with comment thread, reactions and reply field.
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/feed_provider.dart';

class PostDetailScreen extends ConsumerStatefulWidget {
  const PostDetailScreen({super.key, required this.postId});
  final String postId;
  @override
  ConsumerState<PostDetailScreen> createState() => _PostDetailScreenState();
}

class _PostDetailScreenState extends ConsumerState<PostDetailScreen> {
  final _reply = TextEditingController();

  @override
  void dispose() {
    _reply.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _reply.text.trim();
    if (text.isEmpty) return;
    try {
      await ref.read(feedRepositoryProvider).addComment(widget.postId, text);
      _reply.clear();
      ref.invalidate(commentsProvider(widget.postId));
    } catch (_) {
      _fail('Could not send reply.');
    }
  }

  void _fail(String msg) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    final post = ref.watch(postDetailProvider(widget.postId));
    final comments = ref.watch(commentsProvider(widget.postId));
    return Scaffold(
      appBar: AppBar(title: const Text('Post')),
      body: Column(children: [
        Expanded(
          child: ListView(padding: const EdgeInsets.all(16), children: [
            post.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => const Text('Could not load the post.'),
              data: (p) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(p.author.name, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(p.content),
                for (final u in p.mediaUrls)
                  Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Semantics(
                          label: 'Post image', image: true, child: CachedNetworkImage(imageUrl: u))),
                Row(children: [
                  IconButton(
                    tooltip: 'Like',
                    icon: const Icon(Icons.thumb_up_outlined),
                    onPressed: () async {
                      try {
                        await ref.read(feedRepositoryProvider).react(p.id, '👍');
                      } catch (_) {
                        _fail('Could not like the post.');
                      }
                    },
                  ),
                ]),
              ]),
            ),
            const Divider(),
            comments.when(
              loading: () => const SizedBox.shrink(),
              error: (e, _) => const Text('Could not load comments.'),
              data: (cs) => Column(children: [
                for (final c in cs) ListTile(title: Text(c.author.name), subtitle: Text(c.content)),
              ]),
            ),
          ]),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Row(children: [
              Expanded(
                  child: TextField(
                      controller: _reply,
                      decoration: const InputDecoration(hintText: 'Write a reply', border: OutlineInputBorder()))),
              IconButton(tooltip: 'Send reply', icon: const Icon(Icons.send), onPressed: _send),
            ]),
          ),
        ),
      ]),
    );
  }
}
