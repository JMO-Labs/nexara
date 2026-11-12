# Nexara mobile

Flutter client. Run `flutter pub get`, then `dart run build_runner build`
only if you change `@JsonSerializable` models (generated `*.g.dart` files are committed).

    flutter test
    flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

Native `android/` and `ios/` folders are generated with `flutter create . --platforms android,ios`.
