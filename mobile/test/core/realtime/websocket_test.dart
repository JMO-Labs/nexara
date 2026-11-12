/// @file websocket_test.dart
/// @brief WebSocket client: auth frame, message stream, auto-reconnect.
import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/realtime/websocket.dart';
import 'package:stream_channel/stream_channel.dart';

void main() {
  test('sends auth, relays frames, reconnects after close', () async {
    final servers = <StreamChannelController<Object?>>[];
    final clientSent = <List<Object?>>[];
    final c = WebSocketRealtimeClient(
      url: 'ws://x/ws/',
      tokenReader: () async => 'tok',
      maxBackoff: const Duration(milliseconds: 10),
      connector: (_) {
        final ctrl = StreamChannelController<Object?>(sync: true);
        servers.add(ctrl);
        final sent = <Object?>[];
        clientSent.add(sent);
        ctrl.foreign.stream.listen(sent.add);
        return ctrl.local;
      },
    );
    final got = <RealtimeMessage>[];
    c.messages.listen(got.add);
    c.connect();
    await Future<void>.delayed(const Duration(milliseconds: 20));
    expect(jsonDecode(clientSent[0].first as String), {'type': 'auth', 'payload': {'token': 'tok'}});

    servers[0].foreign.sink.add(jsonEncode({'type': 'chat.message', 'payload': {'a': 1}}));
    await Future<void>.delayed(const Duration(milliseconds: 5));
    expect(got.single.type, 'chat.message');

    await servers[0].foreign.sink.close();
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(servers.length, greaterThanOrEqualTo(2));
    c.dispose();
  });

  test('retries when token is null or reader throws, then connects', () async {
    final sent = <Object?>[];
    var calls = 0;
    final c = WebSocketRealtimeClient(
      url: 'ws://x/ws/',
      tokenReader: () async {
        calls++;
        if (calls == 1) return null;
        if (calls == 2) throw StateError('storage');
        return 'tok';
      },
      maxBackoff: const Duration(milliseconds: 10),
      connector: (_) {
        final ctrl = StreamChannelController<Object?>(sync: true);
        ctrl.foreign.stream.listen(sent.add);
        return ctrl.local;
      },
    );
    c.connect();
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(jsonDecode(sent.first as String), {'type': 'auth', 'payload': {'token': 'tok'}});
    c.dispose();
  });
}
