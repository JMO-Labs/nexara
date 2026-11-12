/// @file platform_config_test.dart
/// @brief Guards native platform config required by plugins (nexara#287).
///
/// Runs from the `mobile/` package root (flutter test cwd).
library;

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// @brief Reads a file relative to the package root, failing clearly if absent.
/// @param path Relative path.
/// @return File contents.
String _read(String path) {
  final file = File(path);
  expect(file.existsSync(), isTrue, reason: '$path is missing');
  return file.readAsStringSync();
}

void main() {
  group('android', () {
    test('MainActivity extends FlutterFragmentActivity (local_auth)', () {
      final src = _read(
        'android/app/src/main/kotlin/dev/jmolabs/nexara_mobile/MainActivity.kt',
      );
      expect(src, contains('package dev.jmolabs.nexara_mobile'));
      expect(src, contains(': FlutterFragmentActivity()'));
    });

    test('manifest declares required permissions', () {
      final manifest = _read('android/app/src/main/AndroidManifest.xml');
      for (final p in [
        'INTERNET',
        'CAMERA',
        'ACCESS_FINE_LOCATION',
        'ACCESS_COARSE_LOCATION',
        'POST_NOTIFICATIONS',
        'USE_BIOMETRIC',
      ]) {
        expect(manifest, contains('android.permission.$p'), reason: p);
      }
    });

    test('application id uses dev.jmolabs org', () {
      final gradle = _read('android/app/build.gradle.kts');
      expect(gradle, contains('applicationId = "dev.jmolabs.nexara_mobile"'));
    });
  });

  group('ios', () {
    test('Info.plist declares usage descriptions', () {
      final plist = _read('ios/Runner/Info.plist');
      for (final key in [
        'NSCameraUsageDescription',
        'NSPhotoLibraryUsageDescription',
        'NSLocationWhenInUseUsageDescription',
        'NSFaceIDUsageDescription',
      ]) {
        expect(plist, contains('<key>$key</key>'), reason: key);
      }
    });
  });
}
