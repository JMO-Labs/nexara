/// @file member_profile_screen.dart
/// @brief Shows a member's public profile.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers.dart';

/// @brief Public profile screen for the user with [userId].
class MemberProfileScreen extends ConsumerWidget {
  const MemberProfileScreen({super.key, required this.userId});
  final String userId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(memberProfileProvider(userId));
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('Could not load profile')),
        data: (m) {
          Widget row(IconData i, String? v) => v == null
              ? const SizedBox.shrink()
              : ListTile(leading: Icon(i), title: Text(v));
          return ListView(padding: const EdgeInsets.all(16), children: [
            Center(
              child: CircleAvatar(
                radius: 40,
                backgroundImage: m.avatarUrl == null ? null : NetworkImage(m.avatarUrl!),
                child: m.avatarUrl == null ? Text(m.displayName.characters.first) : null,
              ),
            ),
            const SizedBox(height: 12),
            Center(child: Text(m.displayName, style: Theme.of(context).textTheme.headlineSmall)),
            Center(child: Text('@${m.username}')),
            const SizedBox(height: 12),
            row(Icons.work_outline, m.title),
            row(Icons.badge_outlined, m.pronouns),
            row(Icons.place_outlined, m.location),
            row(Icons.link, m.websiteUrl),
            row(Icons.info_outline, m.bio),
          ]);
        },
      ),
    );
  }
}
