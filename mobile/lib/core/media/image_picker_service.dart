/// @file image_picker_service.dart
/// @brief Wrapper around the image_picker plugin returning File or null.
import 'dart:io';

import 'package:image_picker/image_picker.dart';

enum PickSource { gallery, camera }

abstract class PickerSource {
  Future<String?> pick(PickSource s);
  Future<List<String>> pickMany();
}

class PluginPickerSource implements PickerSource {
  final _p = ImagePicker();
  @override
  Future<String?> pick(PickSource s) async => (await _p.pickImage(
          source: s == PickSource.camera ? ImageSource.camera : ImageSource.gallery))
      ?.path;
  @override
  Future<List<String>> pickMany() async => (await _p.pickMultiImage()).map((x) => x.path).toList();
}

class ImagePickerService {
  ImagePickerService([PickerSource? source]) : _s = source ?? PluginPickerSource();
  final PickerSource _s;

  Future<File?> _f(Future<String?> p) async {
    final path = await p;
    return path == null ? null : File(path);
  }

  Future<File?> pickFromGallery() => _f(_s.pick(PickSource.gallery));
  Future<File?> pickFromCamera() => _f(_s.pick(PickSource.camera));
  Future<List<File>> pickMultiple() async => (await _s.pickMany()).map(File.new).toList();
}
