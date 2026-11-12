/// @file post_model.dart
/// @brief Feed post and comment models (hand-written tolerant JSON parsing).
class Author {
  const Author({required this.id, required this.name});
  factory Author.fromJson(Map<String, dynamic>? j) =>
      Author(id: j?['id']?.toString() ?? '', name: (j?['display_name'] ?? j?['username'] ?? 'Unknown').toString());
  final String id;
  final String name;
}

class FeedPost {
  const FeedPost({
    required this.id,
    required this.content,
    required this.author,
    required this.createdAt,
    this.commentCount = 0,
    this.mediaUrls = const [],
  });
  factory FeedPost.fromJson(Map<String, dynamic> j) => FeedPost(
        id: j['id'].toString(),
        content: (j['content'] ?? '').toString(),
        author: Author.fromJson((j['author'] as Map?)?.cast<String, dynamic>()),
        createdAt: DateTime.parse(j['created_at'].toString()).toLocal(),
        commentCount: (j['comment_count'] as num?)?.toInt() ?? 0,
        mediaUrls: ((j['media'] as List?) ?? const [])
            .map((m) => (m as Map)['url'].toString())
            .toList(),
      );
  final String id;
  final String content;
  final Author author;
  final DateTime createdAt;
  final int commentCount;
  final List<String> mediaUrls;
}

class PostComment {
  const PostComment({required this.id, required this.content, required this.author, required this.createdAt});
  factory PostComment.fromJson(Map<String, dynamic> j) => PostComment(
        id: j['id'].toString(),
        content: (j['content'] ?? '').toString(),
        author: Author.fromJson((j['author'] as Map?)?.cast<String, dynamic>()),
        createdAt: DateTime.parse(j['created_at'].toString()).toLocal(),
      );
  final String id;
  final String content;
  final Author author;
  final DateTime createdAt;
}

/// @brief One page of a cursor-paginated list.
class PagedResult<T> {
  const PagedResult(this.items, this.cursor, this.hasMore);
  final List<T> items;
  final String? cursor;
  final bool hasMore;
}
