/**
 * @file tests/unit/hooks/useSSE.test.tsx
 * @brief useSSE shares one ref-counted EventSource per path.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSSE } from "@/hooks/useSSE";

vi.mock("@/lib/auth/session", () => ({
  API_BASE: "http://x",
  getAccessToken: () => "tok",
  refreshAccessToken: vi.fn(),
}));

class FakeES {
  static all: FakeES[] = [];
  url: string;
  closed = false;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  onopen: (() => void) | null = null;
  listeners = new Map<string, ((e: MessageEvent) => void)[]>();
  constructor(url: string) {
    this.url = url;
    FakeES.all.push(this);
  }
  addEventListener(t: string, fn: (e: MessageEvent) => void) {
    this.listeners.set(t, [...(this.listeners.get(t) ?? []), fn]);
  }
  close() {
    this.closed = true;
  }
  emit(t: string, data: unknown) {
    const ev = { data: JSON.stringify(data), lastEventId: "" } as MessageEvent;
    this.listeners.get(t)?.forEach((fn) => fn(ev));
  }
}

const P = "/api/v1/notifications/stream";
const flush = () => act(async () => {});

describe("useSSE sharing", () => {
  beforeEach(() => {
    FakeES.all = [];
    vi.stubGlobal("EventSource", FakeES);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("two subscribers share one EventSource and both get events", async () => {
    const a = vi.fn();
    const b = vi.fn();
    renderHook(() => useSSE(P, { onMessage: a, eventTypes: ["x"] }));
    renderHook(() => useSSE(P, { onMessage: b, eventTypes: ["y"] }));
    await flush();
    expect(FakeES.all).toHaveLength(1);
    FakeES.all[0].emit("x", { n: 1 });
    FakeES.all[0].emit("y", { n: 2 });
    expect(a).toHaveBeenCalledWith({ n: 1 }, "x");
    expect(a).not.toHaveBeenCalledWith({ n: 2 }, "y");
    expect(b).toHaveBeenCalledWith({ n: 2 }, "y");
  });

  it("stays open until the last subscriber unmounts", async () => {
    const h1 = renderHook(() => useSSE(P, { eventTypes: ["x"] }));
    const h2 = renderHook(() => useSSE(P, { eventTypes: ["x"] }));
    await flush();
    h1.unmount();
    expect(FakeES.all[0].closed).toBe(false);
    h2.unmount();
    expect(FakeES.all[0].closed).toBe(true);
  });

  it("reconnects with backoff after an error", async () => {
    vi.useFakeTimers();
    try {
      renderHook(() => useSSE(P, { eventTypes: ["x"] }));
      await act(async () => {});
      act(() => FakeES.all[0].onerror?.(new Event("error")));
      expect(FakeES.all[0].closed).toBe(true);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
      expect(FakeES.all).toHaveLength(2);
    } finally {
      vi.useRealTimers();
    }
  });
});
