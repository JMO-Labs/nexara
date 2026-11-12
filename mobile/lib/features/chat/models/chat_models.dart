/// @file chat_models.dart
/// @brief Chat channel and message models.
class Channel {
  const Channel({required this.id, required this.name, required this.type, this.lastMessage});
  factory Channel.fromJson(Map<String, dynamic> j) => Channel(
      id: j['id'].toString(), name: (j['name'] ?? '').toString(), type: (j['channel_type'] ?? '').toString());
  final String id;
  final String name;
  final String type;
  final String? lastMessage;
  Channel withLast(String m) => Channel(id: id, name: name, type: type, lastMessage: m);
}

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.channelId,
    required this.authorId,
    required this.authorName,
    required this.content,
    required this.createdAt,
  });
  factory ChatMessage.fromJson(Map<String, dynamic> j) {
    final a = (j['author'] as Map?)?.cast<String, dynamic>();
    return ChatMessage(
      id: j['id'].toString(),
      channelId: j['channel_id'].toString(),
      authorId: a?['id']?.toString() ?? '',
      authorName: (a?['display_name'] ?? 'Unknown').toString(),
      content: (j['content'] ?? '').toString(),
      createdAt: DateTime.parse(j['created_at'].toString()).toLocal(),
    );
  }
  final String id;
  final String channelId;
  final String authorId;
  final String authorName;
  final String content;
  final DateTime createdAt;
}
