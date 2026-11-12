/// @file notifications_screen_test.dart
/// @brief Widget tests for NotificationsScreen (mocked API).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/features/notifications/notifications_api.dart';
import 'package:nexara_mobile/features/notifications/screens/notifications_screen.dart';

class FakeApi implements NotificationsApi {
  FakeApi(this.items);
  List<AppNotification> items;
  final read = <String>[];
  @override
  Future<List<AppNotification>> list() async => items;
  @override
  Future<void> markRead(String id) async => read.add(id);
}

AppNotification n(String id, String msg, DateTime at, {bool isRead = false}) =>
    AppNotification(id: id, type: 'mention', message: msg, createdAt: at, readAt: isRead ? at : null);

Widget host(FakeApi api) => ProviderScope(
      overrides: [notificationsApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: NotificationsScreen()),
    );

void main() {
  testWidgets('lists newest first with unread styling', (t) async {
    final api = FakeApi([
      n('1', 'older', DateTime(2026, 1, 1), isRead: true),
      n('2', 'newer', DateTime(2026, 1, 3)),
    ]);
    await t.pumpWidget(host(api));
    await t.pumpAndSettle();
    expect(t.getTopLeft(find.text('newer')).dy < t.getTopLeft(find.text('older')).dy, isTrue);
    expect(t.widget<Text>(find.text('newer')).style?.fontWeight, FontWeight.bold);
    expect(t.widget<Text>(find.text('older')).style?.fontWeight, isNot(FontWeight.bold));
  });

  testWidgets('tap marks notification read', (t) async {
    final api = FakeApi([n('2', 'newer', DateTime(2026, 1, 3))]);
    await t.pumpWidget(host(api));
    await t.pumpAndSettle();
    await t.tap(find.text('newer'));
    await t.pumpAndSettle();
    expect(api.read, ['2']);
  });

  testWidgets('shows empty state', (t) async {
    await t.pumpWidget(host(FakeApi([])));
    await t.pumpAndSettle();
    expect(find.text('No notifications'), findsOneWidget);
  });
}
