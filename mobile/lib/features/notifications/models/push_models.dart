/// @file push_models.dart
/// @brief Push notification models.

/// @brief Routing data carried in a push `data` map.
class NotificationPayload {
  const NotificationPayload({required this.type, this.id});
  final String type;
  final String? id;

  factory NotificationPayload.fromJson(Map<String, dynamic> j) =>
      NotificationPayload(type: (j['type'] ?? '').toString(), id: j['id']?.toString());
}

class PushNotification {
  const PushNotification({required this.title, required this.body, required this.payload});
  final String title;
  final String body;
  final NotificationPayload payload;

  /// @brief Parse a flattened message `{title, body, data: {...}}`.
  factory PushNotification.fromMap(Map<String, dynamic> m) => PushNotification(
        title: (m['title'] ?? '').toString(),
        body: (m['body'] ?? '').toString(),
        payload: NotificationPayload.fromJson(
            Map<String, dynamic>.from((m['data'] as Map?) ?? const {})),
      );
}
