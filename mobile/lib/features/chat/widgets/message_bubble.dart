/// @file message_bubble.dart
/// @brief Single chat message bubble.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/chat_models.dart';

class MessageBubble extends StatelessWidget {
  const MessageBubble({super.key, required this.message, required this.mine});
  final ChatMessage message;
  final bool mine;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Semantics(
      label: '${message.authorName}: ${message.content}',
      child: Align(
        alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          padding: const EdgeInsets.all(10),
          constraints: const BoxConstraints(maxWidth: 300),
          decoration: BoxDecoration(
              color: mine ? cs.primaryContainer : cs.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (!mine) Text(message.authorName, style: Theme.of(context).textTheme.labelSmall),
            Text(message.content),
            Text(DateFormat.jm().format(message.createdAt), style: Theme.of(context).textTheme.labelSmall),
          ]),
        ),
      ),
    );
  }
}
