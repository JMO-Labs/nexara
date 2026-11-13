/// @file camera_service.dart
/// @brief Camera capture: opens the system camera and returns the photo.
import 'dart:io';

import 'image_picker_service.dart';

class CameraService {
  /// @param capture override for tests; defaults to the platform camera.
  CameraService({Future<String?> Function()? capture})
      : _capture = capture ?? (() => PluginPickerSource().pick(PickSource.camera));
  final Future<String?> Function() _capture;

  /// @return captured photo, or null if cancelled.
  Future<File?> takePhoto() async {
    final p = await _capture();
    return p == null ? null : File(p);
  }
}
