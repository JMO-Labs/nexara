/**
 * @file tests/unit/stores/toasts.test.ts
 * @brief Toast store: ttl defaults, visible cap, update merge.
 */
import { beforeEach, describe, expect, it } from "vitest";
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
