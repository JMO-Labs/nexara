/// @file offline_queue_test.dart
/// @brief Offline queue: queue while offline, persist, sync on reconnect, backoff.
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/offline/offline_queue.dart';
import 'package:nexara_mobile/core/storage/local_storage.dart';

void main() {
  late MemoryLocalStorage store;
  late DateTime now;
  late List<QueuedAction> sent;
  var fail = false;

  OfflineQueue mk() => OfflineQueue(
        storage: store,
        sender: (a) async {
          if (fail) throw Exception('boom');
          sent.add(a);
        },
        clock: () => now,
      );

  setUp(() {
    store = MemoryLocalStorage();
    now = DateTime.utc(2026, 1, 1);
    sent = [];
    fail = false;
  });

  test('actions queued offline are persisted across restarts', () async {
    final q = mk();
    await q.enqueue('post', {'content': 'hi'});
    await q.enqueue('reaction', {'post_id': '1'});
    final q2 = mk();
    await q2.load();
    expect(q2.pending.map((a) => a.type), ['post', 'reaction']);
  });

  test('sync on reconnect sends in order and empties queue', () async {
    final q = mk();
    await q.enqueue('post', {'content': 'a'});
    await q.enqueue('message', {'text': 'b'});
    await q.sync();
    expect(sent.map((a) => a.type), ['post', 'message']);
    expect(q.pending, isEmpty);
  });

  test('failed sync retries with exponential backoff', () async {
    final q = mk();
    await q.enqueue('post', {'content': 'a'});
    fail = true;
    await q.sync();
    expect(q.pending.single.attempts, 1);
    await q.sync(); // within backoff window: not attempted
    expect(q.pending.single.attempts, 1);
    now = now.add(const Duration(seconds: 3));
    await q.sync();
    expect(q.pending.single.attempts, 2);
    fail = false;
    now = now.add(const Duration(seconds: 5));
    await q.sync();
    expect(q.pending, isEmpty);
    q.dispose();
  });

  test('pending count notifies listeners', () async {
    final q = mk();
    final counts = <int>[];
    q.addListener(() => counts.add(q.pending.length));
    await q.enqueue('post', {});
    await q.sync();
    expect(counts, [1, 0]);
  });

  test('failed sync schedules a retry without a reconnect', () async {
    final timers = <Duration, void Function()>{};
    final q = OfflineQueue(
      storage: store,
      sender: (a) async {
        if (fail) throw Exception('boom');
        sent.add(a);
      },
      clock: () => now,
      timerFactory: (d, cb) {
        timers[d] = cb;
        return Timer(const Duration(days: 1), () {});
      },
    );
    await q.enqueue('post', {'content': 'a'});
    fail = true;
    await q.sync();
    expect(timers.keys, [const Duration(seconds: 2)]);
    fail = false;
    now = now.add(const Duration(seconds: 2));
    timers.values.single();
    await pumpEventQueue();
    expect(sent, hasLength(1));
    expect(q.pending, isEmpty);
    q.dispose();
  });

  test('dispose cancels a pending retry timer', () async {
    Timer? t;
    final q = OfflineQueue(
      storage: store,
      sender: (_) async => throw Exception('boom'),
      clock: () => now,
      timerFactory: (d, cb) => t = Timer(const Duration(days: 1), cb),
    );
    await q.enqueue('post', {});
    await q.sync();
    expect(t!.isActive, isTrue);
    q.dispose();
    expect(t!.isActive, isFalse);
  });

  test('enqueue during load keeps its item', () async {
    final slow = _SlowStorage(store);
    await store.cache('offline_queue', [
      QueuedAction(id: 'old', type: 'post', payload: {}).toJson(),
    ]);
    final q = OfflineQueue(storage: slow, sender: (a) async => sent.add(a), clock: () => now);
    final loading = q.load();
    final enq = q.enqueue('reaction', {});
    slow.release();
    await loading;
    await enq;
    expect(q.pending.map((a) => a.type), ['post', 'reaction']);
  });

  test('sync before load completes sends persisted items', () async {
    final slow = _SlowStorage(store);
    await store.cache('offline_queue', [
      QueuedAction(id: 'old', type: 'post', payload: {}).toJson(),
    ]);
    final q = OfflineQueue(storage: slow, sender: (a) async => sent.add(a), clock: () => now);
    final loading = q.load();
    final syncing = q.sync();
    slow.release();
    await loading;
    await syncing;
    expect(sent.map((a) => a.id), ['old']);
    expect(q.pending, isEmpty);
  });
}

/// @brief Storage whose first get() blocks until release() (simulates slow load).
class _SlowStorage implements LocalStorage {
  _SlowStorage(this.inner);
  final LocalStorage inner;
  final _gate = Completer<void>();
  void release() => _gate.complete();
  @override
  Future<void> cache(String key, Object data) => inner.cache(key, data);
  @override
  Future<Object?> get(String key) async {
    await _gate.future;
    return inner.get(key);
  }

  @override
  Future<void> clear(String key) => inner.clear(key);
}
