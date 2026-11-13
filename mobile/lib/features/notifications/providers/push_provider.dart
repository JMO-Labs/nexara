/// @file push_provider.dart
/// @brief Push setup (FCM on Android, APNs via FCM on iOS) and token registration.
import 'dart:async';
import 'dart:io';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../models/push_models.dart';

abstract class PushMessaging {
  Future<bool> requestPermission();
  Future<String?> getToken();
  Stream<String> get onTokenRefresh;
  Stream<Map<String, dynamic>> get onMessage;
  Stream<Map<String, dynamic>> get onTap;
}

Map<String, dynamic> _flatten(RemoteMessage m) => {
      'title': m.notification?.title ?? m.data['title'] ?? '',
      'body': m.notification?.body ?? m.data['body'] ?? '',
      'data': m.data,
    };

class FirebasePushMessaging implements PushMessaging {
  FirebaseMessaging get _f => FirebaseMessaging.instance;
  @override
  Future<bool> requestPermission() async {
    final s = await _f.requestPermission();
    return s.authorizationStatus == AuthorizationStatus.authorized ||
        s.authorizationStatus == AuthorizationStatus.provisional;
  }

  @override
  Future<String?> getToken() => _f.getToken();
  @override
  Stream<String> get onTokenRefresh => _f.onTokenRefresh;
  @override
  Stream<Map<String, dynamic>> get onMessage => FirebaseMessaging.onMessage.map(_flatten);
  @override
  Stream<Map<String, dynamic>> get onTap => FirebaseMessaging.onMessageOpenedApp.map(_flatten);
}

/// @brief Owns permission, token registration and the incoming stream.
class PushService {
  PushService({required this.messaging, required this.platform, required this.register});
  final PushMessaging messaging;
  final String platform;
  final Future<void> Function(String platform, String token) register;
  final _received = StreamController<PushNotification>.broadcast();
  final _opened = StreamController<PushNotification>.broadcast();
  final _subs = <StreamSubscription<dynamic>>[];

  Stream<PushNotification> get received => _received.stream;
  Stream<PushNotification> get opened => _opened.stream;

  /// @brief initPushNotifications: ask permission, register token, listen.
  Future<void> init() async {
    if (!await messaging.requestPermission()) return;
    final t = await messaging.getToken();
    if (t != null) await register(platform, t);
    _subs
      ..add(messaging.onTokenRefresh.listen((t) => register(platform, t)))
      ..add(messaging.onMessage.map(PushNotification.fromMap).listen(_received.add))
      ..add(messaging.onTap.map(PushNotification.fromMap).listen(_opened.add));
  }

  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
    _received.close();
    _opened.close();
  }
}

final pushServiceProvider = Provider<PushService>((ref) {
  final s = PushService(
    messaging: FirebasePushMessaging(),
    platform: Platform.isIOS ? 'ios' : 'android',
    register: (p, t) async {
      await ref.read(apiClientProvider).dio.post('/push/devices', data: {'platform': p, 'token': t});
    },
  );
  ref.onDispose(s.dispose);
  return s;
});
