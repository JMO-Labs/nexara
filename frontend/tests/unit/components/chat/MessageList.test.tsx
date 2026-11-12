/**
 * @file tests/unit/components/chat/MessageList.test.tsx
 * @brief Chat message list: grouping, date labels, loading/empty/error states.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MessageList } from "@/components/chat/MessageList";
import { dayLabel, isGrouped } from "@/components/chat/grouping";
import type { ChatMessage } from "@/lib/api/chat";

const msg = (id: string, author: string, iso: string): ChatMessage =>
  ({
    id,
    channel_id: "c",
    author: {
      id: author,
      username: author,
      display_name: author,
      avatar_url: null,
    },
    content: id,
    edited_at: null,
    deleted: false,
    created_at: iso,
  }) as ChatMessage;

const base = {
  isLoading: false,
  hasMore: false,
  isFetchingMore: false,
  onLoadMore: () => {},
};

describe("grouping helpers", () => {
  const now = new Date("2026-11-12T12:00:00");
  it("labels Today / Yesterday / date", () => {
    expect(dayLabel("2026-11-12T08:00:00", now)).toBe("Today");
    expect(dayLabel("2026-11-11T23:00:00", now)).toBe("Yesterday");
    expect(dayLabel("2026-11-01T10:00:00", now)).toBe("November 1, 2026");
  });
  it("groups same sender within 5 min on the same day only", () => {
    const a = msg("a", "u1", "2026-11-12T10:00:00");
    expect(isGrouped(a, msg("b", "u1", "2026-11-12T10:02:00"))).toBe(true);
    expect(isGrouped(a, msg("b", "u2", "2026-11-12T10:02:00"))).toBe(false);
    expect(isGrouped(a, msg("b", "u1", "2026-11-12T10:30:00"))).toBe(false);
    const late = msg("c", "u1", "2026-11-11T23:59:00");
    expect(isGrouped(late, msg("d", "u1", "2026-11-12T00:00:30"))).toBe(false);
    expect(isGrouped(undefined, a)).toBe(false);
  });
});

describe("MessageList states", () => {
  it("shows skeleton while loading", () => {
    const { container } = render(
      <MessageList {...base} messages={[]} isLoading />,
    );
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
  });
  it("shows empty state with start CTA", () => {
    const onStart = vi.fn();
    render(
      <MessageList {...base} messages={[]} onStartConversation={onStart} />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /start conversation/i }),
    );
    expect(onStart).toHaveBeenCalled();
  });
  it("shows error with retry", () => {
    const onRetry = vi.fn();
    render(<MessageList {...base} messages={[]} isError onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });
});
