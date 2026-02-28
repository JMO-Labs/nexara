/**
 * @file tests/components/notifications/NotificationPanel.test.ts
 * @brief TDD tests for the NotificationPanel component.
 *
 * Verifies notification list rendering, fetch on open, mark-all-read, and behavior.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import NotificationPanel from "~/components/notifications/NotificationPanel.vue";
import { useNotificationsStore } from "~/stores/notifications";
import type { Notification } from "~/types/api";

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue({ items: [] }),
    post: vi.fn().mockResolvedValue({}),
  }),
}));

const mockNotifications: Notification[] = [
  {
    id: "1",
    user_id: "u1",
    type: "mention",
    payload: { message: "Alice mentioned you" },
    read_at: null,
    created_at: "2026-02-27T10:00:00Z",
  },
  {
    id: "2",
    user_id: "u1",
    type: "comment",
    payload: { message: "New comment on your post" },
    read_at: "2026-02-27T10:05:00Z",
    created_at: "2026-02-27T10:05:00Z",
  },
];

describe("NotificationPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders notification list", () => {
    const store = useNotificationsStore();
    store.notifications = mockNotifications;

    const wrapper = mount(NotificationPanel, {
      props: { open: true },
    });

    const items = wrapper.findAll("li");
    expect(items).toHaveLength(2);
    expect(items[0].text()).toContain("Alice mentioned you");
    expect(items[1].text()).toContain("New comment on your post");
  });

  it("calls fetchNotifications when panel opens", async () => {
    const store = useNotificationsStore();
    const fetchSpy = vi.spyOn(store, "fetchNotifications").mockResolvedValue();

    const wrapper = mount(NotificationPanel, {
      props: { open: false },
    });

    expect(fetchSpy).not.toHaveBeenCalled();

    await wrapper.setProps({ open: true });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("calls markAllRead when mark all button clicked", async () => {
    const store = useNotificationsStore();
    store.notifications = mockNotifications;
    store.unreadCount = 1;
    const markAllSpy = vi.spyOn(store, "markAllRead").mockResolvedValue();

    const wrapper = mount(NotificationPanel, {
      props: { open: true },
    });

    const markAllBtn = wrapper.find("button");
    expect(markAllBtn.exists()).toBe(true);
    await markAllBtn.trigger("click");

    expect(markAllSpy).toHaveBeenCalledTimes(1);
  });
});
