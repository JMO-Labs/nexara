/// @file settings_api.dart
/// @brief Notification preferences API client.
import '../../core/api/api_client.dart';

abstract class SettingsApi {
  Future<Map<String, bool>> getPrefs();
  Future<void> savePrefs(Map<String, bool> prefs);
}

class HttpSettingsApi implements SettingsApi {
  HttpSettingsApi(this._api);
  final ApiClient _api;

  @override
  Future<Map<String, bool>> getPrefs() async {
    final r = await _api.dio.get('/settings/notifications');
    return {
      for (final e in (r.data as Map).entries)
        if (e.value is bool) e.key as String: e.value as bool
    };
  }

  @override
  Future<void> savePrefs(Map<String, bool> prefs) =>
      _api.dio.put('/settings/notifications', data: prefs);
}
