/**
 * @file tests/components/chat/MessageItem.test.ts
 * @brief Tests for the chat MessageItem component.
 *
 * Verifies author rendering, edited badge, deleted tombstone styling,
 * inline edit flow, hover actions visibility, and emitted events.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import MessageItem from "~/components/chat/MessageItem.vue";
import type { ChatMessage } from "~/types/api";

vi.mock("~/utils/date", () => ({
  timeAgo: (_iso: string) => "just now",
}));

const baseMessage: ChatMessage = {
  id: "msg-1",
  channel_id: "chan-1",
  author: {
    id: "user-1",
    username: "alice",
    display_name: "Alice",
    avatar_url: null,
  },
  content: "Hello world",
  edited_at: null,
  deleted: false,
  created_at: "2026-04-18T10:00:00Z",
};

describe("MessageItem", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("renders the message content and author name", () => {
    const wrapper = mount(MessageItem, {
      props: { message: baseMessage },
    });

    expect(wrapper.text()).toContain("Alice");
    expect(
      wrapper.find('[data-testid="chat-message-content"]').text(),
    ).toBe("Hello world");
  });

  it("shows the edited badge when edited_at is set", () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: { ...baseMessage, edited_at: "2026-04-18T10:05:00Z" },
      },
    });

    expect(
      wrapper.find('[data-testid="chat-message-edited"]').exists(),
    ).toBe(true);
  });

  it("renders the deleted tombstone with italic styling", () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: { ...baseMessage, deleted: true, content: "[deleted]" },
      },
    });

    const body = wrapper.find('[data-testid="chat-message-content"]');
    expect(body.text()).toBe("[deleted]");
    expect(body.classes()).toContain("italic");
  });

  it("hides edit/delete actions when not the author", () => {
    const wrapper = mount(MessageItem, {
      props: { message: baseMessage, currentUserId: "other-user" },
    });

    expect(wrapper.find('[data-testid="chat-message-edit"]').exists()).toBe(
      false,
    );
    expect(
      wrapper.find('[data-testid="chat-message-delete"]').exists(),
    ).toBe(false);
  });

  it("shows edit/delete actions for own messages", () => {
    const wrapper = mount(MessageItem, {
      props: { message: baseMessage, currentUserId: "user-1" },
    });

    expect(wrapper.find('[data-testid="chat-message-edit"]').exists()).toBe(
      true,
    );
    expect(
      wrapper.find('[data-testid="chat-message-delete"]').exists(),
    ).toBe(true);
  });

  it("shows actions for admins on any non-deleted message", () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: baseMessage,
        currentUserId: "other-user",
        isAdmin: true,
      },
    });

    expect(wrapper.find('[data-testid="chat-message-edit"]').exists()).toBe(
      true,
    );
  });

  it("emits delete with message id when delete is clicked", async () => {
    const wrapper = mount(MessageItem, {
      props: { message: baseMessage, currentUserId: "user-1" },
    });

    await wrapper.get('[data-testid="chat-message-delete"]').trigger("click");

    expect(wrapper.emitted("delete")?.[0]).toEqual(["msg-1"]);
  });

  it("enters edit mode and emits edit event with trimmed content", async () => {
    const wrapper = mount(MessageItem, {
      props: { message: baseMessage, currentUserId: "user-1" },
    });

    await wrapper.get('[data-testid="chat-message-edit"]').trigger("click");
    const input = wrapper.get('[data-testid="chat-message-edit-input"]');
    await input.setValue("  edited body  ");
    await wrapper
      .get('[data-testid="chat-message-edit-save"]')
      .trigger("click");

    expect(wrapper.emitted("edit")?.[0]).toEqual(["msg-1", "edited body"]);
  });

  it("cancels edit mode without emitting", async () => {
    const wrapper = mount(MessageItem, {
      props: { message: baseMessage, currentUserId: "user-1" },
    });

    await wrapper.get('[data-testid="chat-message-edit"]').trigger("click");
    await wrapper
      .get('[data-testid="chat-message-edit-cancel"]')
      .trigger("click");

    expect(wrapper.emitted("edit")).toBeUndefined();
    expect(
      wrapper.find('[data-testid="chat-message-edit-input"]').exists(),
    ).toBe(false);
  });
});
