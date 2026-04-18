<!--
  @file pages/app/admin/settings.vue
  @brief Admin community settings page.

  Two-column layout: community settings on left, branding link + info on right.
  Save calls PUT /admin/settings.
-->
<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-foreground">
      {{ $t("admin.settings") }}
    </h1>

    <div class="grid gap-6 lg:grid-cols-2">
      <!-- Community settings -->
      <div class="rounded-lg border border-border bg-card p-6">
        <h2 class="mb-4 text-lg font-semibold text-foreground">
          {{ $t("admin.settings") }}
        </h2>
        <form class="space-y-5" @submit.prevent="handleSave">
          <div class="flex items-center justify-between gap-4">
            <label
              for="enable_registration"
              class="text-sm font-medium text-foreground"
            >
              {{ $t("admin.enable_registration") }}
            </label>
            <input
              id="enable_registration"
              v-model="form.enable_registration"
              type="checkbox"
              class="h-4 w-4 rounded border-input text-primary focus:ring-ring"
            />
          </div>
          <div class="flex items-center justify-between gap-4">
            <label
              for="require_invite"
              class="text-sm font-medium text-foreground"
            >
              {{ $t("admin.require_invite") }}
            </label>
            <input
              id="require_invite"
              v-model="form.require_invite"
              type="checkbox"
              class="h-4 w-4 rounded border-input text-primary focus:ring-ring"
            />
          </div>
          <div class="flex items-center justify-between gap-4">
            <label for="waf_enabled" class="text-sm font-medium text-foreground">
              {{ $t("admin.waf_enabled") }}
            </label>
            <input
              id="waf_enabled"
              v-model="form.waf_enabled"
              type="checkbox"
              class="h-4 w-4 rounded border-input text-primary focus:ring-ring"
            />
          </div>
          <div>
            <label
              for="storage_quota"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("admin.storage_quota") }}
            </label>
            <input
              id="storage_quota"
              v-model.number="form.default_storage_quota_mb"
              type="number"
              min="1"
              class="w-full max-w-[200px] rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
            />
          </div>
          <button
            type="submit"
            :disabled="loading"
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {{ loading ? $t("common.loading") : $t("admin.save") }}
          </button>
        </form>
      </div>

      <!-- Branding link card -->
      <div class="space-y-6">
        <div class="rounded-lg border border-border bg-card p-6">
          <h2 class="mb-2 text-lg font-semibold text-foreground">
            {{ $t("admin.branding") }}
          </h2>
          <p class="mb-4 text-sm text-muted-foreground">
            {{ $t("admin.brandingDescription") }}
          </p>
          <NuxtLink
            to="/app/admin/branding"
            class="inline-flex rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
          >
            {{ $t("admin.branding") }} &rarr;
          </NuxtLink>
        </div>

        <div class="rounded-lg border border-border bg-card p-6">
          <h2 class="mb-2 text-lg font-semibold text-foreground">
            {{ $t("admin.sso") }}
          </h2>
          <p class="mb-4 text-sm text-muted-foreground">
            {{ $t("admin.ssoDescription") }}
          </p>
          <NuxtLink
            to="/app/admin/sso"
            class="inline-flex rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
          >
            {{ $t("admin.sso") }} &rarr;
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin community settings form.
 */
import { ref, onMounted } from "vue";
import { useApi } from "~/composables/useApi";
import { useUiStore } from "~/stores/ui";
import type { AdminCommunitySettings } from "~/types/api";

const api = useApi();
const uiStore = useUiStore();
const { t: $t } = useI18n();

const form = ref<AdminCommunitySettings>({
  enable_registration: true,
  require_invite: false,
  default_storage_quota_mb: 1024,
  waf_enabled: true,
});
const loading = ref(false);

async function fetchSettings(): Promise<void> {
  try {
    const data = await api.get<AdminCommunitySettings>("/admin/settings");
    if (data) form.value = { ...form.value, ...data };
  } catch {
    /* use defaults */
  }
}

async function handleSave(): Promise<void> {
  loading.value = true;
  try {
    await api.put("/admin/settings", form.value);
    uiStore.showToast({ type: "success", message: $t("admin.settingsSaved") });
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchSettings();
});
</script>
