/// @file providers.dart
/// @brief Riverpod providers wiring storage, API client and auth service.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api/api_client.dart';
import 'auth/auth_service.dart';
import 'storage/local_storage.dart';

const apiBaseUrl =
    String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000/api/v1');

final tokenStoreProvider = Provider<TokenStore>((_) => SecureTokenStore());
final localStorageProvider = Provider<LocalStorage>((_) => MemoryLocalStorage());

final authServiceProvider = Provider<AuthService>((ref) {
  final tokens = ref.watch(tokenStoreProvider);
  late final AuthService svc;
  final api = ApiClient(baseUrl: apiBaseUrl, tokens: tokens, refresher: () => svc.refreshToken());
  return svc = AuthService(api: api, tokens: tokens);
});

final apiClientProvider = Provider<ApiClient>((ref) => ref.watch(authServiceProvider).api);
