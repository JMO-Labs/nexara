/// @file post_composer_test.dart
/// @brief Composer must not offer visibility/media it cannot send; payload is content only.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/features/feed/models/post_model.dart';
import 'package:nexara_mobile/features/feed/providers/feed_provider.dart';
import 'package:nexara_mobile/features/feed/screens/post_composer_screen.dart';

import 'feed_screen_test.dart';

class CaptureRepo extends FakeFeedRepo {
  final created = <String>[];
  @override
  Future<FeedPost> create(String content, {List<String> mediaIds = const []}) async {
    created.add(content);
    return mkPost(1);
  }
}

void main() {
  testWidgets('no visibility selector or dead attach button; sends content only', (t) async {
    final repo = CaptureRepo();
    await t.pumpWidget(ProviderScope(
      overrides: [feedRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: PostComposerScreen()),
    ));
    expect(find.text('Visibility'), findsNothing);
    expect(find.text('Private'), findsNothing);
    expect(find.byIcon(Icons.image), findsNothing);
    await t.enterText(find.byType(TextField), 'hello');
    await t.tap(find.text('Post'));
    await t.pumpAndSettle();
    expect(repo.created, ['hello']);
  });
}
