<!--
  @file pages/app/admin/interests.vue
  @brief Admin analytics dashboard for interests.
-->
<template>
  <div class="space-y-6">
    <div
      v-if="authStore.user?.role !== 'admin'"
      class="rounded-lg border border-border bg-card p-6 text-center text-muted-foreground"
    >
      {{ $t("common.loading") }}
    </div>

    <template v-else>
      <div class="rounded-lg border border-border bg-card p-4">
        <h1 class="mb-4 text-lg font-semibold text-foreground">
          {{ $t("admin.interests.title") }}
        </h1>

        <div v-if="loading" class="text-muted-foreground">
          {{ $t("common.loading") }}
        </div>

        <div v-else-if="analytics.length === 0" class="text-muted-foreground">
          {{ $t("admin.interests.empty") }}
        </div>

        <table class="w-full text-left text-sm">
          <thead>
            <tr class="border-b border-border">
              <th class="pb-2 text-foreground">
                {{ $t("admin.interests.category") }}
              </th>
              <th class="pb-2 text-foreground">
                {{ $t("admin.interests.value") }}
              </th>
              <th class="pb-2 text-foreground">
                {{ $t("admin.interests.count") }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in analytics"
              :key="`${row.category_slug}-${row.value}-${idx}`"
              class="border-b border-border"
            >
              <td class="py-2">{{ row.category_slug }}</td>
              <td class="py-2">{{ row.value }}</td>
              <td class="py-2">{{ row.count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin interests analytics page.
 */
import { ref, computed, onMounted } from "vue";
import { useAuthStore } from "~/stores/auth";
import { useApi } from "~/composables/useApi";
import type { InterestAnalytics } from "~/types/api";

const authStore = useAuthStore();
const api = useApi();
const rawAnalytics = ref<InterestAnalytics[]>([]);
const loading = ref(true);

const analytics = computed(() =>
  [...rawAnalytics.value].sort((a, b) => b.count - a.count),
);

async function fetchAnalytics(): Promise<void> {
  if (authStore.user?.role !== "admin") return;
  loading.value = true;
  try {
    const res = await api.get<{ items: InterestAnalytics[] }>(
      "/interests/admin/interests/analytics",
    );
    rawAnalytics.value = res?.items ?? [];
  } catch {
    rawAnalytics.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(fetchAnalytics);
</script>
