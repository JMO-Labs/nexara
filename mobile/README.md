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

## CI / release pipeline

- **Flutter pin**: `mobile/.flutter-version` is the source of truth. GitHub
  (`wq-workflows/mobile-build.yml`) and `scripts/wq-ci-test.sh` read it; GitLab mirrors it
  in `FLUTTER_VERSION` (`.gitlab/ci/variables.yml`). `scripts/test-mobile-ci.sh` fails on drift.
  Bump all together.
- **Lint/test**: `dart format --set-exit-if-changed`, `flutter analyze`, `flutter test`.
- **Signing**: `android/app/build.gradle.kts` reads `NEXARA_KEYSTORE_PATH`,
  `NEXARA_KEYSTORE_PASSWORD`, `NEXARA_KEY_ALIAS`, `NEXARA_KEY_PASSWORD` from env, else
  git-ignored `android/key.properties` (`storeFile`, `storePassword`, `keyAlias`,
  `keyPassword`); with neither it falls back to the debug key. CI builds both variants.
- **`build:mobile-aab`**: tag-only (`vX.Y.Z`), protected refs only; decodes
  `NEXARA_KEYSTORE_BASE64` and builds a signed AAB.
- **Fastlane** (`mobile/fastlane/`): `fastlane android beta` (Play internal) and
  `fastlane ios beta` (TestFlight); manual, protected tag jobs.

Required CI variables (protected, masked): `NEXARA_KEYSTORE_BASE64`,
`NEXARA_KEYSTORE_PASSWORD`, `NEXARA_KEY_ALIAS`, `NEXARA_KEY_PASSWORD`,
`PLAY_JSON_KEY_DATA`, `APP_STORE_CONNECT_API_KEY_ID`, `APP_STORE_CONNECT_ISSUER_ID`,
`APP_STORE_CONNECT_API_KEY_CONTENT`. The iOS lane also needs a macOS runner tagged `macos`
and `ios/ExportOptions.plist`. The macOS runner is not containerised, so it must provide
the pinned Flutter (`cat mobile/.flutter-version`) and fastlane itself; the pin is not applied there.

`wq-workflows/mobile-build.yml` is promoted by the owner to `.github/workflows/mobile-build.yml`
(the workflow's own `paths` filter already references that final path).
