<!--
  @file components/common/AppToast.vue
  @brief Toast notification container rendered via Teleport to body.

  Renders a stack of toast notifications from the UI store using
  TransitionGroup for slide-in/fade animations. Each toast
  auto-dismisses after its configured duration. Teleported to
  <body> to avoid CSS stacking context issues from layout ancestors.
-->
<template>
  <Teleport to="body">
    <div
      class="fixed right-4 top-4 z-[9999] flex flex-col gap-2"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
    >
      <TransitionGroup name="toast" tag="div" class="flex flex-col gap-2">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-xl backdrop-blur-sm',
            'min-w-[300px] max-w-[400px]',
            typeBgClasses[toast.type],
          ]"
          role="alert"
        >
          <span class="text-lg" aria-hidden="true">{{
            typeIcons[toast.type]
          }}</span>
          <p class="flex-1 text-sm font-medium">{{ toast.message }}</p>
          <button
            class="ml-2 text-current opacity-60 transition-opacity hover:opacity-100"
            aria-label="Dismiss"
            @click="dismiss(toast.id)"
          >
            &times;
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * @brief AppToast component with Teleport, TransitionGroup, and auto-dismiss.
 */
import { watch, onUnmounted } from "vue";
import type { ToastItem } from "~/types/api";

const props = defineProps<{
  /** @brief Active toast notifications. */
  toasts: ToastItem[];
}>();

const emit = defineEmits<{
  (e: "dismiss", id: string): void;
}>();

const timers = new Map<string, ReturnType<typeof setTimeout>>();

/** @brief Background + text classes per toast type for high-visibility rendering. */
const typeBgClasses: Record<string, string> = {
  success:
    "border-green-300 bg-green-50/95 text-green-800 dark:border-green-700 dark:bg-green-950/95 dark:text-green-200",
  error:
    "border-red-300 bg-red-50/95 text-red-800 dark:border-red-700 dark:bg-red-950/95 dark:text-red-200",
  info: "border-blue-300 bg-blue-50/95 text-blue-800 dark:border-blue-700 dark:bg-blue-950/95 dark:text-blue-200",
  warning:
    "border-yellow-300 bg-yellow-50/95 text-yellow-800 dark:border-yellow-700 dark:bg-yellow-950/95 dark:text-yellow-200",
};

/** @brief Icon per toast type. */
const typeIcons: Record<string, string> = {
  success: "\u2713",
  error: "\u2715",
  info: "\u2139",
  warning: "\u26A0",
};

function dismiss(id: string): void {
  clearTimer(id);
  emit("dismiss", id);
}

function clearTimer(id: string): void {
  const timer = timers.get(id);
  if (timer) {
    clearTimeout(timer);
    timers.delete(id);
  }
}

watch(
  () => props.toasts,
  (newToasts) => {
    for (const toast of newToasts) {
      if (!timers.has(toast.id) && toast.duration) {
        timers.set(
          toast.id,
          setTimeout(() => dismiss(toast.id), toast.duration),
        );
      }
    }
  },
  { deep: true, immediate: true },
);

onUnmounted(() => {
  timers.forEach((timer) => clearTimeout(timer));
  timers.clear();
});
</script>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.2s ease-in;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(60px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(60px);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
