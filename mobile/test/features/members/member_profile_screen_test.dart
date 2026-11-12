/// @file member_profile_screen_test.dart
/// @brief Widget tests for MemberProfileScreen (mocked API).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/features/members/member_profile_screen.dart';
import 'package:nexara_mobile/features/members/models.dart';
import 'package:nexara_mobile/features/members/providers.dart';

final _m = MemberProfile.fromJson({
  'id': 'u1',
  'username': 'ada',
  'display_name': 'Ada L',
  'bio': 'Maths',
  'title': 'Engineer',
  'pronouns': 'she/her',
  'location': 'London',
  'role': 'member',
});

void main() {
  testWidgets('shows public profile', (t) async {
    await t.pumpWidget(ProviderScope(
      overrides: [memberProfileProvider.overrideWith((_, __) async => _m)],
      child: const MaterialApp(home: MemberProfileScreen(userId: 'u1')),
    ));
    await t.pumpAndSettle();
    expect(find.text('Ada L'), findsOneWidget);
    expect(find.text('@ada'), findsOneWidget);
    expect(find.text('Maths'), findsOneWidget);
    expect(find.text('Engineer'), findsOneWidget);
    expect(find.text('she/her'), findsOneWidget);
    expect(find.text('London'), findsOneWidget);
  });

  testWidgets('shows error', (t) async {
    await t.pumpWidget(ProviderScope(
      overrides: [memberProfileProvider.overrideWith((_, __) async => throw Exception('x'))],
      child: const MaterialApp(home: MemberProfileScreen(userId: 'u1')),
    ));
    await t.pumpAndSettle();
    expect(find.text('Could not load profile'), findsOneWidget);
  });
}
