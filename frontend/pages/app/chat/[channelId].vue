<!--
  @file pages/app/chat/[channelId].vue
  @brief Chat room view for a single channel (community, subgroup, or DM).

  Renders the sidebar, the message list for the active channel, and
  the composer. Opens a WebSocket on mount (via useWebSocket) and
  routes inbound frames to the chat store. Sends outbound messages,
  typing events, and read receipts through the same socket.
-->
<template>
  <div
    class="flex h-[calc(100vh-8rem)] overflow-hidden rounded-lg border border-border bg-background"
  >
    <div class="hidden w-64 shrink-0 md:block">
      <ChannelSidebar
        :channels="chatStore.channels"
        :unread-by-channel="chatStore.unreadByChannel"
        :active-channel-id="channelId"
        @select="onSelectChannel"
      />
    </div>

    <section class="flex min-w-0 flex-1 flex-col">
      <header
        class="flex shrink-0 items-center justify-between border-b border-border bg-card px-4 py-2"
      >
        <h1 class="truncate text-sm font-semibold text-foreground">
          <span class="text-muted-foreground">
            {{ activeChannel?.channel_type === "direct" ? "@" : "#" }}
          </span>
          {{ activeChannel?.name ?? $t("chat.title") }}
        </h1>
        <span
          v-if="wsStatus !== 'open'"
          class="text-xs text-muted-foreground"
          role="status"
          data-testid="chat-connection-status"
        >
          {{ $t("chat.connectError") }}
        </span>
      </header>

      <div class="min-h-0 flex-1">
        <MessageList
          :messages="messages"
          :has-more="historyEntry?.hasMore ?? false"
          :loading="historyEntry?.loading ?? false"
          :current-user-id="authStore.user?.id ?? null"
          :is-admin="authStore.user?.role === 'admin'"
          @load-older="loadOlder"
          @edit="onEditMessage"
          @delete="onDeleteMessage"
        />
      </div>

      <div
        v-if="typingLabel"
        class="px-4 py-1 text-xs italic text-muted-foreground"
        data-testid="chat-typing-indicator"
      >
        {{ typingLabel }}
      </div>

      <MessageInput
        :disabled="wsStatus !== 'open'"
        @send="onSend"
        @typing="onTyping"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Channel chat room page.
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "~/stores/auth";
import { useChatStore } from "~/stores/chat";
import { useWebSocket } from "~/composables/useWebSocket";
import ChannelSidebar from "~/components/chat/ChannelSidebar.vue";
import MessageList from "~/components/chat/MessageList.vue";
import MessageInput from "~/components/chat/MessageInput.vue";
import type { ChatChannel } from "~/types/api";

definePageMeta({ middleware: "auth" });

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const chatStore = useChatStore();

/** @brief Current channel id from the dynamic route param. */
const channelId = computed(() => String(route.params.channelId ?? ""));

/** @brief Channel record for header display. */
const activeChannel = computed<ChatChannel | undefined>(() =>
  chatStore.channels.find((c) => c.id === channelId.value),
);

/** @brief History entry for the active channel. */
const historyEntry = computed(
  () => chatStore.messagesByChannel[channelId.value],
);

/** @brief Message list view — newest first. */
const messages = computed(() => historyEntry.value?.items ?? []);

/**
 * @brief WebSocket to the backend realtime endpoint.
 *
 * The composable performs first-message JWT auth automatically
 * and reconnects with exponential backoff on disconnection.
 */
const { status: wsStatus, connect, disconnect, send } = useWebSocket(
  (data) => {
    if (!data || typeof data !== "object") return;
    const frame = data as { type?: string; payload?: unknown };
    if (!frame.type) return;
    chatStore.handleInboundWsMessage({
      type: frame.type,
      payload: frame.payload,
    });
  },
);

/** @brief Label for the typing indicator row. */
const typingLabel = computed(() => {
  const state = chatStore.typingByChannel[channelId.value];
  if (!state || state.users.size === 0) return "";
  const ownId = authStore.user?.id;
  const others = Array.from(state.users.keys()).filter((u) => u !== ownId);
  if (others.length === 0) return "";
  if (others.length === 1) {
    /* Backend sends opaque user_id; display as a generic label. */
    return "…";
  }
  return "…";
});

const pruneTimer = ref<ReturnType<typeof setInterval> | null>(null);

onMounted(async () => {
  connect();
  if (chatStore.channels.length === 0) {
    await chatStore.fetchChannels();
  }
  await ensureHistory();
  chatStore.setActiveChannel(channelId.value);
  pruneTimer.value = setInterval(() => chatStore.pruneTyping(), 1_500);
});

onBeforeUnmount(() => {
  disconnect();
  chatStore.setActiveChannel(null);
  if (pruneTimer.value) clearInterval(pruneTimer.value);
});

watch(channelId, async () => {
  chatStore.setActiveChannel(channelId.value);
  await ensureHistory();
});

/** @brief Fetch history for the current channel if not already loaded. */
async function ensureHistory(): Promise<void> {
  const cid = channelId.value;
  if (!cid) return;
  const entry = chatStore.messagesByChannel[cid];
  if (!entry || entry.items.length === 0) {
    await chatStore.fetchHistory(cid, true);
  }
  /* Mark latest message as read. */
  const top = chatStore.messagesByChannel[cid]?.items[0];
  if (top) chatStore.markRead(send, cid, top.id);
}

async function loadOlder(): Promise<void> {
  await chatStore.fetchHistory(channelId.value);
}

function onSend(content: string): void {
  chatStore.sendMessage(send, channelId.value, content);
}

function onTyping(): void {
  chatStore.sendTyping(send, channelId.value);
}

function onEditMessage(id: string, content: string): void {
  chatStore.editMessage(id, channelId.value, content);
}

function onDeleteMessage(id: string): void {
  if (!confirm(String("Delete this message?"))) return;
  chatStore.deleteMessage(id, channelId.value);
}

function onSelectChannel(channel: ChatChannel): void {
  router.push(`/app/chat/${channel.id}`);
}
</script>
