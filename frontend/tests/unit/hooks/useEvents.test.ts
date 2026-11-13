/**
 * @file tests/unit/hooks/useEvents.test.ts
 * @brief Asserts useRsvp optimistic update, rollback and invalidation.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";

const qcHolder: { qc: unknown } = { qc: {} };
const spy = vi.fn((opts: unknown) => opts);
vi.mock("@/hooks/useMutationWithToast", () => ({
  useMutationWithToast: (opts: unknown) => spy(opts),
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => qcHolder.qc,
}));

import { useRsvp } from "@/hooks/useEvents";

type Opts = {
  onMutate: (s: string | null) => Promise<unknown>;
  onError: (e: Error, s: string | null, ctx: unknown) => void;
  onSettled: () => void;
};
const ev = () => ({ id: "e1", user_rsvp: { status: "no" } });
const listKey = qk.events.list({});

describe("useRsvp optimistic", () => {
  let qc: QueryClient;
  beforeEach(() => {
    spy.mockClear();
    qc = new QueryClient();
    qcHolder.qc = qc;
    qc.setQueryData(qk.events.detail("e1"), ev());
    qc.setQueryData(listKey, { items: [ev()] });
  });
  const opts = () => {
    renderHook(() => useRsvp("e1"));
    return spy.mock.results.at(-1)!.value as Opts;
  };
  const status = () =>
    (qc.getQueryData(qk.events.detail("e1")) as ReturnType<typeof ev>)
      .user_rsvp?.status;
  const listStatus = () =>
    (qc.getQueryData(listKey) as { items: ReturnType<typeof ev>[] }).items[0]
      .user_rsvp?.status;

  it("updates detail and list immediately", async () => {
    await opts().onMutate("yes");
    expect(status()).toBe("yes");
    expect(listStatus()).toBe("yes");
  });
  it("rolls back detail and list on error", async () => {
    const o = opts();
    const ctx = await o.onMutate("yes");
    o.onError(new Error("x"), "yes", ctx);
    expect(status()).toBe("no");
    expect(listStatus()).toBe("no");
  });
  it("invalidates on settled", () => {
    const inv = vi.spyOn(qc, "invalidateQueries");
    opts().onSettled();
    expect(inv).toHaveBeenCalledWith({ queryKey: qk.events.all() });
  });
});
