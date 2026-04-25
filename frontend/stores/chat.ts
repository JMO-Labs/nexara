/**
 * @file stores/chat.ts
 * @brief Pinia setup store for the real-time chat feature.
 *
 * Tracks the user's channels, per-channel message history (keyed by
 * channel id), typing indicators, unread counts and last-read message
 * IDs. REST actions call the `/api/v1/chat/*` endpoints via `useApi`.
 * Inbound WebSocket frames (`chat.message`, `chat.updated`,
 * `chat.deleted`, `chat.typing`, `chat.read`, `chat.error`) are routed
 * through `handleInboundWsMessage`.
 */

import { ref, reactive, computed } from "vue";
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";
import type {
  ChatChannel,
  ChatMessage,
  ChatErrorPayload,
  ChatTypingPayload,
  ChatReadPayload,
  ChatDeletedPayload,
  MessageHistoryResponse,
  DirectMessageThread,
} from "~/types/api";
import { CHAT_EVENT } from "~/types/events";

/** @brief Typing indicator TTL in milliseconds. */
const TYPING_TTL_MS = 4_000;

/** @brief Shape of the per-channel history entry. */
interface ChannelHistory {
  items: ChatMessage[];
  cursor: string | null;
  hasMore: boolean;
  loading: boolean;
}

/** @brief Per-channel typing state. */
interface TypingState {
  /** @brief Map of user_id -> expiry timestamp (ms since epoch). */
  users: Map<string, number>;
}

