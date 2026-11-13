# Mobile App

Nexara ships a Flutter client for Android and iOS in `mobile/`.

## Prerequisites

| Tool            | Version  | Purpose                         |
| --------------- | -------- | ------------------------------- |
| Flutter SDK     | Dart 3.8+ | Build and run the app          |
| Android Studio  | latest   | Android SDK and emulator        |
| Xcode (macOS)   | latest   | iOS builds and simulator        |
| Nexara backend  | running  | API the app talks to            |

## Point the app at a server

The server URL is set at build time with `API_BASE_URL`:

```bash
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

`10.0.2.2` is the Android emulator's alias for the host machine. On the iOS
simulator use `http://localhost:8000/api/v1`; on a physical device use your
server's reachable URL (HTTPS recommended).

## Run the tests

```bash
cd mobile
flutter test
```

Run `dart run build_runner build` only if you change `@JsonSerializable`
models; generated `*.g.dart` files are committed.

## Native push (FCM)

Native push uses Firebase Cloud Messaging for both Android and iOS.

### Create the Firebase project

1. Create a project in the [Firebase console](https://console.firebase.google.com).
2. Add an **Android** app with package name `dev.jmolabs.nexara_mobile` (check
   `mobile/android/app/build.gradle*` for the exact application id) and
   download `google-services.json` into `mobile/android/app/`.
3. Add an **iOS** app with the bundle id from Xcode and download
   `GoogleService-Info.plist` into `mobile/ios/Runner/`.
4. For iOS, upload an APNs authentication key (Apple Developer account,
   `.p8`) under Project settings -> Cloud Messaging.
5. Under Project settings -> Service accounts, generate a new private key.
   This JSON file is the backend credential.

Do not commit these credential files.

### Configure the backend

Set `FCM_CREDENTIALS_FILE` to the path of the service-account JSON:

```bash
FCM_CREDENTIALS_FILE=/run/secrets/fcm-service-account.json
```

Mount the file read-only into the API and Celery worker containers. When the
variable is unset the FCM channel is disabled and notifications skip it
(`fcm_not_configured`); in-app, Web Push and email are unaffected.

The app registers its device token via `POST /api/v1/push/devices` after
login and removes it with `DELETE /api/v1/push/devices/{token}` on logout.
Invalid tokens reported by FCM are deactivated automatically.

## Features

- **Feed**: community posts, with pull-to-refresh
- **Chat**: realtime messaging over WebSocket
- **Events**: browse events and RSVP
- **Galleries**: view albums; upload from camera or gallery
- **Subgroups**: browse and open subgroups you belong to
- **Notifications**: in-app list and native push
- **Settings**: profile, notification preferences, biometric toggle
- **Offline mode**: cached reads and a queue for writes made offline, replayed
  when connectivity returns
- **Biometric unlock**: optional fingerprint/Face ID lock on app launch

## Building releases

Release builds and store publishing are out of scope here (see #135).
For local artifacts: `flutter build apk` and `flutter build ios --no-codesign`.
