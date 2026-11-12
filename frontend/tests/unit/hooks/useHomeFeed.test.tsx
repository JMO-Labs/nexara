/**
 * @file tests/unit/hooks/useHomeFeed.test.tsx
 * @brief useHomeFeed: pending buffering while scrolled, reveal, dedupe.
 */
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { vi, describe, it, expect, beforeEach } from "vitest";

let emit: (d: unknown, t: string) => void = () => {};
vi.mock("@/hooks/useSSE", () => ({
  useSSE: (_p: string, o: { onMessage?: typeof emit }) => {
    emit = o.onMessage ?? (() => {});
  },
}));
vi.mock("@/lib/api/home", () => ({ getHomeFeed: vi.fn() }));

import { useHomeFeed } from "@/hooks/useHomeFeed";
import * as api from "@/lib/api/home";

const item = (id: string, t = "2026-10-20T10:00:00Z") =>
  ({
    kind: "activity",
    id,
    created_at: t,
    activity: { id, actor_name: "Sue", verb: "x" },
  }) as unknown as api.FeedItem;

const setScroll = (y: number) =>
  Object.defineProperty(window, "scrollY", { value: y, configurable: true });

describe("useHomeFeed", () => {
  let qc: QueryClient;
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  beforeEach(() => {
    qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.clearAllMocks();
    setScroll(0);
  });

  it("loads items", async () => {
    vi.mocked(api.getHomeFeed).mockResolvedValue({
      items: [item("a")],
      next_cursor: null,
    });
    const { result } = renderHook(() => useHomeFeed(), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
  });

  it("buffers pings while scrolled, reveals on demand", async () => {
    vi.mocked(api.getHomeFeed).mockResolvedValueOnce({
      items: [item("a")],
      next_cursor: null,
    });
    const { result } = renderHook(() => useHomeFeed(), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    setScroll(800);
    vi.mocked(api.getHomeFeed).mockResolvedValueOnce({
      items: [item("c"), item("b"), item("a")],
      next_cursor: null,
    });
    await act(async () => emit({}, "feed_ping"));
    await waitFor(() => expect(result.current.pending).toHaveLength(2));
    expect(result.current.items.map((i) => i.id)).toEqual(["a"]);
    act(() => result.current.reveal());
    expect(result.current.items.map((i) => i.id)).toEqual(["c", "b", "a"]);
    expect(result.current.pending).toHaveLength(0);
    expect(result.current.freshIds.has("activity:c")).toBe(true);
  });

  it("inserts immediately at top", async () => {
    vi.mocked(api.getHomeFeed).mockResolvedValueOnce({
      items: [item("a")],
      next_cursor: null,
    });
    const { result } = renderHook(() => useHomeFeed(), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    vi.mocked(api.getHomeFeed).mockResolvedValueOnce({
      items: [item("b"), item("a")],
      next_cursor: null,
    });
    await act(async () => emit({}, "feed_update"));
    await waitFor(() => expect(result.current.items).toHaveLength(2));
    expect(result.current.pending).toHaveLength(0);
    expect(result.current.items[0].id).toBe("b");
  });
});
