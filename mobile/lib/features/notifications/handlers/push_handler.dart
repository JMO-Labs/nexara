/// @file push_handler.dart
/// @brief Routes push notifications: in-app display and tap deep links.
import 'dart:async';

import '../models/push_models.dart';
import '../providers/push_provider.dart';

/// @brief Map a payload to an app route; unknown types go home.
String routeForPayload(NotificationPayload p) {
  if (p.id == null || p.id!.isEmpty) return '/';
  return switch (p.type) {
    'post' => '/posts/${p.id}',
    'chat' => '/chat/${p.id}',
    'event' => '/events/${p.id}',
    _ => '/',
  };
}

class PushHandler {
  PushHandler({required this.service, required this.navigate, this.onForeground});
  final PushService service;
  final void Function(String route) navigate;
  final void Function(PushNotification n)? onForeground;
  final _subs = <StreamSubscription<PushNotification>>[];

  void start() {
    _subs
      ..add(service.received.listen((n) => onForeground?.call(n)))
      ..add(service.opened.listen((n) => navigate(routeForPayload(n.payload))));
  }

  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
  }
}
