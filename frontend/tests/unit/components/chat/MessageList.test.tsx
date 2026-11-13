/**
 * @file tests/unit/components/chat/MessageList.test.tsx
 * @brief Chat message list: grouping, date labels, loading/empty/error states.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MessageList } from "@/components/chat/MessageList";
import { dayLabel, isGrouped, startsNewDay } from "@/components/chat/grouping";
import type { ChatMessage } from "@/lib/api/chat";

vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: (o: {
    count: number;
    getItemKey: (i: number) => string | number;
  }) => ({
    getTotalSize: () => o.count * 64,
    getVirtualItems: () =>
      Array.from({ length: o.count }, (_, index) => ({
        index,
        key: o.getItemKey(index),
        start: index * 64,
      })),
    measureElement: () => {},
  }),
}));

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

describe("startsNewDay", () => {
  it("is true for the first message and on day change only", () => {
    const a = msg("a", "u1", "2026-11-11T23:58:00");
    expect(startsNewDay(undefined, a)).toBe(true);
    expect(startsNewDay(a, msg("b", "u1", "2026-11-11T23:59:00"))).toBe(false);
    expect(startsNewDay(a, msg("c", "u1", "2026-11-12T00:01:00"))).toBe(true);
  });
});

describe("MessageList rendering", () => {
  // Backend order is newest-first; the list reverses it.
  const two = [
    msg("new", "u1", "2026-11-12T09:00:00"),
    msg("old", "u1", "2026-11-11T09:00:00"),
  ];
  it("renders a separator between messages on different days", () => {
    render(<MessageList {...base} messages={two} />);
    expect(screen.getAllByRole("separator")).toHaveLength(2);
  });
  it("renders no extra separator within one day", () => {
    render(
      <MessageList
        {...base}
        messages={[
          msg("b", "u1", "2026-11-12T09:05:00"),
          msg("a", "u1", "2026-11-12T09:00:00"),
        ]}
      />,
    );
    expect(screen.getAllByRole("separator")).toHaveLength(1);
  });
  const bubble = (c: HTMLElement) => c.querySelector(".rounded-2xl");
  const row = (c: HTMLElement, id: string) =>
    c.querySelector(`[data-message-id='${id}']`);
  it("applies compact density spacing to message rows", () => {
    const { container } = render(
      <MessageList {...base} messages={two} density="compact" />,
    );
    expect(bubble(container)?.className).toContain("py-1");
    expect(bubble(container)?.className).toContain("text-xs");
  });
  it("applies comfortable density spacing to message rows", () => {
    const { container } = render(<MessageList {...base} messages={two} />);
    expect(bubble(container)?.className).toContain("py-2");
    expect(bubble(container)?.className).not.toContain("text-xs");
    expect(row(container, "old")?.className).toContain("py-1.5");
  });
  it("hides the author header for a grouped follow-up", () => {
    render(
      <MessageList
        {...base}
        messages={[
          msg("b", "u1", "2026-11-12T09:03:00"),
          msg("a", "u1", "2026-11-12T09:00:00"),
        ]}
      />,
    );
    expect(screen.getAllByText("u1")).toHaveLength(1);
    expect(screen.getAllByRole("img", { name: "u1" })).toHaveLength(1);
  });
  const isNew = (c: HTMLElement, id: string) =>
    row(c, id)
      ?.closest("[data-testid='message-row']")
      ?.getAttribute("data-new");
  it("marks only messages that arrive after first render as new", () => {
    const { container, rerender } = render(
      <MessageList {...base} messages={two} />,
    );
    rerender(
      <MessageList
        {...base}
        messages={[msg("live", "u2", "2026-11-12T09:10:00"), ...two]}
      />,
    );
    expect(isNew(container, "live")).toBe("true");
    expect(isNew(container, "new")).toBe("false");
    expect(isNew(container, "old")).toBe("false");
  });
  it("does not mark history arriving after the loading render", () => {
    const { container, rerender } = render(
      <MessageList {...base} messages={[]} isLoading />,
    );
    rerender(<MessageList {...base} messages={two} />);
    expect(container.querySelectorAll("[data-new='true']")).toHaveLength(0);
  });
  it("does not mark an older page", () => {
    const { container, rerender } = render(
      <MessageList {...base} messages={two} />,
    );
    rerender(
      <MessageList
        {...base}
        messages={[...two, msg("older", "u3", "2026-11-10T09:00:00")]}
      />,
    );
    expect(container.querySelectorAll("[data-new='true']")).toHaveLength(0);
  });
});
