# Nexara mobile

Flutter client. Run `flutter pub get`, then `dart run build_runner build`
only if you change `@JsonSerializable` models (generated `*.g.dart` files are committed).

    flutter test
    flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

Native platform folders live in `android/` and `ios/` (org `dev.jmolabs`).
Customised files (manifest permissions, `MainActivity` as `FlutterFragmentActivity`
for local_auth, `Info.plist` usage strings) are committed. Generated boilerplate
that is not committed (gradle wrapper, Xcode project) is filled in by
`flutter create . --platforms android,ios --org dev.jmolabs`, which never
overwrites existing files (delete any stray `test/widget_test.dart` it adds).

    flutter build apk
    flutter build ios --no-codesign
