/**
 * @file tests/unit/chat/MessageList.test.tsx
 * @brief MessageList empty, loading and populated states.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageList } from "@/components/chat/MessageList";
import type { ChatMessage } from "@/lib/api/chat";

const msg: ChatMessage = {
  id: "m1",
  channel_id: "c1",
  author: { id: "u1", username: "a", display_name: "Alex", avatar_url: null },
  content: "hello",
  edited_at: null,
  deleted: false,
  created_at: new Date().toISOString(),
};
const props = {
  hasMore: false,
  isFetchingMore: false,
  onLoadMore: vi.fn(),
};

describe("MessageList", () => {
  it("shows empty state", () => {
    render(<MessageList messages={[]} isLoading={false} {...props} />);
    expect(screen.getByText("No messages yet")).toBeInTheDocument();
  });
  it("shows skeletons while loading", () => {
    render(<MessageList messages={[]} isLoading {...props} />);
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });
  it("renders messages", () => {
    // jsdom has no layout; stub sizes so the virtualizer yields rows.
    const spy = vi
      .spyOn(HTMLElement.prototype, "getBoundingClientRect")
      .mockReturnValue({ width: 400, height: 400 } as DOMRect);
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      value: 400,
    });
    render(<MessageList messages={[msg]} isLoading={false} {...props} />);
    expect(screen.getByText("hello")).toBeInTheDocument();
    spy.mockRestore();
  });
});
