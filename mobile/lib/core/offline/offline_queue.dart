/// @file offline_queue.dart
/// @brief Persistent queue of actions taken offline, synced with backoff on reconnect.
import 'package:flutter/foundation.dart';

import '../storage/local_storage.dart';

/// @brief One queued action (post, message, reaction, rsvp...).
class QueuedAction {
  QueuedAction({
    required this.id,
    required this.type,
    required this.payload,
    this.attempts = 0,
    this.nextAttempt,
  });
  final String id;
  final String type;
  final Map<String, dynamic> payload;
  int attempts;
  DateTime? nextAttempt;

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type,
        'payload': payload,
        'attempts': attempts,
        'next': nextAttempt?.toIso8601String(),
      };

  factory QueuedAction.fromJson(Map<String, dynamic> j) => QueuedAction(
        id: j['id'] as String,
        type: j['type'] as String,
        payload: Map<String, dynamic>.from(j['payload'] as Map),
        attempts: j['attempts'] as int? ?? 0,
        nextAttempt: j['next'] == null ? null : DateTime.parse(j['next'] as String),
      );
}

/// @brief FIFO queue persisted in LocalStorage; notifies on change (pending badges).
class OfflineQueue extends ChangeNotifier {
  OfflineQueue({
    required this.storage,
    required this.sender,
    DateTime Function()? clock,
    this.maxBackoff = const Duration(minutes: 5),
  }) : _clock = clock ?? DateTime.now;

  static const _key = 'offline_queue';
  final LocalStorage storage;
  final Future<void> Function(QueuedAction) sender;
  final DateTime Function() _clock;
  final Duration maxBackoff;
  final List<QueuedAction> _items = [];
  bool _syncing = false;
  int _seq = 0;

  List<QueuedAction> get pending => List.unmodifiable(_items);
  bool get syncing => _syncing;

  /// @brief Restore the persisted queue (call on app start).
  Future<void> load() async {
    final raw = await storage.get(_key);
    _items
      ..clear()
      ..addAll((raw as List? ?? const [])
          .map((e) => QueuedAction.fromJson(Map<String, dynamic>.from(e as Map))));
    notifyListeners();
  }

  Future<void> _save() => storage.cache(_key, _items.map((a) => a.toJson()).toList());

  /// @brief Queue an action; returns it so the UI can show a pending marker.
  Future<QueuedAction> enqueue(String type, Map<String, dynamic> payload) async {
    final a = QueuedAction(
        id: '${_clock().microsecondsSinceEpoch}-${_seq++}', type: type, payload: payload);
    _items.add(a);
    await _save();
    notifyListeners();
    return a;
  }

  /// @brief Send due items in order; stop at first failure (keeps ordering).
  /// Notifies listeners only when the pending list changes.
  Future<void> sync() async {
    if (_syncing) return;
    _syncing = true;
    try {
      while (_items.isNotEmpty) {
        final a = _items.first;
        if (a.nextAttempt != null && _clock().isBefore(a.nextAttempt!)) break;
        try {
          await sender(a);
          _items.removeAt(0);
        } catch (_) {
          a.attempts++;
          var d = Duration(seconds: 1 << a.attempts);
          if (d > maxBackoff) d = maxBackoff;
          a.nextAttempt = _clock().add(d);
          await _save();
          break;
        }
        await _save();
        notifyListeners();
      }
    } finally {
      _syncing = false;
    }
  }
}
