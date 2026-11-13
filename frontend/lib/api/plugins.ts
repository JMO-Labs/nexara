/**
 * @file lib/api/plugins.ts
 * @brief Plugin admin API calls and TanStack Query hooks.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut, seg } from "./client";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import { qk } from "@/lib/query-keys";

/** @brief Installed plugin summary. */
export interface Plugin {
  id: string;
  name: string;
  version: string;
  is_enabled: boolean;
  description: string;
}

/** @brief One declared plugin setting. */
export interface SettingSpec {
  type: "string" | "integer" | "boolean" | "number";
  label: string;
  required?: boolean;
  secret?: boolean;
  default?: unknown;
}

/** @brief Plugin manifest as served by the API. */
export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  min_core_version?: string;
  permissions: string[];
  settings: Record<string, SettingSpec>;
}

/** @brief Install staging response with permissions diff. */
export interface InstallReview {
  plugin_id: string;
  manifest: PluginManifest;
  permissions_requested: string[];
  permissions_previously_granted: string[];
  new_permissions: string[];
  removed_permissions: string[];
}

/** @brief Install confirmation response; api_key is shown once. */
export interface InstallResult extends Plugin {
  permissions_granted: string[];
  api_key: string;
}

/** @brief Masked API key metadata. */
export interface PluginApiKey {
  id: string;
  plugin_id: string;
  masked_key: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

/** @brief Newly created key including the plaintext secret. */
export interface PluginApiKeyCreated extends PluginApiKey {
  key: string;
}

const P = "/api/v1/plugins";
const A = "/api/v1/admin/plugins";

/** @brief List installed plugins. */
export const useGetPlugins = () =>
  useQuery({
    queryKey: qk.admin.plugins(),
    queryFn: () => apiGet<Plugin[]>(P),
  });

/** @brief Fetch a plugin manifest. */
export const useGetPluginManifest = (id: string) =>
  useQuery({
    queryKey: [...qk.admin.plugin(id), "manifest"],
    queryFn: () => apiGet<PluginManifest>(`${P}/${seg(id)}/manifest`),
  });

/** @brief Fetch plugin settings (secrets masked by the server). */
export const useGetPluginSettings = (id: string) =>
  useQuery({
    queryKey: [...qk.admin.plugin(id), "settings"],
    queryFn: () =>
      apiGet<{ settings: Record<string, unknown> }>(`${P}/${seg(id)}/settings`),
  });

/** @brief Stage an install; resolves with the permissions diff. */
export const useInstallRequest = (pluginId: string) =>
  useMutationWithToast({
    mutationFn: () =>
      apiPost<InstallReview>(`${A}/install-request`, { plugin_id: pluginId }),
  });

/** @brief Confirm a staged install. */
export const useInstallConfirm = (pluginId: string) => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: () =>
      apiPost<InstallResult>(`${A}/install-confirm`, { plugin_id: pluginId }),
    successKey: "toasts.plugins.installed",
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin.plugins() }),
  });
};

/** @brief Save plugin settings; call mutate(settings). */
export const useUpdatePluginSettings = (pluginId: string) => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (settings: Record<string, unknown>) =>
      apiPut<{ settings: Record<string, unknown> }>(
        `${P}/${seg(pluginId)}/settings`,
        { settings },
      ),
    successKey: "toasts.plugins.settings_saved",
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.admin.plugin(pluginId) }),
  });
};

/** @brief List masked API keys. */
export const useGetPluginApiKeys = (pluginId: string) =>
  useQuery({
    queryKey: qk.admin.pluginKeys(pluginId),
    queryFn: () => apiGet<PluginApiKey[]>(`${A}/${seg(pluginId)}/api-keys`),
  });

/** @brief Generate an API key (plaintext returned once). */
export const useGeneratePluginApiKey = (pluginId: string) => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: () =>
      apiPost<PluginApiKeyCreated>(`${A}/${seg(pluginId)}/api-keys`),
    successKey: "toasts.plugins.key_created",
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.admin.pluginKeys(pluginId) }),
  });
};

/** @brief Revoke an API key; call mutate(keyId). */
export const useRevokePluginApiKey = (pluginId: string) => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (keyId: string) =>
      apiDelete<PluginApiKey>(`${A}/${seg(pluginId)}/api-keys/${seg(keyId)}`),
    successKey: "toasts.plugins.key_revoked",
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.admin.pluginKeys(pluginId) }),
  });
};

/** @brief Enable or disable a plugin; call mutate(enabled). */
export const useTogglePlugin = (pluginId: string) => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (enabled: boolean) =>
      apiPut<Plugin>(`${P}/${seg(pluginId)}/${enabled ? "enable" : "disable"}`),
    silentSuccess: true,
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin.plugins() }),
  });
};

/** @brief Uninstall a plugin. */
export const useUninstallPlugin = (pluginId: string) => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: () => apiDelete<Plugin>(`${P}/${seg(pluginId)}`),
    successKey: "toasts.plugins.uninstalled",
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin.plugins() }),
  });
};
