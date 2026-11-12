/// @file websocket.dart
/// @brief Authenticated WebSocket client with auto-reconnect and a broadcast message stream.
import 'dart:async';
import 'dart:convert';

import 'package:stream_channel/stream_channel.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// @brief Server frame: `{type, payload, ts}`.
class RealtimeMessage {
  const RealtimeMessage(this.type, this.payload);
  factory RealtimeMessage.fromJson(Map<String, dynamic> j) => RealtimeMessage(
      j['type']?.toString() ?? '', (j['payload'] as Map?)?.cast<String, dynamic>() ?? const {});
  final String type;
  final Map<String, dynamic> payload;
}

/// @brief Transport-agnostic realtime client (faked in tests).
abstract class RealtimeClient {
  Stream<RealtimeMessage> get messages;
  void connect();
  void send(String type, Map<String, dynamic> payload);
  void dispose();
}

/// @brief Opens a channel to [Uri]; defaults to [WebSocketChannel.connect], tests pass a fake.
typedef ChannelConnector = StreamChannel<dynamic> Function(Uri uri);

/// @brief RealtimeClient over web_socket_channel. First frame is the JWT auth message.
class WebSocketRealtimeClient implements RealtimeClient {
  WebSocketRealtimeClient({
    required this.url,
    required this.tokenReader,
    ChannelConnector? connector,
    this.maxBackoff = const Duration(seconds: 30),
  }) : _connector = connector ?? ((uri) => WebSocketChannel.connect(uri));

  final String url;
  final Future<String?> Function() tokenReader;
  final ChannelConnector _connector;
  final Duration maxBackoff;
  final _out = StreamController<RealtimeMessage>.broadcast();
  StreamChannel<dynamic>? _ch;
  Timer? _retry;
  int _attempts = 0;
  bool _disposed = false;

  @override
  Stream<RealtimeMessage> get messages => _out.stream;

  @override
  void connect() => _open();

  Future<void> _open() async {
    if (_disposed) return;
    String? token;
    try {
      token = await tokenReader();
    } catch (_) {
      token = null;
    }
    if (_disposed) return;
    if (token == null) return _scheduleReconnect(); // not logged in yet: keep polling
    final ch = _ch = _connector(Uri.parse(url));
    ch.sink.add(jsonEncode({'type': 'auth', 'payload': {'token': token}}));
    ch.stream.listen((raw) {
      try {
        final m = RealtimeMessage.fromJson(jsonDecode(raw as String) as Map<String, dynamic>);
        if (m.type == 'auth_ok') _attempts = 0;
        _out.add(m);
      } catch (_) {/* ignore malformed frame */}
    }, onDone: _scheduleReconnect, onError: (_) => _scheduleReconnect(), cancelOnError: true);
  }

  void _scheduleReconnect() {
    if (_disposed || (_retry?.isActive ?? false)) return;
    final secs = 1 << (_attempts < 5 ? _attempts : 5);
    _attempts++;
    final d = Duration(seconds: secs);
    _retry = Timer(d > maxBackoff ? maxBackoff : d, _open);
  }

  @override
  void send(String type, Map<String, dynamic> payload) =>
      _ch?.sink.add(jsonEncode({'type': type, 'payload': payload}));

  @override
  void dispose() {
    _disposed = true;
    _retry?.cancel();
    _ch?.sink.close();
    _out.close();
  }
}
