/// @file image_picker_test.dart
/// @brief Picker wrapper returns files / null with a mocked source.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/media/camera_service.dart';
import 'package:nexara_mobile/core/media/image_picker_service.dart';

class FakeSource implements PickerSource {
  FakeSource(this.paths);
  final List<String> paths;
  @override
  Future<String?> pick(PickSource s) async => paths.isEmpty ? null : paths.first;
  @override
  Future<List<String>> pickMany() async => paths;
}

void main() {
  test('gallery and camera return files', () async {
    final s = ImagePickerService(FakeSource(['/tmp/a.jpg']));
    expect((await s.pickFromGallery())!.path, '/tmp/a.jpg');
    expect(await s.pickFromCamera(), isA<File>());
  });
  test('cancel returns null', () async {
    final s = ImagePickerService(FakeSource([]));
    expect(await s.pickFromGallery(), isNull);
    expect(await s.pickMultiple(), isEmpty);
  });
  test('pickMultiple returns all', () async {
    final s = ImagePickerService(FakeSource(['/a', '/b']));
    expect((await s.pickMultiple()).length, 2);
  });
  test('takePhoto delegates to camera capture', () async {
    final c = CameraService(capture: () async => '/tmp/p.jpg');
    expect((await c.takePhoto())!.path, '/tmp/p.jpg');
  });
}
