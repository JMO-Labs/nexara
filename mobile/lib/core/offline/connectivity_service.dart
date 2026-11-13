/// @file connectivity_service.dart
/// @brief Network status stream, offline banner, and sync-on-reconnect wiring.
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import 'offline_queue.dart';

abstract class ConnectivityService {
  Future<bool> isOnline();
  Stream<bool> get onChanged;
}

class PluginConnectivityService implements ConnectivityService {
  PluginConnectivityService([Connectivity? c]) : _c = c ?? Connectivity();
  final Connectivity _c;
  static bool _on(List<ConnectivityResult> r) => r.any((e) => e != ConnectivityResult.none);
  @override
  Future<bool> isOnline() async => _on(await _c.checkConnectivity());
  @override
  Stream<bool> get onChanged => _c.onConnectivityChanged.map(_on).distinct();
}

final connectivityServiceProvider =
    Provider<ConnectivityService>((_) => PluginConnectivityService());

/// @brief Current online state (initial value from isOnline, then changes).
final onlineProvider = StreamProvider<bool>((ref) async* {
  final s = ref.watch(connectivityServiceProvider);
  yield await s.isOnline();
  yield* s.onChanged;
});

/// @brief Queue sender: replays an action against the REST API.
Future<void> sendQueuedAction(Ref ref, QueuedAction a) async {
  final api = ref.read(apiClientProvider);
  switch (a.type) {
    case 'post':
      await api.dio.post('/posts', data: a.payload);
    default:
      throw UnsupportedError('Unknown queued action ${a.type}');
  }
}

final offlineQueueProvider = ChangeNotifierProvider<OfflineQueue>((ref) {
  final q = OfflineQueue(
      storage: ref.watch(localStorageProvider), sender: (a) => sendQueuedAction(ref, a));
  q.load();
  ref.listen<AsyncValue<bool>>(onlineProvider, (_, n) {
    if (n.value == true) q.sync();
  });
  return q;
});

/// @brief Banner shown at the top when there is no connection.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final online = ref.watch(onlineProvider).value ?? true;
    if (online) return const SizedBox.shrink();
    final n = ref.watch(offlineQueueProvider).pending.length;
    return Semantics(
      liveRegion: true,
      label: 'Offline',
      child: Material(
        color: Theme.of(context).colorScheme.errorContainer,
        child: SizedBox(
          width: double.infinity,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            child: Text(
                n == 0
                    ? 'Offline - showing saved content'
                    : 'Offline - $n change${n == 1 ? '' : 's'} will sync when you reconnect',
                style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer)),
          ),
        ),
      ),
    );
  }
}

/// @brief Small "syncing" badge for queued items.
class PendingBadge extends StatelessWidget {
  const PendingBadge({super.key});
  @override
  Widget build(BuildContext context) => const Tooltip(
        message: 'Syncing',
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.schedule, size: 14),
          SizedBox(width: 4),
          Text('Syncing', style: TextStyle(fontSize: 12)),
        ]),
      );
}
