// GENERATED CODE - DO NOT MODIFY BY HAND (regenerate: dart run build_runner build)
// ignore_for_file: type=lint
part of 'models.dart';

User _$UserFromJson(Map<String, dynamic> json) => User(
      id: json['id'] as String,
      email: json['email'] as String,
      displayName: json['display_name'] as String?,
      avatarUrl: json['avatar_url'] as String?,
    );

Map<String, dynamic> _$UserToJson(User i) => <String, dynamic>{
      'id': i.id,
      'email': i.email,
      'display_name': i.displayName,
      'avatar_url': i.avatarUrl,
    };

Media _$MediaFromJson(Map<String, dynamic> json) => Media(
      id: json['id'] as String,
      url: json['url'] as String,
      mimeType: json['mime_type'] as String?,
    );

Map<String, dynamic> _$MediaToJson(Media i) =>
    <String, dynamic>{'id': i.id, 'url': i.url, 'mime_type': i.mimeType};

Post _$PostFromJson(Map<String, dynamic> json) => Post(
      id: json['id'] as String,
      authorId: json['author_id'] as String,
      body: json['body'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$PostToJson(Post i) => <String, dynamic>{
      'id': i.id,
      'author_id': i.authorId,
      'body': i.body,
      'created_at': i.createdAt.toIso8601String(),
    };

Chat _$ChatFromJson(Map<String, dynamic> json) =>
    Chat(id: json['id'] as String, title: json['title'] as String?);

Map<String, dynamic> _$ChatToJson(Chat i) =>
    <String, dynamic>{'id': i.id, 'title': i.title};

Event _$EventFromJson(Map<String, dynamic> json) => Event(
      id: json['id'] as String,
      title: json['title'] as String,
      startsAt: DateTime.parse(json['starts_at'] as String),
      location: json['location'] as String?,
    );

Map<String, dynamic> _$EventToJson(Event i) => <String, dynamic>{
      'id': i.id,
      'title': i.title,
      'starts_at': i.startsAt.toIso8601String(),
      'location': i.location,
    };
