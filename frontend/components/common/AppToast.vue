<!--
  @file components/common/AppToast.vue
  @brief Toast notification container component.

  Renders a stack of toast notifications from the UI store.
  Each toast auto-dismisses after its configured duration.
  Positioned fixed in the top-right corner.
-->
<template>
  <div
    class="fixed right-4 top-4 z-50 flex flex-col gap-2"
    role="region"
    :aria-label="$t('toast.success')"
    aria-live="polite"
  >
    <div
      v-for="toast in toasts"
      :key="toast.id"
      :class="[
        'flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 shadow-lg transition-all duration-300',
        'min-w-[300px] max-w-[400px]',
        typeClasses[toast.type],
      ]"
      role="alert"
    >
      <span class="text-lg">{{ typeIcons[toast.type] }}</span>
      <p class="flex-1 text-sm font-medium">{{ toast.message }}</p>
      <button
        class="ml-2 text-current opacity-60 hover:opacity-100"
        :aria-label="$t('common.close')"
        @click="dismiss(toast.id)"
      >
        &times;
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief AppToast component with auto-dismiss and styling per type.
 */
import { watch, onUnmounted } from 'vue'
import type { ToastItem } from '~/types/api'

const props = defineProps<{
  /** @brief Active toast notifications. */
  toasts: ToastItem[]
}>()

const emit = defineEmits<{
  (e: 'dismiss', id: string): void
}>()

const timers = new Map<string, ReturnType<typeof setTimeout>>()

/** @brief CSS classes per toast type. */
const typeClasses: Record<string, string> = {
  success: 'text-green-700 dark:text-green-400',
  error: 'text-red-700 dark:text-red-400',
  info: 'text-blue-700 dark:text-blue-400',
  warning: 'text-yellow-700 dark:text-yellow-400',
}

/** @brief Icon per toast type. */
const typeIcons: Record<string, string> = {
  success: '\u2713',
  error: '\u2715',
  info: '\u2139',
  warning: '\u26A0',
}

function dismiss(id: string): void {
  clearTimer(id)
  emit('dismiss', id)
}

function clearTimer(id: string): void {
  const timer = timers.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.delete(id)
  }
}

watch(
  () => props.toasts,
  (newToasts) => {
    for (const toast of newToasts) {
      if (!timers.has(toast.id) && toast.duration) {
        timers.set(toast.id, setTimeout(() => dismiss(toast.id), toast.duration))
      }
    }
  },
  { deep: true, immediate: true },
)

onUnmounted(() => {
  timers.forEach(timer => clearTimeout(timer))
  timers.clear()
})
</script>
