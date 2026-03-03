/**
 * @file composables/useSsoProviderForm.ts
 * @brief Composable for OAuth provider create/edit form state and actions.
 *
 * Manages form data, group mappings, discovery, and save logic.
 * Used by SsoProviderForm.vue.
 */

import type { Ref } from "vue";
import { ref, watch } from "vue";
import { useApi } from "~/composables/useApi";
import { useUiStore } from "~/stores/ui";
import type { OAuthProviderResponse, UserRole } from "~/types/api";

/** @brief Form state for OAuth provider. */
export interface SsoFormState {
  provider_type: "oidc" | "oauth2";
  display_name: string;
  slug: string;
  icon_url: string;
  issuer_url: string;
  authorization_endpoint: string;
  token_endpoint: string;
  userinfo_endpoint: string;
  jwks_uri: string;
  end_session_endpoint: string;
  client_id: string;
  client_secret: string;
  group_mappings: Record<string, UserRole>;
  default_role: UserRole;
  group_claim: string;
  scopes: string;
  sub_claim: string;
  email_claim: string;
  name_claim: string;
  avatar_claim: string;
  auto_create_users: boolean;
  enabled: boolean;
}

const defaultForm = (): SsoFormState => ({
  provider_type: "oidc",
  display_name: "",
  slug: "",
  icon_url: "",
  issuer_url: "",
  authorization_endpoint: "",
  token_endpoint: "",
  userinfo_endpoint: "",
  jwks_uri: "",
  end_session_endpoint: "",
  client_id: "",
  client_secret: "",
  group_mappings: {},
  default_role: "member",
  group_claim: "groups",
  scopes: "openid profile email groups",
  sub_claim: "sub",
  email_claim: "email",
  name_claim: "name",
  avatar_claim: "picture",
  auto_create_users: true,
  enabled: true,
});

/**
 * @brief Composable for SsoProviderForm.
 * @param provider - Provider to edit (undefined for create).
 */
export function useSsoProviderForm(
  provider: Ref<OAuthProviderResponse | null | undefined>,
) {
  const api = useApi();
  const uiStore = useUiStore();
  const { t: $t } = useI18n();
  const form = ref<SsoFormState>(defaultForm());
  const groupMappingsList = ref<{ idp_group: string; role: UserRole }[]>([]);
  const saving = ref(false);

  function syncFromProvider(p: OAuthProviderResponse): void {
    form.value = {
      provider_type: p.provider_type,
      display_name: p.display_name,
      slug: p.slug,
      icon_url: p.icon_url ?? "",
      issuer_url: p.issuer_url ?? "",
      authorization_endpoint: p.authorization_endpoint,
      token_endpoint: p.token_endpoint,
      userinfo_endpoint: p.userinfo_endpoint ?? "",
      jwks_uri: p.jwks_uri ?? "",
      end_session_endpoint: p.end_session_endpoint ?? "",
      client_id: p.client_id,
      client_secret: "",
      group_mappings: { ...p.group_mappings },
      default_role: p.default_role,
      group_claim: p.group_claim,
      scopes: p.scopes,
      sub_claim: p.sub_claim,
      email_claim: p.email_claim,
      name_claim: p.name_claim,
      avatar_claim: p.avatar_claim,
      auto_create_users: p.auto_create_users,
      enabled: p.enabled,
    };
    groupMappingsList.value = Object.entries(p.group_mappings).map(
      ([idp_group, role]) => ({ idp_group, role }),
    );
  }

  watch(
    provider,
    (p) => {
      if (p) syncFromProvider(p);
      else {
        form.value = defaultForm();
        groupMappingsList.value = [];
      }
    },
    { immediate: true },
  );

  function maybeSlugFromDisplayName(): void {
    if (!provider.value && !form.value.slug) {
      form.value.slug = form.value.display_name
        .toLowerCase()
        .replace(/\s+/g, "-")
        .replace(/[^a-z0-9-]/g, "");
    }
  }

  function addGroupMapping(): void {
    groupMappingsList.value.push({ idp_group: "", role: "member" });
  }

  function removeGroupMapping(idx: number): void {
    groupMappingsList.value.splice(idx, 1);
  }

  function syncGroupMappingsToForm(): void {
    const m: Record<string, UserRole> = {};
    for (const { idp_group, role } of groupMappingsList.value) {
      if (idp_group.trim()) m[idp_group.trim()] = role;
    }
    form.value.group_mappings = m;
  }

  async function discover(): Promise<void> {
    const issuer = form.value.issuer_url?.trim();
    if (!issuer) return;
    try {
      const data = await api.post<{
        authorization_endpoint?: string;
        token_endpoint?: string;
        userinfo_endpoint?: string;
        jwks_uri?: string;
        end_session_endpoint?: string;
      }>("/admin/oauth/discover", { issuer });
      if (data?.authorization_endpoint)
        form.value.authorization_endpoint = data.authorization_endpoint;
      if (data?.token_endpoint) form.value.token_endpoint = data.token_endpoint;
      if (data?.userinfo_endpoint)
        form.value.userinfo_endpoint = data.userinfo_endpoint ?? "";
      if (data?.jwks_uri) form.value.jwks_uri = data.jwks_uri ?? "";
      if (data?.end_session_endpoint)
        form.value.end_session_endpoint = data.end_session_endpoint ?? "";
      uiStore.showToast({
        type: "success",
        message: $t("admin.discoverySuccess"),
      });
    } catch {
      uiStore.showToast({
        type: "error",
        message: $t("admin.discoveryFailed"),
      });
    }
  }

  async function save(): Promise<boolean> {
    saving.value = true;
    syncGroupMappingsToForm();
    try {
      const payload = {
        ...form.value,
        client_secret: form.value.client_secret || undefined,
      };
      if (provider.value) {
        await api.put(`/admin/oauth/providers/${provider.value.id}`, payload);
      } else {
        await api.post("/admin/oauth/providers", payload);
      }
      return true;
    } catch (e) {
      uiStore.showToast({
        type: "error",
        message: e instanceof Error ? e.message : $t("common.error"),
      });
      return false;
    } finally {
      saving.value = false;
    }
  }

  return {
    form,
    groupMappingsList,
    saving,
    maybeSlugFromDisplayName,
    addGroupMapping,
    removeGroupMapping,
    discover,
    save,
  };
}
