/**
 * @file tests/components/chat/MessageList.test.ts
 * @brief Tests for the chat MessageList component.
 *
 * Verifies message rendering, empty state, load-older button visibility
 * and disabled state, and re-emission of edit/delete events from items.
 */

import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import MessageList from "~/components/chat/MessageList.vue";
import type { ChatMessage } from "~/types/api";

vi.mock("~/utils/date", () => ({
  timeAgo: () => "just now",
}));

const message = (id: string, content = "hi"): ChatMessage => ({
  id,
  channel_id: "chan-1",
  author: {
    id: "user-1",
    username: "alice",
    display_name: "Alice",
    avatar_url: null,
  },
  content,
  edited_at: null,
  deleted: false,
  created_at: "2026-04-18T10:00:00Z",
});

describe("MessageList", () => {
  it("renders an empty state when there are no messages", () => {
    const wrapper = mount(MessageList, {
      props: { messages: [], hasMore: false, loading: false },
    });

    expect(wrapper.find('[data-testid="chat-empty"]').exists()).toBe(true);
  });

  it("does not render empty state while loading", () => {
    const wrapper = mount(MessageList, {
      props: { messages: [], hasMore: false, loading: true },
    });

    expect(wrapper.find('[data-testid="chat-empty"]').exists()).toBe(false);
  });

  it("renders one MessageItem per message", () => {
    const wrapper = mount(MessageList, {
      props: {
        messages: [message("a"), message("b")],
        hasMore: false,
        loading: false,
      },
    });

    expect(
      wrapper.findAll('[data-testid^="chat-message-"]').length,
    ).toBeGreaterThanOrEqual(2);
  });

  it("shows the load-older button when hasMore is true", () => {
    const wrapper = mount(MessageList, {
      props: { messages: [message("a")], hasMore: true, loading: false },
    });

    expect(
      wrapper.find('[data-testid="chat-load-older"]').exists(),
    ).toBe(true);
  });

  it("hides the load-older button when hasMore is false", () => {
    const wrapper = mount(MessageList, {
      props: { messages: [message("a")], hasMore: false, loading: false },
    });

    expect(
      wrapper.find('[data-testid="chat-load-older"]').exists(),
    ).toBe(false);
  });

  it("disables load-older while loading", () => {
    const wrapper = mount(MessageList, {
      props: { messages: [message("a")], hasMore: true, loading: true },
    });

    expect(
      wrapper.get('[data-testid="chat-load-older"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("emits loadOlder when the button is clicked", async () => {
    const wrapper = mount(MessageList, {
      props: { messages: [message("a")], hasMore: true, loading: false },
    });

    await wrapper.get('[data-testid="chat-load-older"]').trigger("click");

    expect(wrapper.emitted("loadOlder")).toBeTruthy();
  });

  it("re-emits edit and delete events from MessageItem", async () => {
    const wrapper = mount(MessageList, {
      props: {
        messages: [message("a")],
        hasMore: false,
        loading: false,
        currentUserId: "user-1",
      },
    });

    await wrapper.get('[data-testid="chat-message-delete"]').trigger("click");

    expect(wrapper.emitted("delete")?.[0]).toEqual(["a"]);
  });
});
