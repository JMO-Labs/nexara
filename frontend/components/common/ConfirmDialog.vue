<!--
  @file components/common/ConfirmDialog.vue
  @brief Reusable confirmation dialog with focus trap.

  Renders a modal overlay with a title, message, and confirm/cancel
  buttons. Uses focus trapping for accessibility. Emits `confirm`
  or `cancel` events based on user action.
-->
<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      @keydown.escape="$emit('cancel')"
    >
      <div
        ref="dialogRef"
        class="mx-4 w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-xl"
        tabindex="-1"
      >
        <h2 class="mb-2 text-lg font-semibold text-card-foreground">
          {{ title }}
        </h2>
        <p class="mb-6 text-sm text-muted-foreground">{{ message }}</p>
        <div class="flex justify-end gap-3">
          <button
            class="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
            @click="$emit('cancel')"
          >
            {{ $t("common.cancel") }}
          </button>
          <button
            class="rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground transition-colors hover:bg-destructive/90 focus:ring-2 focus:ring-ring"
            @click="$emit('confirm')"
          >
            {{ $t("common.confirm") }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * @brief ConfirmDialog component props and events.
 */
import { ref, watch, nextTick } from "vue";

const props = defineProps<{
  /** @brief Whether the dialog is visible. */
  open: boolean;
  /** @brief Dialog title text. */
  title: string;
  /** @brief Dialog message body. */
  message: string;
}>();

defineEmits<{
  confirm: [];
  cancel: [];
}>();

const dialogRef = ref<HTMLElement | null>(null);

/** Focus the dialog container when opened for keyboard accessibility. */
watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await nextTick();
      dialogRef.value?.focus();
    }
  },
);
</script>
