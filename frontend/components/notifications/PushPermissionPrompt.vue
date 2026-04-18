<!--
  @file components/notifications/PushPermissionPrompt.vue
  @brief Opt-in dialog for push notifications.

  Shows when permission is "default". Enable calls subscribe(), Not now emits dismissed.
-->
<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    data-testid="push-permission-prompt"
  >
    <div
      class="max-w-md rounded-lg border border-border bg-card p-6 shadow-xl"
      role="dialog"
      aria-labelledby="push-prompt-title"
    >
      <h2
        id="push-prompt-title"
        class="mb-2 text-lg font-semibold text-foreground"
      >
        {{ $t("notifications.pushTitle") }}
      </h2>
      <p class="mb-6 text-sm text-muted-foreground">
        {{ $t("notifications.pushDescription") }}
      </p>
      <div class="flex justify-end gap-2">
        <button
          class="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
          @click="handleDismiss"
        >
          {{ $t("notifications.pushNotNow") }}
        </button>
        <button
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          :disabled="loading"
          @click="handleEnable"
        >
          {{ loading ? $t("common.loading") : $t("notifications.pushEnable") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief PushPermissionPrompt - opt-in for push notifications.
 */
import { computed } from "vue";
import { usePushNotifications } from "~/composables/usePushNotifications";

const emit = defineEmits<{
  (e: "dismissed"): void;
}>();

const { isSupported, permission, subscribe, loading } = usePushNotifications();

const show = computed(
  () => isSupported.value && permission.value === "default",
);

async function handleEnable(): Promise<void> {
  const ok = await subscribe();
  if (ok) emit("dismissed");
}

function handleDismiss(): void {
  emit("dismissed");
}
</script>
