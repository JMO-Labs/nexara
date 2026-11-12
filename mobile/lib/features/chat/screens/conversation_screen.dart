/// @file conversation_screen.dart
/// @brief Single conversation: history, live messages, typing indicator, composer.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../providers/chat_provider.dart';
import '../widgets/message_bubble.dart';

class ConversationScreen extends ConsumerStatefulWidget {
  const ConversationScreen({super.key, required this.chatId, required this.title, this.currentUserId});
  final String chatId;
  final String title;
  final String? currentUserId;
  @override
  ConsumerState<ConversationScreen> createState() => _ConversationScreenState();
}

class _ConversationScreenState extends ConsumerState<ConversationScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      // List is reversed: "extentAfter" is the distance toward older messages.
      if (_scroll.position.extentAfter < 300) {
        ref.read(conversationProvider(widget.chatId).notifier).loadOlder();
      }
    });
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _send() {
    final t = _input.text.trim();
    if (t.isEmpty) return;
    ref.read(sendMessageProvider)(widget.chatId, t);
    _input.clear();
  }

  @override
  Widget build(BuildContext context) {
    final s = ref.watch(conversationProvider(widget.chatId));
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(children: [
        Expanded(
          child: s.loading && s.messages.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : ListView.builder(
                  controller: _scroll,
                  reverse: true,
                  itemCount: s.messages.length,
                  itemBuilder: (_, i) => MessageBubble(
                      message: s.messages[i], mine: s.messages[i].authorId == widget.currentUserId),
                ),
        ),
        if (s.typing)
          const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Align(alignment: Alignment.centerLeft, child: Text('Someone is typing…'))),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Row(children: [
              IconButton(
                tooltip: 'Attach media',
                icon: const Icon(Icons.attach_file),
                onPressed: () => ImagePicker().pickImage(source: ImageSource.gallery),
              ),
              Expanded(
                child: TextField(
                  controller: _input,
                  onChanged: (_) => ref.read(sendTypingProvider)(widget.chatId),
                  decoration: const InputDecoration(hintText: 'Message', border: OutlineInputBorder()),
                ),
              ),
              IconButton(tooltip: 'Send message', icon: const Icon(Icons.send), onPressed: _send),
            ]),
          ),
        ),
      ]),
    );
  }
}
