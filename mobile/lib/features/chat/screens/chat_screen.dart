/// @file chat_screen.dart
/// @brief Conversation list with search.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../providers/chat_provider.dart';
import 'conversation_screen.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});
  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final chats = ref.watch(chatListProvider);
    ref.watch(currentUserIdProvider); // resolve early so taps have the id
    return Scaffold(
      appBar: AppBar(title: const Text('Chat')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: TextField(
            decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search), hintText: 'Search chats', border: OutlineInputBorder()),
            onChanged: (v) => setState(() => _q = v.toLowerCase()),
          ),
        ),
        Expanded(
          child: chats.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => const Center(child: Text('Could not load chats.')),
            data: (list) {
              final shown = list.where((c) => c.name.toLowerCase().contains(_q)).toList();
              return ListView(children: [
                for (final c in shown)
                  ListTile(
                    leading: Icon(c.type == 'direct' ? Icons.person : Icons.group),
                    title: Text(c.name),
                    subtitle: c.lastMessage == null ? null : Text(c.lastMessage!, maxLines: 1),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => ConversationScreen(
                            chatId: c.id, title: c.name, currentUserId: ref.read(currentUserIdProvider).valueOrNull))),
                  ),
              ]);
            },
          ),
        ),
      ]),
    );
  }
}
