<!--
  @file components/admin/SsoProviderForm.vue
  @brief OAuth/OIDC provider add/edit form.

  Supports create and edit modes. Emits @saved on success, @cancelled on cancel.
  Sections: Basic Info, Connection, Credentials, Role Mapping, Advanced.
-->
<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    @click.self="$emit('cancelled')"
  >
    <div
      class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-border bg-card p-6"
    >
      <h3 class="mb-4 text-lg font-semibold text-foreground">
        {{ provider ? $t("admin.editProvider") : $t("admin.addProvider") }}
      </h3>

      <form class="space-y-6" @submit.prevent="handleSave">
        <fieldset class="space-y-3">
          <legend class="text-sm font-medium text-foreground">
            {{ $t("admin.displayName") }}
          </legend>
          <div class="grid gap-3 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm text-muted-foreground">
                {{ $t("admin.providerType") }}
              </label>
              <select
                v-model="form.provider_type"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
                <option value="oidc">OIDC</option>
                <option value="oauth2">OAuth2</option>
              </select>
            </div>
            <div v-for="f in basicFields" :key="f.key">
              <label class="mb-1 block text-sm text-muted-foreground">
                {{ f.labelKey ? $t(f.labelKey) : "Icon URL" }}
              </label>
              <input
                v-model="form[f.key]"
                :type="f.type"
                :placeholder="f.placeholder"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
                @input="f.key === 'display_name' && maybeSlugFromDisplayName()"
              >
            </div>
          </div>
        </fieldset>

        <fieldset class="space-y-3">
          <legend class="text-sm font-medium text-foreground">
            {{ $t("admin.connectionSettings") }}
          </legend>
          <div v-if="form.provider_type === 'oidc'" class="flex gap-2">
            <input
              v-model="form.issuer_url"
              type="url"
              :placeholder="$t('admin.issuerUrl')"
              class="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-foreground"
            >
            <button
              type="button"
              class="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent"
              @click="discover"
            >
              {{ $t("admin.discoverEndpoints") }}
            </button>
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <div v-for="ep in endpointFields" :key="ep.key">
              <label class="mb-1 block text-sm text-muted-foreground">
                {{ ep.label }}
              </label>
              <input
                v-model="form[ep.key]"
                type="url"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
            </div>
          </div>
        </fieldset>

        <fieldset class="space-y-3">
          <legend class="text-sm font-medium text-foreground">
            {{ $t("admin.credentials") }}
          </legend>
          <div class="grid gap-3 sm:grid-cols-2">
            <div v-for="c in credFields" :key="c.key">
              <label class="mb-1 block text-sm text-muted-foreground">
                {{ $t(c.i18n) }}
              </label>
              <input
                v-model="form[c.key]"
                :type="c.type"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
            </div>
          </div>
        </fieldset>

        <fieldset class="space-y-3">
          <legend class="text-sm font-medium text-foreground">
            {{ $t("admin.roleMapping") }}
          </legend>
          <div class="space-y-2">
            <div
              v-for="(entry, idx) in groupMappingsList"
              :key="idx"
              class="flex gap-2"
            >
              <input
                v-model="entry.idp_group"
                type="text"
                class="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-foreground"
                :placeholder="$t('admin.idpGroup')"
              >
              <select
                v-model="entry.role"
                class="w-32 rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
                <option value="admin">admin</option>
                <option value="member">member</option>
                <option value="viewer">viewer</option>
              </select>
              <button
                type="button"
                class="text-destructive hover:underline"
                @click="removeGroupMapping(idx)"
              >
                ×
              </button>
            </div>
            <button
              type="button"
              class="text-sm text-primary hover:underline"
              @click="addGroupMapping"
            >
              {{ $t("admin.addMapping") }}
            </button>
          </div>
          <div class="flex gap-4">
            <div>
              <label class="mb-1 block text-sm text-muted-foreground">
                {{ $t("admin.defaultRole") }}
              </label>
              <select
                v-model="form.default_role"
                class="rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
                <option value="admin">admin</option>
                <option value="member">member</option>
                <option value="viewer">viewer</option>
              </select>
            </div>
            <div>
              <label class="mb-1 block text-sm text-muted-foreground">
                {{ $t("admin.groupClaim") }}
              </label>
              <input
                v-model="form.group_claim"
                type="text"
                class="w-40 rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
            </div>
          </div>
        </fieldset>

        <fieldset class="space-y-3">
          <legend class="text-sm font-medium text-foreground">
            {{ $t("admin.advancedSettings") }}
          </legend>
          <div class="grid gap-3 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm text-muted-foreground">
                {{ $t("admin.scopes") }}
              </label>
              <input
                v-model="form.scopes"
                type="text"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
            </div>
            <div class="space-y-2">
              <div class="flex items-center gap-2">
                <input
                  id="auto_create"
                  v-model="form.auto_create_users"
                  type="checkbox"
                  class="h-4 w-4 rounded border-input text-primary"
                >
                <label for="auto_create" class="text-sm">
                  {{ $t("admin.autoCreateUsers") }}
                </label>
              </div>
              <div class="flex items-center gap-2">
                <input
                  id="enabled"
                  v-model="form.enabled"
                  type="checkbox"
                  class="h-4 w-4 rounded border-input text-primary"
                >
                <label for="enabled" class="text-sm">
                  {{ $t("admin.enabled") }}
                </label>
              </div>
            </div>
          </div>
          <div class="grid gap-3 sm:grid-cols-4">
            <div v-for="c in claimFields" :key="c.key">
              <label class="mb-1 block text-xs text-muted-foreground">
                {{ c.label }}
              </label>
              <input
                v-model="form[c.key]"
                type="text"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
            </div>
          </div>
        </fieldset>

        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent"
            @click="$emit('cancelled')"
          >
            {{ $t("common.cancel") }}
          </button>
          <button
            type="submit"
            :disabled="saving"
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {{ saving ? $t("common.loading") : $t("common.save") }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief SsoProviderForm — create/edit OAuth provider.
 */
import { toRef } from "vue";
import { useSsoProviderForm } from "~/composables/useSsoProviderForm";
import type { OAuthProviderResponse } from "~/types/api";

const props = defineProps<{
  /** @brief Provider to edit (undefined for create). */
  provider?: OAuthProviderResponse | null;
}>();

const emit = defineEmits<{ saved: []; cancelled: [] }>();

const providerRef = toRef(props, "provider");
const {
  form,
  groupMappingsList,
  saving,
  maybeSlugFromDisplayName,
  addGroupMapping,
  removeGroupMapping,
  discover,
  save,
} = useSsoProviderForm(providerRef);

const credFields = [
  { key: "client_id" as const, type: "text", i18n: "admin.clientId" },
  {
    key: "client_secret" as const,
    type: "password",
    i18n: "admin.clientSecret",
  },
];
const basicFields = [
  {
    key: "display_name" as const,
    labelKey: "admin.displayName",
    type: "text",
    placeholder: "",
  },
  {
    key: "slug" as const,
    labelKey: "admin.slug",
    type: "text",
    placeholder: "",
  },
  {
    key: "icon_url" as const,
    labelKey: "",
    type: "url",
    placeholder: "https://...",
  },
];
const endpointFields = [
  { key: "authorization_endpoint" as const, label: "Authorization Endpoint" },
  { key: "token_endpoint" as const, label: "Token Endpoint" },
  { key: "userinfo_endpoint" as const, label: "Userinfo Endpoint" },
  { key: "jwks_uri" as const, label: "JWKS URI" },
];
const claimFields = [
  { key: "sub_claim" as const, label: "Sub Claim" },
  { key: "email_claim" as const, label: "Email Claim" },
  { key: "name_claim" as const, label: "Name Claim" },
  { key: "avatar_claim" as const, label: "Avatar Claim" },
];

async function handleSave(): Promise<void> {
  const ok = await save();
  if (ok) emit("saved");
}
</script>
