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
        'flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg transition-all duration-300',
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
  success: 'bg-green-50 text-green-800 dark:bg-green-900/80 dark:text-green-200',
  error: 'bg-red-50 text-red-800 dark:bg-red-900/80 dark:text-red-200',
  info: 'bg-blue-50 text-blue-800 dark:bg-blue-900/80 dark:text-blue-200',
  warning: 'bg-yellow-50 text-yellow-800 dark:bg-yellow-900/80 dark:text-yellow-200',
}

/** @brief Icon per toast type. */
const typeIcons: Record<string, string> = {
  success: '✓',
  error: '✕',
  info: 'ℹ',
  warning: '⚠',
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
