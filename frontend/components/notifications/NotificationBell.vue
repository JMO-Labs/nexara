<!--
  @file components/notifications/NotificationBell.vue
  @brief Bell icon with unread count badge.

  Emits 'toggle' on click to open the notification panel.
  Hides badge when count is 0. Includes ARIA labels for accessibility.
-->

<script setup lang="ts">
/**
 * @brief NotificationBell component.
 *
 * Reads unread count directly from the notifications store.
 * Fetches the count on mount so the badge is always current.
 */
import { onMounted } from "vue";
import { useNotificationsStore } from "~/stores/notifications";

const notifStore = useNotificationsStore();

defineEmits<{
  /** @brief Emitted when the bell is clicked to open the panel. */
  toggle: [];
}>();

onMounted(() => {
  notifStore.fetchUnreadCount();
});
</script>

<template>
  <button
    type="button"
    class="relative rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
    :aria-label="$t('a11y.notifications')"
    @click="$emit('toggle')"
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
    <span
      v-if="notifStore.unreadCount > 0"
      class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-destructive-foreground"
      :aria-hidden="true"
    >
      {{ notifStore.unreadCount > 99 ? "99+" : notifStore.unreadCount }}
    </span>
  </button>
</template>
