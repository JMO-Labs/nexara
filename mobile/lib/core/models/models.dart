/// @file models.dart
/// @brief Shared API models (json_serializable; `*.g.dart` generated and committed).
import 'package:json_annotation/json_annotation.dart';

part 'models.g.dart';

@JsonSerializable()
class User {
  const User({required this.id, required this.email, this.displayName, this.avatarUrl});
  factory User.fromJson(Map<String, dynamic> j) => _$UserFromJson(j);
  final String id;
  final String email;
  @JsonKey(name: 'display_name')
  final String? displayName;
  @JsonKey(name: 'avatar_url')
  final String? avatarUrl;
  Map<String, dynamic> toJson() => _$UserToJson(this);
}

@JsonSerializable()
class Media {
  const Media({required this.id, required this.url, this.mimeType});
  factory Media.fromJson(Map<String, dynamic> j) => _$MediaFromJson(j);
  final String id;
  final String url;
  @JsonKey(name: 'mime_type')
  final String? mimeType;
  Map<String, dynamic> toJson() => _$MediaToJson(this);
}

@JsonSerializable()
class Post {
  const Post({required this.id, required this.authorId, required this.body, required this.createdAt});
  factory Post.fromJson(Map<String, dynamic> j) => _$PostFromJson(j);
  final String id;
  @JsonKey(name: 'author_id')
  final String authorId;
  final String body;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  Map<String, dynamic> toJson() => _$PostToJson(this);
}

@JsonSerializable()
class Chat {
  const Chat({required this.id, this.title});
  factory Chat.fromJson(Map<String, dynamic> j) => _$ChatFromJson(j);
  final String id;
  final String? title;
  Map<String, dynamic> toJson() => _$ChatToJson(this);
}

@JsonSerializable()
class Event {
  const Event({required this.id, required this.title, required this.startsAt, this.location});
  factory Event.fromJson(Map<String, dynamic> j) => _$EventFromJson(j);
  final String id;
  final String title;
  @JsonKey(name: 'starts_at')
  final DateTime startsAt;
  final String? location;
  Map<String, dynamic> toJson() => _$EventToJson(this);
}
