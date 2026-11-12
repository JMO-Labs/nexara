/// @file settings_screen.dart
/// @brief Per-channel notification preferences and biometric unlock toggle.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';

const _types = {
  'mention': 'Mentions',
  'comment': 'Comments',
  'reaction': 'Reactions',
  'new_post': 'New posts',
  'system': 'System',
  'invite_accepted': 'Invites accepted',
};

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});
  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  Map<String, bool>? _prefs;
  bool _bioAvailable = false, _bioEnabled = false, _loadFailed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final bio = ref.read(biometricSettingsProvider);
      final prefs = await ref.read(settingsApiProvider).getPrefs();
      final avail = await bio.isAvailable();
      final enabled = await bio.isEnabled();
      if (!mounted) return;
      setState(() {
        _prefs = {...prefs};
        _bioAvailable = avail;
        _bioEnabled = enabled;
      });
    } catch (_) {
      if (mounted) setState(() => _loadFailed = true);
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<void> _save() async {
    try {
      await ref.read(settingsApiProvider).savePrefs(_prefs!);
      _snack('Settings saved');
    } catch (_) {
      _snack('Could not save settings');
    }
  }

  Future<void> _toggleBio(bool v) async {
    final r = await ref.read(biometricSettingsProvider).setEnabled(v);
    if (mounted) setState(() => _bioEnabled = r);
  }

  Widget _channel(String type, String label) => Row(children: [
        Expanded(child: Text(label)),
        for (final ch in const ['inapp', 'email'])
          Column(children: [
            Text(ch == 'inapp' ? 'In-app' : 'Email', style: Theme.of(context).textTheme.labelSmall),
            Switch(
              key: Key('notif_${type}_$ch'),
              value: _prefs!['notif_${type}_$ch'] ?? false,
              onChanged: (v) => setState(() => _prefs!['notif_${type}_$ch'] = v),
            ),
          ]),
      ]);

  @override
  Widget build(BuildContext context) {
    final prefs = _prefs;
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: _loadFailed
          ? const Center(child: Text('Could not load settings'))
          : prefs == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(padding: const EdgeInsets.all(16), children: [
                  Text('Notifications', style: Theme.of(context).textTheme.titleMedium),
                  for (final e in _types.entries) _channel(e.key, e.value),
                  FilledButton(onPressed: _save, child: const Text('Save')),
                  const Divider(height: 32),
                  SwitchListTile(
                    key: const Key('biometric_switch'),
                    title: const Text('Biometric unlock'),
                    subtitle: Text(_bioAvailable ? 'Unlock with fingerprint or face' : 'Not available on this device'),
                    value: _bioEnabled,
                    onChanged: _bioAvailable ? _toggleBio : null,
                  ),
                ]),
    );
  }
}
