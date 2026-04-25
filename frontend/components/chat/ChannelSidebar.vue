<!--
  @file components/chat/ChannelSidebar.vue
  @brief Channel list with per-channel unread indicator.

  Groups channels by type (community / subgroup / direct). The active
  channel is highlighted and unread counts are rendered as a pill
  badge on the right. Emits `select` when a channel is clicked.
-->
<template>
  <aside
    class="flex h-full w-full flex-col border-r border-border bg-card"
    role="navigation"
    :aria-label="$t('chat.channels')"
  >
    <header class="border-b border-border px-4 py-3">
      <h2 class="text-sm font-semibold text-foreground">
        {{ $t("chat.channels") }}
      </h2>
    </header>

    <div
      v-if="channels.length === 0"
      class="flex flex-1 items-center justify-center px-4 text-center text-sm text-muted-foreground"
      data-testid="channel-sidebar-empty"
    >
      {{ $t("chat.noChannels") }}
    </div>

    <ul
      v-else
      class="flex-1 space-y-6 overflow-y-auto px-2 py-3"
      data-testid="channel-sidebar-list"
    >
      <li v-for="group in groups" :key="group.key">
        <p
          class="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
        >
          {{ $t(`chat.${group.key}`) }}
        </p>
        <ul class="space-y-0.5">
          <li v-for="channel in group.items" :key="channel.id">
            <button
              type="button"
              :data-testid="`channel-item-${channel.id}`"
              :aria-current="channel.id === activeChannelId ? 'page' : undefined"
              class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors"
              :class="
                channel.id === activeChannelId
                  ? 'bg-accent text-accent-foreground'
                  : 'text-foreground hover:bg-accent/60'
              "
              @click="$emit('select', channel)"
            >
              <span class="text-muted-foreground">
                {{ channel.channel_type === "direct" ? "@" : "#" }}
              </span>
              <span class="min-w-0 flex-1 truncate">{{ channel.name }}</span>
              <span
                v-if="(unreadByChannel[channel.id] ?? 0) > 0"
                class="inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 py-0.5 text-xs font-medium text-primary-foreground"
                :data-testid="`channel-unread-${channel.id}`"
                :aria-label="$t('chat.unread')"
              >
                {{ unreadByChannel[channel.id] }}
              </span>
            </button>
          </li>
        </ul>
      </li>
    </ul>
  </aside>
</template>

<script setup lang="ts">
/**
 * @brief ChannelSidebar — navigation between channels.
 */
import { computed } from "vue";
import type { ChatChannel, ChannelType } from "~/types/api";

const props = defineProps<{
  /** @brief All channels to render. */
  channels: ChatChannel[];
  /** @brief Unread counts keyed by channel id. */
  unreadByChannel: Record<string, number>;
  /** @brief Currently active channel id (highlighted). */
  activeChannelId: string | null;
}>();

defineEmits<{
  (e: "select", channel: ChatChannel): void;
}>();

/** @brief Display order for the grouped headings. */
const GROUP_ORDER: ChannelType[] = ["community", "subgroup", "direct"];

/** @brief Channels grouped by type, preserving GROUP_ORDER. */
const groups = computed(() => {
  const bucket: Record<ChannelType, ChatChannel[]> = {
    community: [],
    subgroup: [],
    direct: [],
  };
  for (const c of props.channels) {
    bucket[c.channel_type].push(c);
  }
  return GROUP_ORDER.filter((k) => bucket[k].length > 0).map((k) => ({
    key: k,
    items: bucket[k],
  }));
});
</script>
