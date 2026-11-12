/// @file galleries_screen_test.dart
/// @brief Widget tests for galleries list, detail grid and viewer (mocked repo).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/api/api_client.dart';
import 'package:nexara_mobile/features/galleries/galleries_screen.dart';
import 'package:nexara_mobile/features/galleries/gallery_models.dart';
import 'package:nexara_mobile/features/galleries/gallery_repository.dart';

class FakeRepo implements GalleryRepository {
  FakeRepo({this.galleries = const [], this.media = const [], this.fail = false});
  final List<Gallery> galleries;
  final List<GalleryItem> media;
  final bool fail;

  @override
  Future<List<Gallery>> list() async {
    if (fail) throw AppError('Cannot reach the server.');
    return galleries;
  }

  @override
  Future<List<GalleryItem>> items(String galleryId) async {
    if (fail) throw AppError('Cannot reach the server.');
    return media;
  }
}

Widget app(FakeRepo repo) => ProviderScope(
      overrides: [
        galleryRepositoryProvider.overrideWithValue(repo),
        imageHeadersProvider.overrideWith((_) async => <String, String>{}),
      ],
      child: const MaterialApp(home: GalleriesScreen()),
    );

const g1 = Gallery(id: 'g1', title: 'Summer BBQ', itemCount: 2);
final photos = [
  const GalleryItem(id: 'i1', mediaId: 'm1', caption: 'First'),
  const GalleryItem(id: 'i2', mediaId: 'm2', caption: 'Second'),
];

void main() {
  testWidgets('lists galleries', (t) async {
    await t.pumpWidget(app(FakeRepo(galleries: [g1])));
    await t.pumpAndSettle();
    expect(find.text('Summer BBQ'), findsOneWidget);
    expect(find.text('2 items'), findsOneWidget);
  });

  testWidgets('shows empty state', (t) async {
    await t.pumpWidget(app(FakeRepo()));
    await t.pumpAndSettle();
    expect(find.text('No galleries yet'), findsOneWidget);
  });

  testWidgets('shows error state with retry', (t) async {
    await t.pumpWidget(app(FakeRepo(fail: true)));
    await t.pumpAndSettle();
    expect(find.text('Cannot reach the server.'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('tap gallery opens detail grid', (t) async {
    await t.pumpWidget(app(FakeRepo(galleries: [g1], media: photos)));
    await t.pumpAndSettle();
    await t.tap(find.text('Summer BBQ'));
    await t.pumpAndSettle();
    expect(find.byType(GridView), findsOneWidget);
    expect(find.byKey(const ValueKey('thumb-i1')), findsOneWidget);
    expect(find.byKey(const ValueKey('thumb-i2')), findsOneWidget);
  });

  testWidgets('empty gallery shows empty state', (t) async {
    await t.pumpWidget(app(FakeRepo(galleries: [g1])));
    await t.pumpAndSettle();
    await t.tap(find.text('Summer BBQ'));
    await t.pumpAndSettle();
    expect(find.text('This gallery is empty'), findsOneWidget);
  });

  testWidgets('tap thumbnail opens swipeable viewer', (t) async {
    await t.pumpWidget(app(FakeRepo(galleries: [g1], media: photos)));
    await t.pumpAndSettle();
    await t.tap(find.text('Summer BBQ'));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('thumb-i1')));
    await t.pumpAndSettle();
    expect(find.text('1 / 2'), findsOneWidget);
    expect(find.text('First'), findsOneWidget);
    await t.fling(find.byType(PageView), const Offset(-400, 0), 1000);
    await t.pumpAndSettle();
    expect(find.text('2 / 2'), findsOneWidget);
    expect(find.text('Second'), findsOneWidget);
  });
}
