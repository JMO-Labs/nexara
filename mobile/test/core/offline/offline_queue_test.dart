/// @file offline_queue_test.dart
/// @brief Offline queue: queue while offline, persist, sync on reconnect, backoff.
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
  });

  test('pending count notifies listeners', () async {
    final q = mk();
    final counts = <int>[];
    q.addListener(() => counts.add(q.pending.length));
    await q.enqueue('post', {});
    await q.sync();
    expect(counts, [1, 0]);
  });
}
