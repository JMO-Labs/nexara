<!--
  @file components/notifications/NotificationPanel.vue
  @brief Dropdown panel listing notifications.

  Each notification shows type icon, message from payload.message, relative time.
  Click marks as read and navigates to payload.link. Includes "Mark all as read"
  button and empty state. Fetches notifications when opened. Closes on click-outside.
-->

<script setup lang="ts">
/**
 * @brief NotificationPanel component.
 */
import { computed, watch, ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  AtSymbolIcon,
  BellIcon,
  ChatBubbleLeftRightIcon,
  HeartIcon,
  DocumentTextIcon,
  UserPlusIcon,
} from "@heroicons/vue/24/outline";
import { useNotificationsStore } from "~/stores/notifications";
import type { Notification } from "~/types/api";

const typeIcons: Record<string, typeof BellIcon> = {
  mention: AtSymbolIcon,
  comment: ChatBubbleLeftRightIcon,
  reaction: HeartIcon,
  new_post: DocumentTextIcon,
  system: BellIcon,
  invite_accepted: UserPlusIcon,
};

const props = defineProps<{
  /** @brief Whether the panel is visible. */
  open: boolean;
}>();

const emit = defineEmits<{
  /** @brief Emitted when the panel should close. */
  close: [];
}>();

const { t } = useI18n();
const router = useRouter();
const store = useNotificationsStore();

/** @brief Template ref for click-outside detection. */
const panelRef = ref<HTMLElement | null>(null);

/** @brief Fetch notifications when panel opens. */
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) store.fetchNotifications();
  },
);

/** @brief Close panel when clicking outside. */
function onClickOutside(event: MouseEvent): void {
  if (panelRef.value && !panelRef.value.contains(event.target as Node)) {
    emit("close");
  }
}

onMounted(() => document.addEventListener("mousedown", onClickOutside));
onBeforeUnmount(() => document.removeEventListener("mousedown", onClickOutside));

/** @brief Notifications from the store. */
const notifications = computed(() => store.notifications);

/** @brief Whether the list is empty. */
const isEmpty = computed(() => notifications.value.length === 0);

/**
 * @brief Format relative time (e.g. "2 min ago").
 */
function formatRelative(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 1) return t("notifications.justNow");
  if (diffMins < 60) return t("notifications.minutesAgo", { count: diffMins });
  if (diffHours < 24) return t("notifications.hoursAgo", { count: diffHours });
  return t("notifications.daysAgo", { count: diffDays });
}

/**
 * @brief Get icon component for notification type.
 */
function typeIcon(type: string): typeof BellIcon {
  return typeIcons[type] ?? BellIcon;
}

/**
 * @brief Handle notification click: mark read and navigate.
 */
async function onNotificationClick(n: Notification): Promise<void> {
  if (!n.read_at) {
    await store.markRead(n.id);
  }
  const link = n.payload?.link as string | undefined;
  emit("close");
  if (link) {
    await router.push(link);
  }
}

/**
 * @brief Mark all as read.
 */
async function onMarkAllRead(): Promise<void> {
  await store.markAllRead();
}

/**
 * @brief Clear all notifications.
 */
async function onClearAll(): Promise<void> {
  await store.clearAll();
}
</script>

<template>
  <div
    v-if="open"
    ref="panelRef"
    class="absolute right-0 top-full z-50 mt-2 w-80 max-h-96 overflow-y-auto rounded-lg border bg-background shadow-lg"
    role="dialog"
    aria-label="Notifications"
  >
    <div class="flex items-center justify-between border-b px-4 py-2">
      <h3 class="font-semibold">{{ t("notifications.title") }}</h3>
      <div class="flex items-center gap-2">
        <button
          v-if="!isEmpty && store.unreadCount > 0"
          type="button"
          class="text-sm text-primary hover:underline"
          @click="onMarkAllRead"
        >
          {{ t("notifications.markAllRead") }}
        </button>
        <button
          v-if="!isEmpty"
          type="button"
          class="text-sm text-destructive hover:underline"
          @click="onClearAll"
        >
          {{ t("notifications.clearAll") }}
        </button>
      </div>
    </div>
    <div v-if="isEmpty" class="px-4 py-8 text-center text-muted-foreground">
      {{ t("notifications.empty") }}
    </div>
    <ul v-else class="divide-y">
      <li
        v-for="n in notifications"
        :key="n.id"
        class="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/50 transition-colors"
        :class="{ 'bg-muted/30': !n.read_at }"
        @click="onNotificationClick(n)"
      >
        <component
          :is="typeIcon(n.type)"
          class="h-5 w-5 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
        <div class="min-w-0 flex-1">
          <p class="text-sm">
            {{ (n.payload?.message as string) || n.type }}
          </p>
          <p class="text-xs text-muted-foreground">
            {{ formatRelative(n.created_at) }}
          </p>
        </div>
      </li>
    </ul>
  </div>
</template>
