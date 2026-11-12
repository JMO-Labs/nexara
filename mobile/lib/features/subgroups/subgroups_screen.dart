/// @file subgroups_screen.dart
/// @brief Lists subgroups from the subgroups API.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers.dart';
import 'subgroup_detail_screen.dart';

/// @brief Subgroup list; tapping a row opens SubgroupDetailScreen.
class SubgroupsScreen extends ConsumerWidget {
  const SubgroupsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(subgroupsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Subgroups')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Text('Could not load subgroups'),
            TextButton(
                onPressed: () => ref.invalidate(subgroupsProvider), child: const Text('Retry')),
          ]),
        ),
        data: (items) => items.isEmpty
            ? const Center(child: Text('No subgroups yet'))
            : RefreshIndicator(
                onRefresh: () => ref.refresh(subgroupsProvider.future),
                child: ListView.builder(
                  itemCount: items.length,
                  itemBuilder: (_, i) {
                    final s = items[i];
                    return ListTile(
                      leading: CircleAvatar(child: Text(s.name.characters.first.toUpperCase())),
                      title: Text(s.name),
                      subtitle: s.description == null ? null : Text(s.description!),
                      trailing: s.isPrivate ? const Icon(Icons.lock, semanticLabel: 'Private') : null,
                      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                          builder: (_) => SubgroupDetailScreen(slug: s.slug))),
                    );
                  },
                ),
              ),
      ),
    );
  }
}
