/**
 * @file tests/unit/lists/useLists.test.tsx
 * @brief Hooks: infinite pagination, queryKeys, invalidation on mutations.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  getLists: vi.fn(),
  createList: vi.fn(),
  updateList: vi.fn(),
  deleteList: vi.fn(),
  listItems: vi.fn(),
  createItem: vi.fn(),
  completeItem: vi.fn(),
  claimSignup: vi.fn(),
}));
const tpl = vi.hoisted(() => ({
  getTemplates: vi.fn(),
  cloneTemplate: vi.fn(),
}));
vi.mock("@/lib/api/lists", () => ({ listApi: api }));
vi.mock("@/lib/api/listTemplates", () => ({ templateApi: tpl }));

import {
  useLists,
  useListItems,
  useListCreate,
  useListUpdate,
  useListDelete,
  useListItemCreate,
  useListItemComplete,
  useListSignupClaim,
  useListTemplates,
  useListTemplateClone,
} from "@/hooks/useLists";

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { qc, spy, wrapper };
}

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  Object.values(tpl).forEach((f) => f.mockReset());
});

describe("queries", () => {
  it("useLists is keyed by community and gated on it", async () => {
    const { qc, wrapper } = setup();
    api.getLists.mockResolvedValue({ lists: [], nextCursor: undefined });
    const { result } = renderHook(() => useLists("c1"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(
      qc.getQueryData(["lists", "c1", "list", { limit: 20 }]),
    ).toBeDefined();
    const off = renderHook(() => useLists(undefined), { wrapper });
    expect(off.result.current.fetchStatus).toBe("idle");
  });

  it("useListItems paginates with cursor", async () => {
    const { wrapper } = setup();
    api.listItems
      .mockResolvedValueOnce({ items: [{ id: "a" }], nextCursor: "n1" })
      .mockResolvedValueOnce({ items: [{ id: "b" }], nextCursor: undefined });
    const { result } = renderHook(() => useListItems("l1"), { wrapper });
    await waitFor(() => expect(result.current.hasNextPage).toBe(true));
    expect(api.listItems.mock.calls[0][1]).toMatchObject({ cursor: undefined });
    await act(async () => {
      await result.current.fetchNextPage();
    });
    expect(api.listItems.mock.calls[1][1]).toMatchObject({ cursor: "n1" });
    await waitFor(() => expect(result.current.hasNextPage).toBe(false));
    expect(result.current.isFetchingNextPage).toBe(false);
  });

  it("useListTemplates fetches", async () => {
    const { wrapper } = setup();
    tpl.getTemplates.mockResolvedValue({ templates: [] });
    const { result } = renderHook(() => useListTemplates(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("mutations invalidate", () => {
  it.each([
    ["create", () => useListCreate("c1"), api.createList, [{ title: "x" }]],
    [
      "update",
      () => useListUpdate("c1"),
      api.updateList,
      [{ id: "l1", data: {} }],
    ],
    ["delete", () => useListDelete("c1"), api.deleteList, ["l1"]],
  ] as const)("list %s", async (_n, hook, fn, args) => {
    const { wrapper, spy } = setup();
    fn.mockResolvedValue({});
    const { result } = renderHook(hook, { wrapper });
    await act(async () => {
      await (result.current.mutateAsync as (a: unknown) => Promise<unknown>)(
        args[0],
      );
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["lists", "c1"] });
  });

  it("item create invalidates listItems", async () => {
    const { wrapper, spy } = setup();
    api.createItem.mockResolvedValue({});
    const { result } = renderHook(() => useListItemCreate("l1"), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ position: 0, values: {} });
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["listItems", "l1"] });
  });

  it("complete and claim invalidate listItems", async () => {
    const { wrapper, spy } = setup();
    api.completeItem.mockResolvedValue({});
    api.claimSignup.mockResolvedValue({});
    const c = renderHook(() => useListItemComplete("l1"), { wrapper });
    await act(async () => {
      await c.result.current.mutateAsync({ itemId: "i1", completed: true });
    });
    expect(api.completeItem).toHaveBeenCalledWith("l1", "i1");
    const s = renderHook(() => useListSignupClaim("l1"), { wrapper });
    await act(async () => {
      await s.result.current.mutateAsync({ itemId: "i1", quantity: 1 });
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["listItems", "l1"] });
  });

  it("template clone invalidates lists", async () => {
    const { wrapper, spy } = setup();
    tpl.cloneTemplate.mockResolvedValue({});
    const { result } = renderHook(() => useListTemplateClone("c1"), {
      wrapper,
    });
    await act(async () => {
      await result.current.mutateAsync({ id: "t1", options: {} });
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["lists", "c1"] });
  });

  it("errors surface in error state", async () => {
    const { wrapper } = setup();
    api.createList.mockRejectedValue(new Error("Forbidden"));
    const { result } = renderHook(() => useListCreate("c1"), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ title: "x" }).catch(() => undefined);
    });
    await waitFor(() =>
      expect(result.current.error?.message).toBe("Forbidden"),
    );
  });
});
