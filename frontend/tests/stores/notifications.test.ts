/**
 * @file tests/stores/notifications.test.ts
 * @brief TDD tests for the notifications Pinia store.
 *
 * Tests markRead() decrements unread count. Mocks useApi() for HTTP calls.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useNotificationsStore } from "~/stores/notifications";

const mockPost = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: vi.fn(),
    post: mockPost,
    put: vi.fn(),
    del: vi.fn(),
  }),
}));

describe("notifications store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockPost.mockResolvedValue({});
  });

  it("markRead() decrements unread count", async () => {
    const store = useNotificationsStore();
    store.unreadCount = 3;
    store.notifications = [
      {
        id: "n1",
        user_id: "u1",
        type: "mention",
        payload: {},
        read_at: null,
        created_at: "2026-02-27T10:00:00Z",
      },
    ];

    await store.markRead("n1");

    expect(mockPost).toHaveBeenCalledWith("/notifications/n1/read");
    expect(store.unreadCount).toBe(2);
  });

  it("handleIncoming() prepends notification and increments unread", () => {
    const store = useNotificationsStore();
    store.unreadCount = 1;

    store.handleIncoming({
      id: "n-new",
      user_id: "u1",
      type: "comment",
      payload: { link: "/app/post/123" },
      read_at: null,
      created_at: "2026-02-28T10:00:00Z",
    });

    expect(store.notifications).toHaveLength(1);
    expect(store.notifications[0].id).toBe("n-new");
    expect(store.unreadCount).toBe(2);
  });

  it("handleIncoming() deduplicates by id", () => {
    const store = useNotificationsStore();
    const notif = {
      id: "n-dup",
      user_id: "u1",
      type: "mention" as const,
      payload: {},
      read_at: null,
      created_at: "2026-02-28T10:00:00Z",
    };
    store.notifications = [notif];

    store.handleIncoming(notif);

    expect(store.notifications).toHaveLength(1);
  });
});
