/**
 * @file tests/unit/stores/toasts.test.ts
 * @brief Toast store: ttl defaults, visible cap, update merge.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useToasts, selectVisible } from "@/stores/toasts";

beforeEach(() => useToasts.getState().clear());

describe("toasts store", () => {
  it("caps visible toasts at 3 while queueing the rest", () => {
    for (let i = 0; i < 5; i++) {
      useToasts.getState().push({ variant: "info", message: `m${i}` });
    }
    const { items } = useToasts.getState();
    expect(items).toHaveLength(5);
    expect(selectVisible(items).map((t) => t.message)).toEqual([
      "m0",
      "m1",
      "m2",
    ]);
  });

  it("loading persists, others use default ttl", () => {
    const s = useToasts.getState();
    const l = s.push({ variant: "loading", message: "up" });
    const e = s.push({ variant: "danger", message: "x" });
    const get = (id: string) =>
      useToasts.getState().items.find((t) => t.id === id)!;
    expect(get(l).ttl).toBeNull();
    expect(get(e).ttl).toBe(6000);
  });

  it("update merges and gives loading->success a ttl", () => {
    const id = useToasts
      .getState()
      .push({ variant: "loading", message: "Uploading" });
    useToasts
      .getState()
      .update(id, { variant: "success", message: "Upload complete" });
    const t = useToasts.getState().items[0];
    expect(t.message).toBe("Upload complete");
    expect(t.variant).toBe("success");
    expect(t.ttl).toBe(4000);
  });

  it("update respects explicit ttl", () => {
    const id = useToasts.getState().push({ variant: "loading", message: "a" });
    useToasts.getState().update(id, { variant: "success", ttl: 100 });
    expect(useToasts.getState().items[0].ttl).toBe(100);
  });
});

describe("toasts dedupe + priority", () => {
  afterEach(() => vi.useRealTimers());

  it("returns the existing id for same dedupeKey within 5s", () => {
    const s = useToasts.getState();
    const a = s.push({ variant: "info", message: "a", dedupeKey: "k" });
    const b = s.push({ variant: "info", message: "b", dedupeKey: "k" });
    expect(b).toBe(a);
    expect(useToasts.getState().items).toHaveLength(1);
  });

  it("allows the same dedupeKey after the 5s window", () => {
    vi.useFakeTimers();
    const s = useToasts.getState();
    const a = s.push({ variant: "info", message: "a", dedupeKey: "k" });
    vi.advanceTimersByTime(5001);
    const b = s.push({ variant: "info", message: "b", dedupeKey: "k" });
    expect(b).not.toBe(a);
    expect(useToasts.getState().items).toHaveLength(2);
  });

  it("sorts by priority desc, stable for ties", () => {
    const s = useToasts.getState();
    s.push({ variant: "info", message: "low" });
    s.push({ variant: "info", message: "high", priority: 5 });
    s.push({ variant: "info", message: "low2" });
    expect(useToasts.getState().items.map((t) => t.message)).toEqual([
      "high",
      "low",
      "low2",
    ]);
  });
});
