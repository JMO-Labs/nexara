/// @file fake_realtime.dart
/// @brief In-memory RealtimeClient for widget/unit tests.
import 'dart:async';

import 'package:nexara_mobile/core/realtime/websocket.dart';

class FakeRealtime implements RealtimeClient {
  final _c = StreamController<RealtimeMessage>.broadcast();
  final sent = <(String, Map<String, dynamic>)>[];

  void emit(String type, Map<String, dynamic> payload) => _c.add(RealtimeMessage(type, payload));

  @override
  Stream<RealtimeMessage> get messages => _c.stream;
  @override
  void connect() {}
  @override
  void send(String type, Map<String, dynamic> payload) => sent.add((type, payload));
  @override
  void dispose() => _c.close();
}
