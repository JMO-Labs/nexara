/// @file notifications_screen.dart
/// @brief Notifications list, newest first; tap marks as read.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../notifications_api.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificationsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Center(
          child: TextButton(
              onPressed: () => ref.invalidate(notificationsProvider),
              child: const Text('Could not load. Retry')),
        ),
        data: (items) => items.isEmpty
            ? const Center(child: Text('No notifications'))
            : RefreshIndicator(
                onRefresh: () => ref.refresh(notificationsProvider.future),
                child: ListView.builder(
                  itemCount: items.length,
                  itemBuilder: (_, i) {
                    final n = items[i];
                    return ListTile(
                      leading: Icon(n.unread ? Icons.circle : Icons.circle_outlined, size: 12,
                          semanticLabel: n.unread ? 'Unread' : 'Read'),
                      title: Text(n.message,
                          style: TextStyle(fontWeight: n.unread ? FontWeight.bold : FontWeight.normal)),
                      subtitle: Text(n.type),
                      onTap: () async {
                        if (n.unread) await ref.read(notificationsApiProvider).markRead(n.id);
                        ref.invalidate(notificationsProvider);
                      },
                    );
                  },
                ),
              ),
      ),
    );
  }
}
