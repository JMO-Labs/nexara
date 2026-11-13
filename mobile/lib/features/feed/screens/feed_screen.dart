/// @file feed_screen.dart
/// @brief Activity feed with pull-to-refresh and infinite scroll.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/offline/connectivity_service.dart';
import '../providers/feed_provider.dart';
import 'post_composer_screen.dart';
import 'post_detail_screen.dart';

class FeedScreen extends ConsumerStatefulWidget {
  const FeedScreen({super.key});
  @override
  ConsumerState<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends ConsumerState<FeedScreen> {
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      if (_scroll.position.extentAfter < 300) ref.read(feedProvider.notifier).loadMore();
    });
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = ref.watch(feedProvider);
    final queued =
        ref.watch(offlineQueueProvider).pending.where((a) => a.type == 'post').toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Feed')),
      floatingActionButton: FloatingActionButton(
        tooltip: 'New post',
        onPressed: () => Navigator.of(context)
            .push(MaterialPageRoute<void>(builder: (_) => const PostComposerScreen())),
        child: const Icon(Icons.edit),
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(feedProvider.notifier).refresh(),
        child: s.loading && s.items.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : ListView.builder(
                controller: _scroll,
                physics: const AlwaysScrollableScrollPhysics(),
                itemCount: queued.length + s.items.length + 1,
                itemBuilder: (ctx, i) {
                  if (i < queued.length) {
                    return Card(
                      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      child: ListTile(
                        title: Text(queued[i].payload['content'].toString(),
                            maxLines: 3, overflow: TextOverflow.ellipsis),
                        trailing: const PendingBadge(),
                      ),
                    );
                  }
                  i -= queued.length;
                  if (i == s.items.length) {
                    if (s.error != null) return ListTile(title: Text(s.error!));
                    return s.loading
                        ? const Padding(
                            padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()))
                        : const SizedBox(height: 72);
                  }
                  final p = s.items[i];
                  return Card(
                    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: ListTile(
                      title: Text(p.author.name),
                      subtitle: Text(p.content, maxLines: 3, overflow: TextOverflow.ellipsis),
                      trailing: Text(DateFormat.MMMd().add_jm().format(p.createdAt)),
                      onTap: () => Navigator.of(ctx).push(MaterialPageRoute<void>(
                          builder: (_) => PostDetailScreen(postId: p.id))),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