export const useChatStore = defineStore("chat", () => {
  /** @brief Flat list of channels the user belongs to. */
  const channels = ref<ChatChannel[]>([]);

  /** @brief Direct message thread summaries. */
  const dmThreads = ref<DirectMessageThread[]>([]);

  /** @brief Whether channel fetch is in flight. */
  const loadingChannels = ref(false);

  /** @brief Per-channel message history keyed by channel_id. */
  const messagesByChannel = reactive<Record<string, ChannelHistory>>({});

  /** @brief Per-channel typing state keyed by channel_id. */
  const typingByChannel = reactive<Record<string, TypingState>>({});

  /** @brief Unread counts keyed by channel_id. */
  const unreadByChannel = reactive<Record<string, number>>({});

  /** @brief Last read message id keyed by channel_id. */
  const lastReadByChannel = reactive<Record<string, string>>({});

  /** @brief ID of the currently active channel (for unread suppression). */
  const activeChannelId = ref<string | null>(null);

  /** @brief Latest error frame received from the server. */
  const lastError = ref<ChatErrorPayload | null>(null);

  /** @brief Total unread count across all channels. */
  const totalUnread = computed(() =>
    Object.values(unreadByChannel).reduce((sum, n) => sum + (n || 0), 0),
  );

  /**
   * @brief Fetch the user's channel list from the backend.
   * @throws Error if the request fails.
   */
  async function fetchChannels(): Promise<void> {
    if (loadingChannels.value) return;
    loadingChannels.value = true;
    try {
      const api = useApi();
      channels.value = await api.get<ChatChannel[]>("/chat/channels");
    } finally {
      loadingChannels.value = false;
    }
  }

  /**
   * @brief Fetch DM thread summaries.
   */
  async function fetchDmThreads(): Promise<void> {
    const api = useApi();
    dmThreads.value = await api.get<DirectMessageThread[]>("/chat/dm");
  }

  /**
   * @brief Fetch paginated history for a channel.
   *
   * Appends older messages when a cursor is present, resets otherwise.
   * @param channelId - Channel UUID.
   * @param reset - Start from the newest page and discard cached items.
   * @param limit - Page size (1-100).
   */
  async function fetchHistory(
    channelId: string,
    reset = false,
    limit = 50,
  ): Promise<void> {
    const entry = messagesByChannel[channelId];
    if (entry?.loading) return;
    if (entry && !reset && !entry.hasMore) return;

    if (!messagesByChannel[channelId]) {
      messagesByChannel[channelId] = {
        items: [],
        cursor: null,
        hasMore: true,
        loading: false,
      };
    }
    const state = messagesByChannel[channelId];
    state.loading = true;
    try {
      const api = useApi();
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      if (!reset && state.cursor) params.set("cursor", state.cursor);

      const data = await api.get<MessageHistoryResponse>(
        `/chat/channels/${channelId}/messages?${params}`,
      );

      if (reset) {
        state.items = data.items;
      } else {
        /* Older page — append to tail (history is newest-first). */
        state.items = [...state.items, ...data.items];
      }
      state.cursor = data.cursor;
      state.hasMore = data.has_more;
    } finally {
      state.loading = false;
    }
  }

  /**
   * @brief Resolve or create a DM channel with a peer.
   * @param peerId - UUID of the other user.
   * @returns The channel record (existing or new).
   */
  async function openDm(peerId: string): Promise<ChatChannel> {
    const api = useApi();
    const channel = await api.post<ChatChannel>(`/chat/dm/${peerId}`);
    upsertChannel(channel);
    return channel;
  }

  /**
   * @brief Ensure a channel is present in the local list.
   * @param channel - Channel to insert or replace.
   */
  function upsertChannel(channel: ChatChannel): void {
    const idx = channels.value.findIndex((c) => c.id === channel.id);
    if (idx === -1) {
      channels.value.push(channel);
    } else {
      channels.value[idx] = channel;
    }
  }

  /**
   * @brief Send a chat message over the provided WebSocket channel.
   *
   * REST is history-only; authoring uses the WebSocket. The caller
   * supplies a `send` function from `useWebSocket`.
   *
   * @param send - WS send function.
   * @param channelId - Target channel.
   * @param content - Message body.
   */
  function sendMessage(
    send: (data: unknown) => void,
    channelId: string,
    content: string,
  ): void {
    const trimmed = content.trim();
    if (!trimmed) return;
    send({
      type: CHAT_EVENT.MESSAGE,
      payload: { channel_id: channelId, content: trimmed },
    });
  }

  /**
   * @brief Emit a typing indicator on the WS.
   * @param send - WS send function.
   * @param channelId - Channel the user is typing in.
   */
  function sendTyping(
    send: (data: unknown) => void,
    channelId: string,
  ): void {
    send({
      type: CHAT_EVENT.TYPING,
      payload: { channel_id: channelId },
    });
  }

  /**
   * @brief Mark a message as read (display-only read receipt).
   * @param send - WS send function.
   * @param channelId - Channel id.
   * @param messageId - Message id that was read.
   */
  function markRead(
    send: (data: unknown) => void,
    channelId: string,
    messageId: string,
  ): void {
    lastReadByChannel[channelId] = messageId;
    unreadByChannel[channelId] = 0;
    send({
      type: CHAT_EVENT.READ,
      payload: { channel_id: channelId, message_id: messageId },
    });
  }

  /**
   * @brief Placeholder for edit flow. Backend exposes this via REST/WS
   *        in a future patch; for now we optimistically mutate locally.
   * @param messageId - ID to edit.
   * @param channelId - Channel owning the message.
   * @param content - New content.
   */
  function editMessage(
    messageId: string,
    channelId: string,
    content: string,
  ): void {
    const entry = messagesByChannel[channelId];
    if (!entry) return;
    const msg = entry.items.find((m) => m.id === messageId);
    if (msg) {
      msg.content = content;
      msg.edited_at = new Date().toISOString();
    }
  }

  /**
   * @brief Placeholder soft-delete applied locally; server deletes are
   *        broadcast back via `chat.deleted` and handled there.
   * @param messageId - ID to delete.
   * @param channelId - Channel owning the message.
   */
  function deleteMessage(messageId: string, channelId: string): void {
    applyDeleted({
      id: messageId,
      channel_id: channelId,
      deleted: true,
      edited_at: new Date().toISOString(),
    });
  }

  /**
   * @brief Insert a new message at the head of a channel's history.
   *
   * Deduplicates by message id so own-authored echoes are safe.
   * Increments unread unless this is the active channel.
   * @param message - Incoming chat message.
   */
  function applyMessage(message: ChatMessage): void {
    if (!messagesByChannel[message.channel_id]) {
      messagesByChannel[message.channel_id] = {
        items: [],
        cursor: null,
        hasMore: true,
        loading: false,
      };
    }
    const entry = messagesByChannel[message.channel_id];
    if (entry.items.some((m) => m.id === message.id)) return;
    entry.items.unshift(message);

    if (activeChannelId.value !== message.channel_id) {
      unreadByChannel[message.channel_id] =
        (unreadByChannel[message.channel_id] || 0) + 1;
    }
  }

  /**
   * @brief Apply an edit broadcast (chat.updated).
   * @param message - The updated message payload.
   */
  function applyUpdated(message: ChatMessage): void {
    const entry = messagesByChannel[message.channel_id];
    if (!entry) return;
    const idx = entry.items.findIndex((m) => m.id === message.id);
    if (idx === -1) return;
    entry.items[idx] = { ...entry.items[idx], ...message };
  }

  /**
   * @brief Apply a tombstone broadcast (chat.deleted).
   * @param payload - Tombstone data.
   */
  function applyDeleted(payload: ChatDeletedPayload): void {
    const entry = messagesByChannel[payload.channel_id];
    if (!entry) return;
    const idx = entry.items.findIndex((m) => m.id === payload.id);
    if (idx === -1) return;
    entry.items[idx] = {
      ...entry.items[idx],
      content: "[deleted]",
      deleted: true,
      edited_at: payload.edited_at,
    };
  }

  /**
   * @brief Apply a typing indicator from another user.
   * @param payload - Typing event payload.
   */
  function applyTyping(payload: ChatTypingPayload): void {
    if (!payload.user_id) return;
    if (!typingByChannel[payload.channel_id]) {
      typingByChannel[payload.channel_id] = { users: new Map() };
    }
    const state = typingByChannel[payload.channel_id];
    state.users.set(payload.user_id, Date.now() + TYPING_TTL_MS);
  }

  /**
   * @brief Drop expired typing indicators (call on a short interval).
   */
  function pruneTyping(): void {
    const now = Date.now();
    for (const cid of Object.keys(typingByChannel)) {
      const state = typingByChannel[cid];
      for (const [uid, expiry] of state.users) {
        if (expiry < now) state.users.delete(uid);
      }
    }
  }

  /**
   * @brief Apply a read receipt from another user.
   * @param payload - Read event payload.
   */
  function applyRead(payload: ChatReadPayload): void {
    if (!payload.user_id) return;
    /* Display-only per plan — no persisted extra state beyond last-read. */
    lastReadByChannel[`${payload.channel_id}:${payload.user_id}`] =
      payload.message_id;
  }

  /**
   * @brief Main dispatcher for inbound chat WS frames.
   *
   * Accepts the already-parsed frame envelope `{type, payload, ts}`.
   * @param frame - Decoded WS frame.
   */
  function handleInboundWsMessage(frame: {
    type: string;
    payload: unknown;
  }): void {
    switch (frame.type) {
      case CHAT_EVENT.MESSAGE:
        applyMessage(frame.payload as ChatMessage);
        break;
      case CHAT_EVENT.UPDATED:
        applyUpdated(frame.payload as ChatMessage);
        break;
      case CHAT_EVENT.DELETED:
        applyDeleted(frame.payload as ChatDeletedPayload);
        break;
      case CHAT_EVENT.TYPING:
        applyTyping(frame.payload as ChatTypingPayload);
        break;
      case CHAT_EVENT.READ:
        applyRead(frame.payload as ChatReadPayload);
        break;
      case CHAT_EVENT.ERROR:
        lastError.value = frame.payload as ChatErrorPayload;
        break;
      default:
      /* Ignore non-chat frames; other stores may consume them. */
    }
  }

  /**
   * @brief Set the active channel and clear its unread count.
   * @param channelId - Channel being viewed, or null when leaving chat.
   */
  function setActiveChannel(channelId: string | null): void {
    activeChannelId.value = channelId;
    if (channelId) {
      unreadByChannel[channelId] = 0;
    }
  }

  /** @brief Reset all chat state (used on logout). */
  function reset(): void {
    channels.value = [];
    dmThreads.value = [];
    for (const k of Object.keys(messagesByChannel)) {
      Reflect.deleteProperty(messagesByChannel, k);
    }
    for (const k of Object.keys(typingByChannel)) {
      Reflect.deleteProperty(typingByChannel, k);
    }
    for (const k of Object.keys(unreadByChannel)) {
      Reflect.deleteProperty(unreadByChannel, k);
    }
    for (const k of Object.keys(lastReadByChannel)) {
      Reflect.deleteProperty(lastReadByChannel, k);
    }
    activeChannelId.value = null;
    lastError.value = null;
  }

  return {
    /* State */
    channels,
    dmThreads,
    loadingChannels,
    messagesByChannel,
    typingByChannel,
    unreadByChannel,
    lastReadByChannel,
    activeChannelId,
    lastError,
    totalUnread,
    /* Actions */
    fetchChannels,
    fetchDmThreads,
    fetchHistory,
    openDm,
    upsertChannel,
    sendMessage,
    sendTyping,
    markRead,
    editMessage,
    deleteMessage,
    applyMessage,
    applyUpdated,
    applyDeleted,
    applyTyping,
    applyRead,
    pruneTyping,
    handleInboundWsMessage,
    setActiveChannel,
    reset,
  };
});
