/// @file subgroup_detail_screen.dart
/// @brief Subgroup info plus member list.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../members/member_profile_screen.dart';
import 'providers.dart';

/// @brief Shows a subgroup's details and members; member tap opens their profile.
class SubgroupDetailScreen extends ConsumerWidget {
  const SubgroupDetailScreen({super.key, required this.slug});
  final String slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sg = ref.watch(subgroupDetailProvider(slug));
    final members = ref.watch(subgroupMembersProvider(slug));
    return Scaffold(
      appBar: AppBar(title: const Text('Subgroup')),
      body: sg.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('Could not load subgroup')),
        data: (s) => ListView(children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(s.name, style: Theme.of(context).textTheme.headlineSmall),
              if (s.description != null) Text(s.description!),
              if (s.memberCount != null) Text('${s.memberCount} members'),
            ]),
          ),
          const Divider(),
          members.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (_, __) => const ListTile(title: Text('Could not load members')),
            data: (list) => Column(children: [
              for (final m in list)
                ListTile(
                  leading: CircleAvatar(child: Text(m.label.characters.first.toUpperCase())),
                  title: Text(m.label),
                  trailing: Text(m.role),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                      builder: (_) => MemberProfileScreen(userId: m.userId))),
                ),
            ]),
          ),
        ]),
      ),
    );
  }
}
