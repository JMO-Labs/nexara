/// @file feed_screen_test.dart
/// @brief Feed: initial load, pull-to-refresh, infinite scroll, post detail, realtime prepend.
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/providers.dart';
import 'package:nexara_mobile/features/feed/models/post_model.dart';
import 'package:nexara_mobile/features/feed/providers/feed_provider.dart';
import 'package:nexara_mobile/features/feed/screens/feed_screen.dart';

import '../../helpers/fake_realtime.dart';

FeedPost mkPost(int i) => FeedPost(
    id: '$i', content: 'Post $i', author: const Author(id: 'u', name: 'Ann'), createdAt: DateTime(2026, 1, 1));

class FakeFeedRepo implements FeedRepository {
  int feedCalls = 0;
  final cursors = <String?>[];

  @override
  Future<PagedResult<FeedPost>> feed({String? cursor, int limit = 20}) async {
    feedCalls++;
    cursors.add(cursor);
    if (cursor == null) return PagedResult([for (var i = 0; i < 20; i++) mkPost(i)], 'c1', true);
    return PagedResult([mkPost(100), mkPost(101)], null, false);
  }

  @override
  Future<FeedPost> post(String id) async => throw UnimplementedError();
  @override
  Future<List<PostComment>> comments(String id) async => [];
  @override
  Future<FeedPost> create(String content, {String? visibility, List<String> mediaIds = const []}) async =>
      throw UnimplementedError();
  @override
  Future<void> addComment(String postId, String content) async {}
  @override
  Future<void> react(String postId, String emoji) async {}
}

class DetailRepo extends FakeFeedRepo {
  @override
  Future<FeedPost> post(String id) async => FeedPost(
      id: id, content: 'Detail body $id', author: const Author(id: 'u', name: 'Ann'), createdAt: DateTime(2026, 1, 1));
}

Future<FakeRealtime> pump(WidgetTester t, FakeFeedRepo repo) async {
  final rt = FakeRealtime();
  await t.pumpWidget(ProviderScope(
    overrides: [feedRepositoryProvider.overrideWithValue(repo), realtimeClientProvider.overrideWithValue(rt)],
    child: const MaterialApp(home: FeedScreen()),
  ));
  await t.pumpAndSettle();
  return rt;
}

void main() {
  testWidgets('feed loads posts', (t) async {
    await pump(t, FakeFeedRepo());
    expect(find.text('Post 0'), findsOneWidget);
  });

  testWidgets('pull-to-refresh reloads', (t) async {
    final repo = FakeFeedRepo();
    await pump(t, repo);
    expect(repo.feedCalls, 1);
    await t.fling(find.byType(ListView), const Offset(0, 400), 1000);
    await t.pumpAndSettle();
    expect(repo.feedCalls, 2);
  });

  testWidgets('scrolling past the end loads next page', (t) async {
    final repo = FakeFeedRepo();
    await pump(t, repo);
    await t.drag(find.byType(ListView), const Offset(0, -6000));
    await t.pumpAndSettle();
    expect(repo.cursors, [null, 'c1']);
  });

  testWidgets('tap opens post detail', (t) async {
    await pump(t, DetailRepo());
    await t.tap(find.text('Post 0'));
    await t.pumpAndSettle();
    expect(find.text('Detail body 0'), findsOneWidget);
  });

  testWidgets('realtime post_created prepends to feed', (t) async {
    final rt = await pump(t, FakeFeedRepo());
    rt.emit('feed_update', {
      'event': 'created',
      'post': {'id': '999', 'content': 'Fresh', 'created_at': '2026-02-01T10:00:00Z', 'author': {'id': 'u', 'display_name': 'Bo'}},
    });
    await t.pumpAndSettle();
    expect(find.text('Fresh'), findsOneWidget);
  });
}
