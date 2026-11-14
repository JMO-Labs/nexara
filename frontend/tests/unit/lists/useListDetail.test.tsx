/**
 * @file tests/unit/lists/useListDetail.test.tsx
 * @brief Single-list and template detail/create/update hooks.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({ getList: vi.fn() }));
const tpl = vi.hoisted(() => ({
  getTemplate: vi.fn(),
  createTemplate: vi.fn(),
  updateTemplate: vi.fn(),
}));
vi.mock("@/lib/api/lists", () => ({ listApi: api }));
vi.mock("@/lib/api/listTemplates", () => ({ templateApi: tpl }));

import {
  useList,
  useListTemplate,
  useListTemplateCreate,
  useListTemplateUpdate,
} from "@/hooks/useListDetail";

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { qc, spy, wrapper };
}

beforeEach(() => vi.clearAllMocks());

describe("useListDetail hooks", () => {
  it("useList fetches by id under the detail key", async () => {
    api.getList.mockResolvedValue({ id: "l1" });
    const { qc, wrapper } = setup();
    const { result } = renderHook(() => useList("c1", "l1"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getList).toHaveBeenCalledWith("l1");
    expect(qc.getQueryData(["lists", "c1", "detail", "l1"])).toEqual({
      id: "l1",
    });
  });

  it("useList is disabled without an id", () => {
    const { wrapper } = setup();
    renderHook(() => useList("c1", undefined), { wrapper });
    expect(api.getList).not.toHaveBeenCalled();
  });

  it("useListTemplate fetches a template", async () => {
    tpl.getTemplate.mockResolvedValue({ id: "t1" });
    const { wrapper } = setup();
    const { result } = renderHook(() => useListTemplate("t1"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(tpl.getTemplate).toHaveBeenCalledWith("t1");
  });

  it("useListTemplate is disabled without an id", () => {
    const { wrapper } = setup();
    renderHook(() => useListTemplate(undefined), { wrapper });
    expect(tpl.getTemplate).not.toHaveBeenCalled();
  });

  it("create and update invalidate templates", async () => {
    tpl.createTemplate.mockResolvedValue({ id: "t2" });
    tpl.updateTemplate.mockResolvedValue({ id: "t1" });
    const { spy, wrapper } = setup();
    const c = renderHook(() => useListTemplateCreate(), { wrapper });
    const u = renderHook(() => useListTemplateUpdate(), { wrapper });
    await act(() => c.result.current.mutateAsync({ name: "A" }));
    await act(() =>
      u.result.current.mutateAsync({ id: "t1", data: { name: "B" } }),
    );
    expect(tpl.createTemplate).toHaveBeenCalledWith({ name: "A" });
    expect(tpl.updateTemplate).toHaveBeenCalledWith("t1", { name: "B" });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["listTemplates"] });
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
