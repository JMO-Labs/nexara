/**
 * @file tests/unit/lists/useListActions.test.tsx
 * @brief Archive, item update/delete and member hooks: calls + invalidation.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  archiveList: vi.fn(),
  updateItem: vi.fn(),
  deleteItem: vi.fn(),
  getMembers: vi.fn(),
  addMember: vi.fn(),
  removeMember: vi.fn(),
}));
vi.mock("@/lib/api/lists", () => ({ listApi: api }));

import {
  useListArchive,
  useListItemUpdate,
  useListItemDelete,
  useListMembers,
  useListMemberAdd,
  useListMemberRemove,
} from "@/hooks/useListActions";

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { spy, wrapper };
}

beforeEach(() => Object.values(api).forEach((f) => f.mockReset()));

describe("list action hooks", () => {
  it("archive invalidates the community lists", async () => {
    const { spy, wrapper } = setup();
    api.archiveList.mockResolvedValue({});
    const { result } = renderHook(() => useListArchive("c1"), { wrapper });
    await act(() => result.current.mutateAsync("l1"));
    expect(api.archiveList).toHaveBeenCalledWith("l1");
    expect(spy).toHaveBeenCalledWith({ queryKey: ["lists", "c1"] });
  });

  it("item update/delete invalidate list items", async () => {
    const { spy, wrapper } = setup();
    api.updateItem.mockResolvedValue({});
    api.deleteItem.mockResolvedValue(undefined);
    const up = renderHook(() => useListItemUpdate("l1"), { wrapper });
    await act(() =>
      up.result.current.mutateAsync({ itemId: "i1", values: { a: 1 } }),
    );
    expect(api.updateItem).toHaveBeenCalledWith("l1", "i1", {
      values: { a: 1 },
    });
    const del = renderHook(() => useListItemDelete("l1"), { wrapper });
    await act(() => del.result.current.mutateAsync("i1"));
    expect(api.deleteItem).toHaveBeenCalledWith("l1", "i1");
    expect(spy).toHaveBeenCalledWith({ queryKey: ["listItems", "l1"] });
  });

  it("members query and mutations", async () => {
    const { spy, wrapper } = setup();
    api.getMembers.mockResolvedValue([{ userId: "u" }]);
    api.addMember.mockResolvedValue({});
    api.removeMember.mockResolvedValue(undefined);
    const q = renderHook(() => useListMembers("l1"), { wrapper });
    await waitFor(() => expect(q.result.current.data).toHaveLength(1));
    const add = renderHook(() => useListMemberAdd("l1"), { wrapper });
    await act(() => add.result.current.mutateAsync({ userId: "u2" }));
    expect(api.addMember).toHaveBeenCalledWith("l1", { userId: "u2" });
    const rm = renderHook(() => useListMemberRemove("l1"), { wrapper });
    await act(() => rm.result.current.mutateAsync("u2"));
    expect(api.removeMember).toHaveBeenCalledWith("l1", "u2");
    expect(spy).toHaveBeenCalledWith({ queryKey: ["listMembers", "l1"] });
  });
});
