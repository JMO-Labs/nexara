<!--
  @file components/feed/DeleteConfirmDialog.vue
  @brief Delete confirmation dialog with cancel and confirm actions.

  Renders a modal overlay (teleported to body) prompting the user to confirm
  a destructive delete action. Emits confirm when the user confirms, cancel
  when the user dismisses via the cancel button or backdrop click.
-->
<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        class="fixed inset-0 bg-background/80 backdrop-blur-sm"
        @click="$emit('cancel')"
      />
      <div
        class="relative z-10 w-full max-w-sm rounded-lg border border-border bg-popover p-6 shadow-lg"
        role="alertdialog"
      >
        <p class="mb-4 text-sm text-foreground">
          {{ $t("feed.deleteConfirm") }}
        </p>
        <div class="flex justify-end gap-2">
          <button
            class="rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent"
            @click="$emit('cancel')"
          >
            {{ $t("common.cancel") }}
          </button>
          <button
            :disabled="deleting"
            class="rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground transition-colors hover:bg-destructive/90 disabled:opacity-50"
            @click="$emit('confirm')"
          >
            {{ deleting ? $t("common.loading") : $t("common.delete") }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * @brief Delete confirmation dialog component.
 *
 * Displays a modal asking the user to confirm a delete action.
 * Emits confirm when the user clicks delete, cancel when they dismiss.
 */
defineProps<{
  /** @brief Whether the dialog is visible. */
  visible: boolean;
  /** @brief Whether a delete operation is in progress (disables confirm button). */
  deleting: boolean;
}>();

defineEmits<{
  /** @brief Emitted when the user confirms the delete action. */
  (e: "confirm"): void;
  /** @brief Emitted when the user cancels (button or backdrop click). */
  (e: "cancel"): void;
}>();
</script>
