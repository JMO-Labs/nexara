/// @file chat_provider.dart
/// @brief Riverpod providers for chat list, conversations, sending and typing state.
import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../../../core/realtime/websocket.dart';
import '../../feed/models/post_model.dart';
import '../models/chat_models.dart';

class ChatRepository {
  ChatRepository(this._dio);
  final Dio _dio;

  Future<List<Channel>> channels() async {
    final r = await _dio.get('/chat/channels');
    return [for (final c in r.data as List) Channel.fromJson(c as Map<String, dynamic>)];
  }

  /// @brief Newest-first page; `cursor` loads older messages.
  Future<PagedResult<ChatMessage>> history(String channelId, {String? cursor}) async {
    final r = await _dio.get('/chat/channels/$channelId/messages',
        queryParameters: {'limit': 50, if (cursor != null) 'cursor': cursor});
    final d = r.data as Map<String, dynamic>;
    return PagedResult([for (final m in d['items'] as List) ChatMessage.fromJson(m as Map<String, dynamic>)],
        d['cursor'] as String?, d['has_more'] == true);
  }
}

final chatRepositoryProvider =
    Provider<ChatRepository>((ref) => ChatRepository(ref.watch(apiClientProvider).dio));

/// @brief The shared realtime connection (alias for readability in chat code).
final webSocketProvider = Provider<RealtimeClient>((ref) => ref.watch(realtimeClientProvider));

/// @brief Channels list; bumps last-message preview on incoming `chat.message`.
class ChatListNotifier extends StateNotifier<AsyncValue<List<Channel>>> {
  ChatListNotifier(this._repo) : super(const AsyncValue.loading()) {
    load();
  }
  final ChatRepository _repo;

  Future<void> load() async {
    state = await AsyncValue.guard(_repo.channels);
  }

  void onMessage(ChatMessage m) {
    final list = state.valueOrNull;
    if (list == null) return;
    state = AsyncValue.data([for (final c in list) c.id == m.channelId ? c.withLast(m.content) : c]);
  }
}

final chatListProvider = StateNotifierProvider<ChatListNotifier, AsyncValue<List<Channel>>>((ref) {
  final n = ChatListNotifier(ref.watch(chatRepositoryProvider));
  final sub = ref.watch(webSocketProvider).messages.listen((m) {
    if (m.type == 'chat.message') n.onMessage(ChatMessage.fromJson(m.payload));
  });
  ref.onDispose(sub.cancel);
  return n;
});

class ConversationState {
  const ConversationState({this.messages = const [], this.cursor, this.hasMore = true, this.loading = true, this.typing = false});
  final List<ChatMessage> messages; // newest first
  final String? cursor;
  final bool hasMore;
  final bool loading;
  final bool typing;
  ConversationState copyWith({List<ChatMessage>? messages, String? cursor, bool? hasMore, bool? loading, bool? typing}) =>
      ConversationState(
          messages: messages ?? this.messages,
          cursor: cursor ?? this.cursor,
          hasMore: hasMore ?? this.hasMore,
          loading: loading ?? this.loading,
          typing: typing ?? this.typing);
}

class ConversationNotifier extends StateNotifier<ConversationState> {
  ConversationNotifier(this._repo, this.chatId) : super(const ConversationState()) {
    _load();
  }
  final ChatRepository _repo;
  final String chatId;

  Future<void> _load() async {
    try {
      final p = await _repo.history(chatId);
      state = state.copyWith(messages: p.items, cursor: p.cursor, hasMore: p.hasMore, loading: false);
    } catch (_) {
      state = state.copyWith(loading: false);
    }
  }

  /// @brief Lazy-load older messages when scrolling up.
  Future<void> loadOlder() async {
    if (state.loading || !state.hasMore || state.cursor == null) return;
    state = state.copyWith(loading: true);
    try {
      final p = await _repo.history(chatId, cursor: state.cursor);
      state = state.copyWith(
          messages: [...state.messages, ...p.items], cursor: p.cursor, hasMore: p.hasMore, loading: false);
    } catch (_) {
      state = state.copyWith(loading: false);
    }
  }

  void receive(ChatMessage m) {
    if (m.channelId != chatId || state.messages.any((x) => x.id == m.id)) return;
    state = state.copyWith(messages: [m, ...state.messages], typing: false);
  }

  Timer? _typingTimer;

  /// @brief Show the typing indicator; auto-clears after 3 seconds of silence.
  void setTyping(bool v) {
    _typingTimer?.cancel();
    state = state.copyWith(typing: v);
    if (v) _typingTimer = Timer(const Duration(seconds: 3), () => setTyping(false));
  }

  @override
  void dispose() {
    _typingTimer?.cancel();
    super.dispose();
  }
}

final conversationProvider =
    StateNotifierProvider.family<ConversationNotifier, ConversationState, String>((ref, chatId) {
  final n = ConversationNotifier(ref.watch(chatRepositoryProvider), chatId);
  final sub = ref.watch(webSocketProvider).messages.listen((m) {
    if (m.type == 'chat.message') n.receive(ChatMessage.fromJson(m.payload));
    if (m.type == 'chat.typing' && m.payload['channel_id']?.toString() == chatId) {
      final me = ref.read(currentUserIdProvider).valueOrNull;
      if (me == null || m.payload['user_id']?.toString() != me) n.setTyping(true);
    }
  });
  ref.onDispose(sub.cancel);
  return n;
});

/// @brief Mutation: send a message over the WebSocket (server echoes it back as `chat.message`).
final sendMessageProvider = Provider<void Function(String chatId, String content)>((ref) {
  return (chatId, content) =>
      ref.read(webSocketProvider).send('chat.message', {'channel_id': chatId, 'content': content});
});

/// @brief Notify peers that the current user is typing (throttled to once per 2s).
final sendTypingProvider = Provider<void Function(String chatId)>((ref) {
  DateTime? last;
  return (chatId) {
    final now = DateTime.now();
    if (last != null && now.difference(last!) < const Duration(seconds: 2)) return;
    last = now;
    ref.read(webSocketProvider).send('chat.typing', {'channel_id': chatId});
  };
});
