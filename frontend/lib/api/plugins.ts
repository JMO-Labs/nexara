/**
 * @file lib/api/plugins.ts
 * @brief Admin plugin endpoints: list, install, uninstall, per-community
 *        enable/settings. Secret settings come back masked as {set: boolean}.
 */
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, seg } from "./client";

export type FieldType = "boolean" | "select" | "number" | "string" | "secret";

export interface FieldSpec {
  type: FieldType;
  label: string;
  help?: string | null;
  default?: unknown;
  options?: string[] | null;
  min?: number | null;
  max?: number | null;
  max_length?: number | null;
}

export interface PluginInstall {
  id: string;
  plugin_id: string;
  name: string;
  version: string;
  status: string;
  tier?: string | null;
  scopes: string[];
  events: string[];
  egress: string[];
  enabled: boolean;
  bot_user_id: string | null;
  settings_schema: Record<string, FieldSpec>;
}

export interface PluginCredentials {
  token: string;
  webhook_secret: string;
  community_id: string;
}

export interface PluginCommunity {
  plugin_id: string;
  enabled: boolean;
  bot_user_id: string | null;
  settings: Record<string, unknown>;
  credentials: PluginCredentials | null;
}

export interface InstallBody {
  manifest_url: string;
  endpoint_url: string;
  approved_scopes: string[];
}

const BASE = "/api/v1/plugins";

export const listPlugins = () => apiGet<PluginInstall[]>(BASE);
export const installPlugin = (b: InstallBody) =>
  apiPost<PluginInstall>(`${BASE}/install`, { source: "url", ...b });
export const uninstallPlugin = (pluginId: string, deleteContent = false) =>
  apiDelete(`${BASE}/${seg(pluginId)}`, {
    body: { delete_content: deleteContent },
  });
export const setPluginCommunity = (
  pluginId: string,
  communityId: string,
  body: { enabled?: boolean; settings?: Record<string, unknown> },
) =>
  apiPatch<PluginCommunity>(
    `${BASE}/${seg(pluginId)}/communities/${seg(communityId)}`,
    body,
  );
export const getPluginSettings = (pluginId: string) =>
  apiGet<Record<string, unknown>>(`${BASE}/${seg(pluginId)}/settings`);

export interface PluginUi {
  plugin_id: string;
  name: string;
  user_prefs: Record<string, FieldSpec>;
  composer_flags: Record<string, FieldSpec>;
}

/** Plugins enabled for the viewer's community (member-facing specs). */
export const listPluginUi = () => apiGet<PluginUi[]>(`${BASE}/ui`);
export const getPluginPrefs = (pluginId: string) =>
  apiGet<Record<string, unknown>>(`/api/v1/me/plugin-prefs/${seg(pluginId)}`);
export const putPluginPrefs = (
  pluginId: string,
  values: Record<string, unknown>,
) =>
  apiPut<Record<string, unknown>>(`/api/v1/me/plugin-prefs/${seg(pluginId)}`, {
    values,
  });
