/// @file notifications_api.dart
/// @brief Notifications API client and provider.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/api/api_client.dart';

/// @brief A single notification item.
class AppNotification {
  const AppNotification(
      {required this.id, required this.type, required this.message, required this.createdAt, this.readAt});
  final String id;
  final String type;
  final String message;
  final DateTime createdAt;
  final DateTime? readAt;
  bool get unread => readAt == null;

  factory AppNotification.fromJson(Map<String, dynamic> j) {
    final payload = (j['payload'] as Map?) ?? const {};
    return AppNotification(
      id: j['id'] as String,
      type: j['type'] as String,
      message: (payload['message'] as String?) ?? (j['type'] as String),
      createdAt: DateTime.parse(j['created_at'] as String),
      readAt: j['read_at'] == null ? null : DateTime.parse(j['read_at'] as String),
    );
  }
}

/// @brief Contract for the notifications endpoints.
abstract class NotificationsApi {
  Future<List<AppNotification>> list();
  Future<void> markRead(String id);
}

class HttpNotificationsApi implements NotificationsApi {
  HttpNotificationsApi(this._api);
  final ApiClient _api;

  @override
  Future<List<AppNotification>> list() async {
    final r = await _api.dio.get('/notifications', queryParameters: {'limit': 50});
    return ((r.data as Map)['items'] as List)
        .map((e) => AppNotification.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> markRead(String id) => _api.dio.post('/notifications/$id/read');
}

final notificationsApiProvider =
    Provider<NotificationsApi>((ref) => HttpNotificationsApi(ref.watch(apiClientProvider)));

final notificationsProvider = FutureProvider.autoDispose<List<AppNotification>>((ref) async {
  final items = [...await ref.watch(notificationsApiProvider).list()];
  items.sort((a, b) => b.createdAt.compareTo(a.createdAt));
  return items;
});
