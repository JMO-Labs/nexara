/// @file offline_banner_test.dart
/// @brief OfflineBanner: shown when offline (with pending count), hidden online.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/offline/connectivity_service.dart';
import 'package:nexara_mobile/core/providers.dart';
import 'package:nexara_mobile/core/storage/local_storage.dart';

class _FakeConnectivity implements ConnectivityService {
  _FakeConnectivity(this.online);
  final bool online;
  @override
  Future<bool> isOnline() async => online;
  @override
  Stream<bool> get onChanged => const Stream.empty();
}

void main() {
  late ProviderContainer container;

  Future<void> pump(WidgetTester tester, {required bool online}) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [
        connectivityServiceProvider.overrideWithValue(_FakeConnectivity(online)),
        localStorageProvider.overrideWithValue(MemoryLocalStorage()),
      ],
      child: const MaterialApp(home: Scaffold(body: OfflineBanner())),
    ));
    await tester.pumpAndSettle();
    container = ProviderScope.containerOf(tester.element(find.byType(OfflineBanner)));
  }

  testWidgets('shows offline message when there is no connection', (tester) async {
    await pump(tester, online: false);
    expect(find.text('Offline - showing saved content'), findsOneWidget);
  });

  testWidgets('shows pending count when items are queued', (tester) async {
    await pump(tester, online: false);
    // No runAsync: the queue's load future lives in the fake-async zone, so
    // awaiting it from the real zone would never complete (hang).
    final q = container.read(offlineQueueProvider);
    await q.enqueue('post', {'content': 'a'});
    await q.enqueue('post', {'content': 'b'});
    await tester.pumpAndSettle();
    expect(find.text('Offline - 2 changes will sync when you reconnect'), findsOneWidget);
  });

  testWidgets('renders nothing when online', (tester) async {
    await pump(tester, online: true);
    expect(find.textContaining('Offline'), findsNothing);
  });
}
