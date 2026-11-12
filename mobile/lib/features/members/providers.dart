/// @file providers.dart
/// @brief Riverpod provider for a member's public profile.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'models.dart';

final memberProfileProvider =
    FutureProvider.autoDispose.family<MemberProfile, String>((ref, id) async {
  final r = await ref.watch(apiClientProvider).dio.get<Map<String, dynamic>>('/users/$id');
  return MemberProfile.fromJson(r.data!);
});
