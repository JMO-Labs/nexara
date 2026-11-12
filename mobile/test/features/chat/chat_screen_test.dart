/// @file chat_screen_test.dart
/// @brief Chat: list loads, WebSocket receive, send, typing indicator.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/providers.dart';
import 'package:nexara_mobile/features/chat/models/chat_models.dart';
import 'package:nexara_mobile/features/chat/providers/chat_provider.dart';
import 'package:nexara_mobile/features/chat/screens/chat_screen.dart';
import 'package:nexara_mobile/features/chat/screens/conversation_screen.dart';
import 'package:nexara_mobile/features/feed/models/post_model.dart';

import '../../helpers/fake_realtime.dart';

class FakeChatRepo implements ChatRepository {
  @override
  Future<List<Channel>> channels() async => [
        const Channel(id: 'c1', name: 'General', type: 'community'),
        const Channel(id: 'c2', name: 'Bob', type: 'direct'),
      ];

  @override
  Future<PagedResult<ChatMessage>> history(String channelId, {String? cursor}) async => PagedResult([
        ChatMessage(
            id: 'm1', channelId: channelId, authorId: 'u', authorName: 'Ann', content: 'older', createdAt: DateTime(2026, 1, 1)),
      ], null, false);
}

Map<String, dynamic> msg(String id, String content) => {
      'id': id,
      'channel_id': 'c1',
      'content': content,
      'created_at': '2026-02-01T10:00:00Z',
      'author': {'id': 'x', 'display_name': 'Bob'},
    };

Future<FakeRealtime> pump(WidgetTester t, Widget home) async {
  final rt = FakeRealtime();
  await t.pumpWidget(ProviderScope(
    overrides: [chatRepositoryProvider.overrideWithValue(FakeChatRepo()), realtimeClientProvider.overrideWithValue(rt)],
    child: MaterialApp(home: home),
  ));
  await t.pumpAndSettle();
  return rt;
}

void main() {
  testWidgets('chat list loads and filters by search', (t) async {
    await pump(t, const ChatScreen());
    expect(find.text('General'), findsOneWidget);
    expect(find.text('Bob'), findsOneWidget);
    await t.enterText(find.byType(TextField), 'bo');
    await t.pumpAndSettle();
    expect(find.text('General'), findsNothing);
  });

  testWidgets('message received via WebSocket appears', (t) async {
    final rt = await pump(t, const ConversationScreen(chatId: 'c1', title: 'General'));
    expect(find.text('older'), findsOneWidget);
    rt.emit('chat.message', msg('m2', 'hello live'));
    await t.pumpAndSettle();
    expect(find.text('hello live'), findsOneWidget);
  });

  testWidgets('message sends over WebSocket', (t) async {
    final rt = await pump(t, const ConversationScreen(chatId: 'c1', title: 'General'));
    await t.enterText(find.byType(TextField), 'hi there');
    await t.tap(find.byTooltip('Send message'));
    await t.pump();
    expect(rt.sent.where((s) => s.$1 == 'chat.message').single.$2, {'channel_id': 'c1', 'content': 'hi there'});
  });

  testWidgets('typing indicator shows then clears', (t) async {
    final rt = await pump(t, const ConversationScreen(chatId: 'c1', title: 'General'));
    rt.emit('chat.typing', {'channel_id': 'c1'});
    await t.pump();
    expect(find.text('Someone is typing…'), findsOneWidget);
    await t.pump(const Duration(seconds: 4));
    expect(find.text('Someone is typing…'), findsNothing);
  });
}
