/// @file push_test.dart
/// @brief Push: token registration, payload parsing, deep link routing.
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/features/notifications/handlers/push_handler.dart';
import 'package:nexara_mobile/features/notifications/models/push_models.dart';
import 'package:nexara_mobile/features/notifications/providers/push_provider.dart';

class FakeMessaging implements PushMessaging {
  final tokens = StreamController<String>.broadcast();
  final msgs = StreamController<Map<String, dynamic>>.broadcast();
  final taps = StreamController<Map<String, dynamic>>.broadcast();
  @override
  Future<bool> requestPermission() async => true;
  @override
  Future<String?> getToken() async => 'tok1';
  @override
  Stream<String> get onTokenRefresh => tokens.stream;
  @override
  Stream<Map<String, dynamic>> get onMessage => msgs.stream;
  @override
  Stream<Map<String, dynamic>> get onTap => taps.stream;
}

void main() {
  test('push token registered with backend', () async {
    final calls = <(String, String)>[];
    final svc = PushService(
        messaging: FakeMessaging(),
        platform: 'android',
        register: (platform, token) async => calls.add((platform, token)));
    await svc.init();
    expect(calls, [('android', 'tok1')]);
  });

  test('refreshed token is re-registered', () async {
    final m = FakeMessaging();
    final calls = <String>[];
    final svc = PushService(
        messaging: m, platform: 'ios', register: (p, t) async => calls.add(t));
    await svc.init();
    m.tokens.add('tok2');
    await Future<void>.delayed(Duration.zero);
    expect(calls, ['tok1', 'tok2']);
  });

  test('notification received and parsed', () async {
    final m = FakeMessaging();
    final svc = PushService(messaging: m, platform: 'android', register: (p, t) async {});
    await svc.init();
    final got = <PushNotification>[];
    svc.received.listen(got.add);
    m.msgs.add({
      'title': 'New post',
      'body': 'Hello',
      'data': {'type': 'post', 'id': '42'}
    });
    await Future<void>.delayed(Duration.zero);
    expect(got.single.title, 'New post');
    expect(got.single.payload.type, 'post');
    expect(got.single.payload.id, '42');
  });

  test('deep link routes by type', () {
    String r(String t, String id) => routeForPayload(NotificationPayload(type: t, id: id));
    expect(r('post', '1'), '/posts/1');
    expect(r('chat', '2'), '/chat/2');
    expect(r('event', '3'), '/events/3');
    expect(r('unknown', '4'), '/');
  });

  test('tap navigates to the deep link', () async {
    final m = FakeMessaging();
    final svc = PushService(messaging: m, platform: 'android', register: (p, t) async {});
    await svc.init();
    final routes = <String>[];
    final h = PushHandler(service: svc, navigate: routes.add)..start();
    m.taps.add({
      'title': 't',
      'body': 'b',
      'data': {'type': 'event', 'id': '9'}
    });
    await Future<void>.delayed(Duration.zero);
    expect(routes, ['/events/9']);
    h.dispose();
  });
}
