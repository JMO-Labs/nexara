/**
 * @file tests/unit/components/presenceStore.test.tsx
 * @brief Presence store batching/ref-counting and Avatar online dot.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";

const fetchPresence = vi.fn();
vi.mock("@/lib/api/presence", () => ({
  PRESENCE_MAX_IDS: 200,
  fetchPresence: (...a: unknown[]) => fetchPresence(...a),
}));

import {
  watchPresence,
  unwatchPresence,
  flushPresence,
  resetPresence,
  usePresenceStore,
} from "@/stores/presence";
import { Avatar } from "@/components/ui/Avatar";

beforeEach(() => {
  vi.useFakeTimers();
  fetchPresence.mockReset();
  fetchPresence.mockResolvedValue({ online: [], last_seen: {} });
  resetPresence();
});
afterEach(() => vi.useRealTimers());

describe("presence store", () => {
  it("batches new ids into one debounced request", async () => {
    watchPresence(["a", "b"]);
    watchPresence(["c"]);
    await act(() => vi.advanceTimersByTimeAsync(400));
    expect(fetchPresence).toHaveBeenCalledTimes(1);
    expect(fetchPresence.mock.calls[0][0].sort()).toEqual(["a", "b", "c"]);
  });

  it("ref-counts: shared id stays until last unwatch", async () => {
    watchPresence(["a"]);
    watchPresence(["a"]);
    unwatchPresence(["a"]);
    await flushPresence();
    expect(fetchPresence).toHaveBeenCalledWith(["a"]);
    unwatchPresence(["a"]);
    fetchPresence.mockClear();
    await flushPresence();
    expect(fetchPresence).not.toHaveBeenCalled();
  });

  it("chunks at 200 ids", async () => {
    watchPresence(Array.from({ length: 450 }, (_, i) => `u${i}`));
    await flushPresence();
    expect(fetchPresence.mock.calls.map((c) => c[0].length)).toEqual([
      200, 200, 50,
    ]);
  });
});

describe("Avatar online dot", () => {
  it("renders dot with sr-only text only when online", () => {
    const { rerender } = render(<Avatar name="Ruth" userId="u1" />);
    expect(screen.queryByTestId("online-dot")).toBeNull();
    act(() => usePresenceStore.setState({ online: { u1: true } }));
    const dot = screen.getByTestId("online-dot");
    expect(dot.className).toMatch(/bg-ok/);
    expect(dot.className).not.toMatch(/animate/);
    expect(dot.textContent).toBe("online");
    rerender(<Avatar name="Ruth" />);
    expect(screen.queryByTestId("online-dot")).toBeNull();
  });
});
