/**
 * @file tests/unit/motion/message-slide.test.tsx
 * @brief MessageList new-message slide-up: only appended messages animate,
 *        slide props survive re-renders, reduced motion skips; plus the
 *        NotificationsBell badge pop respects reduced motion.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

let reduced = false;
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});
vi.mock("@/lib/api/notifications", () => ({
  getUnreadCount: vi.fn().mockResolvedValue({ count: 2 }),
  listNotifications: vi.fn().mockResolvedValue({ items: [] }),
  markAllRead: vi.fn(),
  markRead: vi.fn(),
  STREAM_PATH: "/s",
}));
vi.mock("@/hooks/useSSE", () => ({ useSSE: vi.fn() }));

import { MessageList } from "@/components/chat/MessageList";
import { NotificationsBell } from "@/components/notifications/NotificationsBell";
import { useSession } from "@/stores/session";
import type { ChatMessage } from "@/lib/api/chat";

const msg = (id: string, offsetMs = 0): ChatMessage => ({
  id,
  channel_id: "c1",
  author: { id: "u1", username: "a", display_name: "Alex", avatar_url: null },
  content: `text ${id}`,
  edited_at: null,
  deleted: false,
  created_at: new Date(Date.now() + offsetMs).toISOString(),
});
const props = { isLoading: false, hasMore: false, isFetchingMore: false };
const list = (messages: ChatMessage[]) => (
  <MessageList messages={messages} onLoadMore={vi.fn()} {...props} />
);
const row = (id: string) =>
  screen.getByText(`text ${id}`).closest("[data-testid='message-row']")!;

let rectSpy: { mockRestore: () => void };
beforeEach(() => {
  reduced = false;
  // jsdom has no layout; stub sizes so the virtualizer yields rows.
  rectSpy = vi
    .spyOn(HTMLElement.prototype, "getBoundingClientRect")
    .mockReturnValue({ width: 400, height: 800 } as DOMRect);
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    value: 800,
  });
});
afterEach(() => rectSpy.mockRestore());

describe("MessageList slide-up", () => {
  it("does not animate messages present on first paint", () => {
    render(list([msg("b", 1), msg("a")]));
    expect(row("a").getAttribute("data-new")).toBe("false");
    expect((row("a") as HTMLElement).style.opacity).toBe("");
  });

  it("slides in a newly appended message only", () => {
    const { rerender } = render(list([msg("a")]));
    rerender(list([msg("b", 1000), msg("a")]));
    const b = row("b") as HTMLElement;
    expect(b.getAttribute("data-new")).toBe("true");
    expect(b).toHaveStyle({ opacity: "0" });
    expect(b.style.transform).toContain("translateY(12px)");
    expect((row("a") as HTMLElement).style.opacity).toBe("");
  });

  it("keeps slide props across re-renders until animation completes", () => {
    const first = [msg("a")];
    const { rerender } = render(list(first));
    const next = [msg("b", 1000), ...first];
    rerender(list(next));
    rerender(list([...next]));
    rerender(list([...next]));
    expect(row("b").getAttribute("data-new")).toBe("true");
  });

  it("does not animate older pages loaded at the top", () => {
    const { rerender } = render(list([msg("b", 1000)]));
    rerender(list([msg("b", 1000), msg("a")]));
    expect(row("a").getAttribute("data-new")).toBe("false");
  });

  it("has no transform/opacity under reduced motion", () => {
    reduced = true;
    const { rerender } = render(list([msg("a")]));
    rerender(list([msg("b", 1000), msg("a")]));
    const b = row("b") as HTMLElement;
    expect(b.style.opacity).toBe("");
    expect(b.style.transform).toBe("");
  });
});

describe("NotificationsBell badge motion", () => {
  const setup = () => {
    useSession.setState({ status: "authenticated" } as never);
    return render(
      <QueryClientProvider client={new QueryClient()}>
        <NotificationsBell />
      </QueryClientProvider>,
    );
  };
  it("pops the badge in", async () => {
    setup();
    const badge = await screen.findByTestId("unread-badge");
    // Animation may have started by the time we read it: assert the pop
    // is in progress (scale between initial 0.6 and final 1), not an exact frame.
    const m = /scale\(([\d.]+)\)/.exec(badge.style.transform);
    expect(m).not.toBeNull();
    const scale = Number(m![1]);
    expect(scale).toBeGreaterThanOrEqual(0.6);
    expect(scale).toBeLessThanOrEqual(1);
  });
  it("renders the badge statically under reduced motion", async () => {
    reduced = true;
    setup();
    const badge = await screen.findByTestId("unread-badge");
    expect(badge.style.transform).toBe("");
    expect(badge.style.opacity).toBe("");
  });
});
