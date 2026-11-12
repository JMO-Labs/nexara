/// @file settings_screen_test.dart
/// @brief Widget tests for SettingsScreen (mocked API and biometrics).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/features/settings/providers.dart';
import 'package:nexara_mobile/features/settings/screens/settings_screen.dart';
import 'package:nexara_mobile/features/settings/settings_api.dart';

class FakeSettings implements SettingsApi {
  Map<String, bool> prefs = {'notif_mention_inapp': true, 'notif_mention_email': false};
  Map<String, bool>? saved;
  @override
  Future<Map<String, bool>> getPrefs() async => prefs;
  @override
  Future<void> savePrefs(Map<String, bool> p) async => saved = p;
}

class FakeBio implements BiometricSettings {
  FakeBio({this.available = true});
  final bool available;
  bool enabled = false;
  @override
  Future<bool> isAvailable() async => available;
  @override
  Future<bool> isEnabled() async => enabled;
  @override
  Future<bool> setEnabled(bool v) async => enabled = v;
}

Widget host(FakeSettings s, FakeBio b) => ProviderScope(
      overrides: [
        settingsApiProvider.overrideWithValue(s),
        biometricSettingsProvider.overrideWithValue(b),
      ],
      child: const MaterialApp(home: SettingsScreen()),
    );

void main() {
  testWidgets('shows saved prefs per channel', (t) async {
    await t.pumpWidget(host(FakeSettings(), FakeBio()));
    await t.pumpAndSettle();
    expect(t.widget<Switch>(find.byKey(const Key('notif_mention_inapp'))).value, isTrue);
    expect(t.widget<Switch>(find.byKey(const Key('notif_mention_email'))).value, isFalse);
  });

  testWidgets('toggling then Save sends prefs', (t) async {
    final s = FakeSettings();
    await t.pumpWidget(host(s, FakeBio()));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const Key('notif_mention_email')));
    await t.pump();
    await t.tap(find.text('Save'));
    await t.pumpAndSettle();
    expect(s.saved?['notif_mention_email'], isTrue);
    expect(s.saved?['notif_mention_inapp'], isTrue);
  });

  testWidgets('biometric toggle enables unlock', (t) async {
    final b = FakeBio();
    await t.pumpWidget(host(FakeSettings(), b));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const Key('biometric_switch')));
    await t.pumpAndSettle();
    expect(b.enabled, isTrue);
    expect(t.widget<SwitchListTile>(find.byKey(const Key('biometric_switch'))).value, isTrue);
  });

  testWidgets('biometric toggle disabled when unavailable', (t) async {
    await t.pumpWidget(host(FakeSettings(), FakeBio(available: false)));
    await t.pumpAndSettle();
    expect(t.widget<SwitchListTile>(find.byKey(const Key('biometric_switch'))).onChanged, isNull);
  });
}
