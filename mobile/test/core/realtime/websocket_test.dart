/// @file websocket_test.dart
/// @brief WebSocket client: auth frame, message stream, auto-reconnect.
import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/realtime/websocket.dart';
import 'package:stream_channel/stream_channel.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

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
        return _Chan(ctrl.local);
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
}

class _Chan extends StreamChannelMixin<dynamic> implements WebSocketChannel {
  _Chan(this._c);
  final StreamChannel<Object?> _c;
  @override
  Stream get stream => _c.stream;
  @override
  WebSocketSink get sink => _Sink(_c.sink);
  @override
  Future<void> get ready => Future.value();
  @override
  int? get closeCode => null;
  @override
  String? get closeReason => null;
  @override
  String? get protocol => null;
}

class _Sink implements WebSocketSink {
  _Sink(this._s);
  final StreamSink<Object?> _s;
  @override
  void add(Object? e) => _s.add(e);
  @override
  void addError(Object e, [StackTrace? st]) => _s.addError(e, st);
  @override
  Future addStream(Stream s) => _s.addStream(s);
  @override
  Future close([int? code, String? reason]) => _s.close();
  @override
  Future get done => _s.done;
}
