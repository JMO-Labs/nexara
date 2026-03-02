<!--
  @file pages/app/admin/sso.vue
  @brief Admin SSO providers management page.

  Lists OAuth/OIDC providers with enable toggle, edit, and delete.
  Uses GET/POST/PUT/DELETE /admin/oauth/providers and toggle endpoint.
-->
<template>
  <div class="space-y-6">
    <div class="rounded-lg border border-border bg-card p-6">
      <h2 class="mb-2 text-lg font-semibold text-foreground">
        {{ $t("admin.sso") }}
      </h2>
      <p class="mb-4 text-sm text-muted-foreground">
        {{ $t("admin.ssoDescription") }}
      </p>

      <div class="mb-4">
        <button
          type="button"
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          @click="openForm()"
        >
          {{ $t("admin.addProvider") }}
        </button>
      </div>

      <div class="overflow-x-auto rounded-lg border border-border">
        <table class="w-full min-w-[600px] text-left text-sm">
          <thead class="border-b border-border bg-muted/50">
            <tr>
              <th class="px-4 py-3 font-medium text-foreground">
                {{ $t("admin.displayName") }}
              </th>
              <th class="px-4 py-3 font-medium text-foreground">
                {{ $t("admin.providerType") }}
              </th>
              <th class="px-4 py-3 font-medium text-foreground">
                {{ $t("admin.slug") }}
              </th>
              <th class="px-4 py-3 font-medium text-foreground">
                {{ $t("admin.status") }}
              </th>
              <th class="px-4 py-3 font-medium text-foreground">
                {{ $t("admin.actions") }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="border-b border-border">
              <td
                colspan="5"
                class="px-4 py-8 text-center text-muted-foreground"
              >
                {{ $t("common.loading") }}
              </td>
            </tr>
            <tr v-else-if="!providers.length" class="border-b border-border">
              <td
                colspan="5"
                class="px-4 py-8 text-center text-muted-foreground"
              >
                {{ $t("admin.no_results") }}
              </td>
            </tr>
            <tr
              v-for="p in providers"
              :key="p.id"
              class="border-b border-border last:border-0 hover:bg-muted/30"
            >
              <td class="px-4 py-3 text-foreground">
                {{ p.display_name }}
                <span
                  v-if="p.env_seeded"
                  class="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs"
                >
                  {{ $t("admin.envSeeded") }}
                </span>
              </td>
              <td class="px-4 py-3">{{ p.provider_type.toUpperCase() }}</td>
              <td class="px-4 py-3 font-mono text-muted-foreground">
                {{ p.slug }}
              </td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="
                    p.enabled
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                      : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                  "
                >
                  {{ p.enabled ? $t("admin.active") : $t("admin.suspended") }}
                </span>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="text-sm text-primary hover:underline"
                    :disabled="p.env_seeded"
                    @click="handleToggle(p)"
                  >
                    {{ p.enabled ? $t("admin.suspend") : $t("admin.restore") }}
                  </button>
                  <button
                    type="button"
                    class="text-sm text-primary hover:underline"
                    :disabled="p.env_seeded"
                    @click="openForm(p)"
                  >
                    {{ $t("admin.editProvider") }}
                  </button>
                  <button
                    type="button"
                    class="text-sm text-red-600 hover:underline dark:text-red-400"
                    :disabled="p.env_seeded"
                    @click="handleDelete(p)"
                  >
                    {{ $t("common.delete") }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <AdminSsoProviderForm
      v-if="showForm"
      :provider="editingProvider"
      @saved="onSaved"
      @cancelled="showForm = false"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin SSO page — provider list and modal form.
 */
import { ref, onMounted } from "vue";
import { useApi } from "~/composables/useApi";
import { useUiStore } from "~/stores/ui";
import type { OAuthProviderResponse } from "~/types/api";

const api = useApi();
const uiStore = useUiStore();
const { t: $t } = useI18n();

const providers = ref<OAuthProviderResponse[]>([]);
const loading = ref(false);
const showForm = ref(false);
const editingProvider = ref<OAuthProviderResponse | undefined>(undefined);

async function fetchProviders(): Promise<void> {
  loading.value = true;
  try {
    const list = await api.get<
      OAuthProviderResponse[] | { items: OAuthProviderResponse[] }
    >("/admin/oauth/providers");
    providers.value = Array.isArray(list) ? list : (list?.items ?? []);
  } catch (e) {
    providers.value = [];
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  } finally {
    loading.value = false;
  }
}

function openForm(provider?: OAuthProviderResponse): void {
  editingProvider.value = provider;
  showForm.value = true;
}

function onSaved(): void {
  showForm.value = false;
  editingProvider.value = undefined;
  fetchProviders();
  uiStore.showToast({ type: "success", message: $t("admin.providerSaved") });
}

async function handleToggle(p: OAuthProviderResponse): Promise<void> {
  if (p.env_seeded) return;
  try {
    await api.post(`/admin/oauth/providers/${p.id}/toggle`);
    await fetchProviders();
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  }
}

async function handleDelete(p: OAuthProviderResponse): Promise<void> {
  if (p.env_seeded) return;
  if (!confirm($t("admin.deleteProviderConfirm"))) return;
  try {
    await api.del(`/admin/oauth/providers/${p.id}`);
    uiStore.showToast({
      type: "success",
      message: $t("admin.providerDeleted"),
    });
    await fetchProviders();
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  }
}

onMounted(() => {
  fetchProviders();
});
</script>
