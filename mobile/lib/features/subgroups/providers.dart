/// @file providers.dart
/// @brief Riverpod providers for subgroup list, detail and members.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'models.dart';

final subgroupsProvider = FutureProvider.autoDispose<List<Subgroup>>((ref) async {
  final r = await ref.watch(apiClientProvider).dio.get<List<dynamic>>('/subgroups');
  return (r.data ?? []).map((e) => Subgroup.fromJson(e as Map<String, dynamic>)).toList();
});

final subgroupDetailProvider =
    FutureProvider.autoDispose.family<Subgroup, String>((ref, slug) async {
  final r = await ref.watch(apiClientProvider).dio.get<Map<String, dynamic>>('/subgroups/$slug');
  return Subgroup.fromJson(r.data!);
});

final subgroupMembersProvider =
    FutureProvider.autoDispose.family<List<SubgroupMember>, String>((ref, slug) async {
  final r = await ref.watch(apiClientProvider).dio.get<List<dynamic>>('/subgroups/$slug/members');
  return (r.data ?? []).map((e) => SubgroupMember.fromJson(e as Map<String, dynamic>)).toList();
});
