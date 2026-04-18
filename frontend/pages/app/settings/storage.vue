<!--
  @file pages/app/settings/storage.vue
  @brief Storage quota usage page.

  Loads user storage data from auth store (storage_used, storage_quota).
  Progress bar showing usage percentage.
  Warning state when > 80%.
-->
<template>
  <div class="flex-1 rounded-lg border border-border bg-card p-6">
    <h2 class="mb-4 text-lg font-semibold text-foreground">
      {{ $t("settings.storage") }}
    </h2>

    <div
      v-if="user"
      class="space-y-4"
    >
      <div
        class="overflow-hidden rounded-full bg-muted"
        :class="{ 'ring-2 ring-amber-500': isWarning }"
        data-testid="storage-bar"
      >
        <div
          class="h-4 rounded-full bg-primary transition-all"
          :style="{ width: `${usagePercent}%` }"
        />
      </div>
      <p
        class="text-sm"
        :class="isWarning ? 'text-amber-600' : 'text-muted-foreground'"
      >
        {{ $t("settings.storageUsed", { used: usedFormatted, quota: quotaFormatted }) }}
      </p>
      <p
        v-if="isWarning"
        class="text-sm text-amber-600"
      >
        {{ $t("settings.storageWarning") }}
      </p>
    </div>

    <p
      v-else
      class="text-muted-foreground"
    >
      {{ $t("common.loading") }}
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Storage settings page — displays user storage quota usage.
 */
import { computed } from "vue";
import { useAuthStore } from "~/stores/auth";

const authStore = useAuthStore();

/** @brief Current user from auth store. */
const user = computed(() => authStore.user);

/** @brief Storage used in bytes (User has storage_used, storage_quota). */
const usedBytes = computed(() => user.value?.storage_used ?? 0);
const quotaBytes = computed(() => user.value?.storage_quota ?? 0);

/** @brief Usage percentage (0-100). */
const usagePercent = computed(() => {
  if (quotaBytes.value === 0) return 0;
  return Math.min(100, Math.round((usedBytes.value / quotaBytes.value) * 100));
});

/** @brief Whether usage is over 80%. */
const isWarning = computed(() => usagePercent.value > 80);

/** @brief Format bytes to human-readable string. */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

const usedFormatted = computed(() => formatBytes(usedBytes.value));
const quotaFormatted = computed(() => formatBytes(quotaBytes.value));
</script>
