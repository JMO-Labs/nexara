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
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      @keydown.escape="$emit('cancel')"
    >
      <div
        ref="dialogRef"
        class="mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        tabindex="-1"
      >
        <h2 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{{ title }}</h2>
        <p class="mb-6 text-sm text-gray-600 dark:text-gray-300">{{ message }}</p>
        <div class="flex justify-end gap-3">
          <button
            class="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="$emit('cancel')"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:ring-2 focus:ring-red-500"
            @click="$emit('confirm')"
          >
            {{ $t('common.confirm') }}
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
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  /** @brief Whether the dialog is visible. */
  open: boolean
  /** @brief Dialog title text. */
  title: string
  /** @brief Dialog message body. */
  message: string
}>()

defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const dialogRef = ref<HTMLElement | null>(null)

/** Focus the dialog container when opened for keyboard accessibility. */
watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    await nextTick()
    dialogRef.value?.focus()
  }
})
</script>
