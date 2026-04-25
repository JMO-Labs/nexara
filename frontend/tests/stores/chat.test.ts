/**
 * @file tests/stores/chat.test.ts
 * @brief TDD tests for the chat Pinia store.
 *
 * Covers channel fetch, history pagination, WS frame routing,
 * typing indicator state, unread counts, and DM resolution.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useChatStore } from "~/stores/chat";
import type {
  ChatChannel,
  ChatMessage,
  MessageHistoryResponse,
} from "~/types/api";

const mockChannel: ChatChannel = {
  id: "chan-1",
  community_id: "comm-1",
  name: "general",
  channel_type: "community",
  subgroup_id: null,
  created_at: "2026-04-01T10:00:00Z",
};

const mockDmChannel: ChatChannel = {
  id: "chan-dm",
  community_id: "comm-1",
  name: "Alice",
  channel_type: "direct",
  subgroup_id: null,
  created_at: "2026-04-02T10:00:00Z",
};

const mockMessage: ChatMessage = {
  id: "msg-1",
  channel_id: "chan-1",
  author: {
    id: "user-1",
    username: "alice",
    display_name: "Alice",
    avatar_url: null,
  },
  content: "Hello chat",
  edited_at: null,
  deleted: false,
  created_at: "2026-04-18T10:00:00Z",
};

const mockGet = vi.fn();
const mockPostFn = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPostFn,
    put: vi.fn(),
    del: vi.fn(),
  }),
}));

describe("chat store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("starts with empty state", () => {
    const store = useChatStore();

    expect(store.channels).toEqual([]);
    expect(store.activeChannelId).toBeNull();
    expect(store.totalUnread).toBe(0);
  });

  it("fetchChannels() populates channels list", async () => {
    const store = useChatStore();
    mockGet.mockResolvedValueOnce([mockChannel]);

    await store.fetchChannels();

    expect(mockGet).toHaveBeenCalledWith("/chat/channels");
    expect(store.channels).toHaveLength(1);
    expect(store.channels[0].id).toBe("chan-1");
  });

  it("fetchHistory() loads newest-first and sets pagination", async () => {
    const store = useChatStore();
    const response: MessageHistoryResponse = {
      items: [mockMessage],
      cursor: "next-cursor",
      has_more: true,
    };
    mockGet.mockResolvedValueOnce(response);

    await store.fetchHistory("chan-1", true);

    expect(mockGet).toHaveBeenCalledWith(
      "/chat/channels/chan-1/messages?limit=50",
    );
    expect(store.messagesByChannel["chan-1"].items).toHaveLength(1);
    expect(store.messagesByChannel["chan-1"].cursor).toBe("next-cursor");
    expect(store.messagesByChannel["chan-1"].hasMore).toBe(true);
  });

  it("fetchHistory() appends older page when cursor is present", async () => {
    const store = useChatStore();
    store.messagesByChannel["chan-1"] = {
      items: [mockMessage],
      cursor: "cursor-1",
      hasMore: true,
      loading: false,
    };

    const older: ChatMessage = {
      ...mockMessage,
      id: "msg-0",
      created_at: "2026-04-17T09:00:00Z",
    };
    mockGet.mockResolvedValueOnce({
      items: [older],
      cursor: null,
      has_more: false,
    });

    await store.fetchHistory("chan-1");

    expect(store.messagesByChannel["chan-1"].items).toHaveLength(2);
    expect(store.messagesByChannel["chan-1"].items[1].id).toBe("msg-0");
    expect(store.messagesByChannel["chan-1"].hasMore).toBe(false);
  });

  it("openDm() calls POST /chat/dm/{peerId} and upserts the channel", async () => {
    const store = useChatStore();
    mockPostFn.mockResolvedValueOnce(mockDmChannel);

    const channel = await store.openDm("user-2");

    expect(mockPostFn).toHaveBeenCalledWith("/chat/dm/user-2");
    expect(channel.id).toBe("chan-dm");
    expect(store.channels.some((c) => c.id === "chan-dm")).toBe(true);
  });

  it("applyMessage() prepends message and bumps unread for non-active channel", () => {
    const store = useChatStore();
    store.setActiveChannel("other-channel");

    store.applyMessage(mockMessage);

    const entry = store.messagesByChannel["chan-1"];
    expect(entry.items[0].id).toBe("msg-1");
    expect(store.unreadByChannel["chan-1"]).toBe(1);
  });

  it("applyMessage() does NOT bump unread for the active channel", () => {
    const store = useChatStore();
    store.setActiveChannel("chan-1");

    store.applyMessage(mockMessage);

    expect(store.unreadByChannel["chan-1"] ?? 0).toBe(0);
  });

  it("applyMessage() deduplicates by id", () => {
    const store = useChatStore();
    store.applyMessage(mockMessage);
    store.applyMessage(mockMessage);

    expect(store.messagesByChannel["chan-1"].items).toHaveLength(1);
  });

  it("applyUpdated() edits an existing message in place", () => {
    const store = useChatStore();
    store.applyMessage(mockMessage);

    store.applyUpdated({
      ...mockMessage,
      content: "edited body",
      edited_at: "2026-04-18T10:05:00Z",
    });

    const m = store.messagesByChannel["chan-1"].items[0];
    expect(m.content).toBe("edited body");
    expect(m.edited_at).toBe("2026-04-18T10:05:00Z");
  });

  it("applyDeleted() replaces content with [deleted] tombstone", () => {
    const store = useChatStore();
    store.applyMessage(mockMessage);

    store.applyDeleted({
      id: "msg-1",
      channel_id: "chan-1",
      deleted: true,
      edited_at: "2026-04-18T10:10:00Z",
    });

    const m = store.messagesByChannel["chan-1"].items[0];
    expect(m.deleted).toBe(true);
    expect(m.content).toBe("[deleted]");
  });

  it("applyTyping() tracks user in typing state", () => {
    const store = useChatStore();
    store.applyTyping({ channel_id: "chan-1", user_id: "user-2" });

    expect(store.typingByChannel["chan-1"].users.has("user-2")).toBe(true);
  });

  it("handleInboundWsMessage() routes chat.message frames to applyMessage", () => {
    const store = useChatStore();
    store.setActiveChannel("chan-1");

    store.handleInboundWsMessage({
      type: "chat.message",
      payload: mockMessage,
    });

    expect(store.messagesByChannel["chan-1"].items[0].id).toBe("msg-1");
  });

  it("handleInboundWsMessage() stores error frames on lastError", () => {
    const store = useChatStore();

    store.handleInboundWsMessage({
      type: "chat.error",
      payload: { code: "rate_limited", message: "Too fast" },
    });

    expect(store.lastError?.code).toBe("rate_limited");
  });

  it("sendMessage() emits a chat.message frame through the socket", () => {
    const store = useChatStore();
    const send = vi.fn();

    store.sendMessage(send, "chan-1", "hi there");

    expect(send).toHaveBeenCalledWith({
      type: "chat.message",
      payload: { channel_id: "chan-1", content: "hi there" },
    });
  });

  it("sendMessage() ignores blank content", () => {
    const store = useChatStore();
    const send = vi.fn();

    store.sendMessage(send, "chan-1", "   ");

    expect(send).not.toHaveBeenCalled();
  });

  it("markRead() clears channel unread and emits a chat.read frame", () => {
    const store = useChatStore();
    store.unreadByChannel["chan-1"] = 5;
    const send = vi.fn();

    store.markRead(send, "chan-1", "msg-9");

    expect(store.unreadByChannel["chan-1"]).toBe(0);
    expect(store.lastReadByChannel["chan-1"]).toBe("msg-9");
    expect(send).toHaveBeenCalledWith({
      type: "chat.read",
      payload: { channel_id: "chan-1", message_id: "msg-9" },
    });
  });

  it("totalUnread computes the sum across channels", () => {
    const store = useChatStore();
    store.unreadByChannel["a"] = 2;
    store.unreadByChannel["b"] = 3;

    expect(store.totalUnread).toBe(5);
  });

  it("reset() clears all state", () => {
    const store = useChatStore();
    store.channels = [mockChannel];
    store.applyMessage(mockMessage);
    store.unreadByChannel["chan-1"] = 3;

    store.reset();

    expect(store.channels).toEqual([]);
    expect(store.messagesByChannel["chan-1"]).toBeUndefined();
    expect(store.unreadByChannel["chan-1"]).toBeUndefined();
  });
});
