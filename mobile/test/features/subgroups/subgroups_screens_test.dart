/// @file subgroups_screens_test.dart
/// @brief Widget tests for SubgroupsScreen and SubgroupDetailScreen (mocked API).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/features/subgroups/models.dart';
import 'package:nexara_mobile/features/subgroups/providers.dart';
import 'package:nexara_mobile/features/subgroups/subgroup_detail_screen.dart';
import 'package:nexara_mobile/features/subgroups/subgroups_screen.dart';

final _sg = Subgroup.fromJson({
  'id': 'g1',
  'name': 'Gardeners',
  'slug': 'gardeners',
  'description': 'We grow things',
  'is_private': false,
  'join_policy': 'open',
  'my_role': 'member',
  'member_count': 2,
});
final _members = [
  SubgroupMember.fromJson({'user_id': 'u1', 'role': 'owner', 'display_name': 'Ada', 'username': 'ada'}),
  SubgroupMember.fromJson({'user_id': 'u2', 'role': 'member', 'display_name': 'Bob', 'username': 'bob'}),
];

Widget _wrap(Widget child, List<Override> o) =>
    ProviderScope(overrides: o, child: MaterialApp(home: child));

void main() {
  testWidgets('list shows subgroups', (t) async {
    await t.pumpWidget(_wrap(const SubgroupsScreen(),
        [subgroupsProvider.overrideWith((_) async => [_sg])]));
    await t.pumpAndSettle();
    expect(find.text('Gardeners'), findsOneWidget);
    expect(find.text('We grow things'), findsOneWidget);
  });

  testWidgets('list shows empty state', (t) async {
    await t.pumpWidget(
        _wrap(const SubgroupsScreen(), [subgroupsProvider.overrideWith((_) async => [])]));
    await t.pumpAndSettle();
    expect(find.text('No subgroups yet'), findsOneWidget);
  });

  testWidgets('list shows error', (t) async {
    await t.pumpWidget(_wrap(const SubgroupsScreen(),
        [subgroupsProvider.overrideWith((_) async => throw Exception('boom'))]));
    await t.pumpAndSettle();
    expect(find.text('Could not load subgroups'), findsOneWidget);
  });

  testWidgets('detail shows info and members', (t) async {
    await t.pumpWidget(_wrap(const SubgroupDetailScreen(slug: 'gardeners'), [
      subgroupDetailProvider.overrideWith((_, __) async => _sg),
      subgroupMembersProvider.overrideWith((_, __) async => _members),
    ]));
    await t.pumpAndSettle();
    expect(find.text('Gardeners'), findsOneWidget);
    expect(find.text('We grow things'), findsOneWidget);
    expect(find.text('2 members'), findsOneWidget);
    expect(find.text('Ada'), findsOneWidget);
    expect(find.text('Bob'), findsOneWidget);
    expect(find.text('owner'), findsOneWidget);
  });
}
