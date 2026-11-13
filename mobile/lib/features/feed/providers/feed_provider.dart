/// @file feed_provider.dart
/// @brief Riverpod providers for the paginated feed, post detail and post creation.
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../../core/offline/connectivity_service.dart';
import '../../../core/providers.dart';
import '../models/post_model.dart';

/// @brief REST access for posts (all calls go through the authenticated ApiClient).
class FeedRepository {
  FeedRepository(this._dio);
  final Dio _dio;

  Future<PagedResult<FeedPost>> feed({String? cursor, int limit = 20}) async {
    final r = await _dio.get('/posts', queryParameters: {'limit': limit, if (cursor != null) 'cursor': cursor});
    final d = r.data as Map<String, dynamic>;
    return PagedResult([for (final p in d['items'] as List) FeedPost.fromJson(p as Map<String, dynamic>)],
        d['cursor'] as String?, d['has_more'] == true);
  }

  Future<FeedPost> post(String id) async =>
      FeedPost.fromJson((await _dio.get('/posts/$id')).data as Map<String, dynamic>);

  Future<List<PostComment>> comments(String id) async {
    final r = await _dio.get('/posts/$id/comments');
    return [for (final c in (r.data as Map)['items'] as List) PostComment.fromJson(c as Map<String, dynamic>)];
  }

  Future<FeedPost> create(String content, {List<String> mediaIds = const []}) async {
    final r = await _dio.post('/posts', data: {
      'content': content,
      'media_ids': mediaIds,
    });
    return FeedPost.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> addComment(String postId, String content) =>
      _dio.post('/posts/$postId/comments', data: {'content': content});

  Future<void> react(String postId, String emoji) =>
      _dio.post('/posts/$postId/reactions', data: {'emoji': emoji});
}

final feedRepositoryProvider =
    Provider<FeedRepository>((ref) => FeedRepository(ref.watch(apiClientProvider).dio));

class FeedState {
  const FeedState({this.items = const [], this.cursor, this.hasMore = true, this.loading = false, this.error});
  final List<FeedPost> items;
  final String? cursor;
  final bool hasMore;
  final bool loading;
  final String? error;
}

/// @brief Paginated feed with refresh, load-more and realtime prepend.
class FeedNotifier extends StateNotifier<FeedState> {
  FeedNotifier(this._repo) : super(const FeedState(loading: true)) {
    refresh();
  }
  final FeedRepository _repo;

  Future<void> refresh() async {
    try {
      final p = await _repo.feed();
      state = FeedState(items: p.items, cursor: p.cursor, hasMore: p.hasMore);
    } catch (e) {
      state = FeedState(items: state.items, cursor: state.cursor, hasMore: state.hasMore, error: _msg(e));
    }
  }

  Future<void> loadMore() async {
    if (state.loading || !state.hasMore || state.cursor == null) return;
    state = FeedState(items: state.items, cursor: state.cursor, hasMore: true, loading: true);
    try {
      final p = await _repo.feed(cursor: state.cursor);
      state = FeedState(items: [...state.items, ...p.items], cursor: p.cursor, hasMore: p.hasMore);
    } catch (e) {
      state = FeedState(items: state.items, cursor: state.cursor, error: _msg(e));
    }
  }

  /// @brief Insert a post received over the realtime channel (deduplicated).
  void prepend(FeedPost p) {
    if (state.items.any((x) => x.id == p.id)) return;
    state = FeedState(items: [p, ...state.items], cursor: state.cursor, hasMore: state.hasMore);
  }

  static String _msg(Object e) =>
      e is DioException && e.error is AppError ? e.error.toString() : 'Could not load the feed.';
}

final feedProvider = StateNotifierProvider<FeedNotifier, FeedState>((ref) {
  final n = FeedNotifier(ref.watch(feedRepositoryProvider));
  final sub = ref.watch(realtimeClientProvider).messages.listen((m) {
    if (m.type == 'feed_update' && m.payload['event'] == 'created' && m.payload['post'] is Map) {
      try {
        n.prepend(FeedPost.fromJson((m.payload['post'] as Map).cast<String, dynamic>()));
      } catch (_) {/* ignore malformed payload */}
    }
  });
  ref.onDispose(sub.cancel);
  return n;
});

final postDetailProvider = FutureProvider.family<FeedPost, String>(
    (ref, id) => ref.watch(feedRepositoryProvider).post(id));

final commentsProvider = FutureProvider.family<List<PostComment>, String>((ref, id) {
  final sub = ref.watch(realtimeClientProvider).messages.listen((m) {
    if (m.type == 'feed_update' &&
        m.payload['event'] == 'comment_created' &&
        m.payload['post_id']?.toString() == id) {
      ref.invalidateSelf();
    }
  });
  ref.onDispose(sub.cancel);
  return ref.watch(feedRepositoryProvider).comments(id);
});

/// @brief Mutation: create a post, then refresh the feed.
final createPostProvider = Provider<Future<void> Function(String)>((ref) {
  return (content) async {
    final online = ref.read(onlineProvider).value ?? true;
    if (!online) {
      await ref.read(offlineQueueProvider).enqueue('post', {'content': content});
      return;
    }
    await ref.read(feedRepositoryProvider).create(content);
    await ref.read(feedProvider.notifier).refresh();
  };
});
