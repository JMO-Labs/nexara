/**
 * @file tests/unit/hooks/useSubgroupMedia.test.tsx
 * @brief Unit tests for useSubgroupMedia (success, empty, error, paging).
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { waitFor } from "@testing-library/react";

import { renderHookWithProviders } from "../../utils/renderWithProviders";
import { useSubgroupMedia } from "@/hooks/useSubgroupMedia";
import { getSubgroupMedia } from "@/lib/api/subgroups";

vi.mock("@/lib/api/subgroups", () => ({ getSubgroupMedia: vi.fn() }));

const item = (id: string) => ({ id, filename: `${id}.jpg` }) as never;

describe("useSubgroupMedia", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns media pages on success with default params", async () => {
    vi.mocked(getSubgroupMedia).mockResolvedValue({
      items: [item("a"), item("b")],
      next_cursor: null,
    });
    const { result } = renderHookWithProviders(() =>
      useSubgroupMedia({ slug: "fam" }),
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.pages[0].items).toHaveLength(2);
    expect(result.current.hasNextPage).toBe(false);
    expect(getSubgroupMedia).toHaveBeenCalledWith("fam", {
      source: "all",
      limit: 60,
      cursor: null,
    });
  });

  it("handles an empty result", async () => {
    vi.mocked(getSubgroupMedia).mockResolvedValue({
      items: [],
      next_cursor: null,
    });
    const { result } = renderHookWithProviders(() =>
      useSubgroupMedia({ slug: "fam" }),
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.pages[0].items).toEqual([]);
    expect(result.current.hasNextPage).toBe(false);
  });

  it("surfaces errors", async () => {
    vi.mocked(getSubgroupMedia).mockRejectedValue(new Error("nope"));
    const { result } = renderHookWithProviders(() =>
      useSubgroupMedia({ slug: "fam" }),
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("nope");
  });

  it("fetches the next page using next_cursor and passes source/limit", async () => {
    vi.mocked(getSubgroupMedia)
      .mockResolvedValueOnce({ items: [item("a")], next_cursor: "c1" })
      .mockResolvedValueOnce({ items: [item("b")], next_cursor: null });
    const { result } = renderHookWithProviders(() =>
      useSubgroupMedia({ slug: "fam", source: "post", limit: 1 }),
    );

    await waitFor(() => expect(result.current.hasNextPage).toBe(true));
    await result.current.fetchNextPage();
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2));

    expect(getSubgroupMedia).toHaveBeenLastCalledWith("fam", {
      source: "post",
      limit: 1,
      cursor: "c1",
    });
  });

  it("does not fetch when disabled", () => {
    renderHookWithProviders(() =>
      useSubgroupMedia({ slug: "fam", enabled: false }),
    );
    expect(getSubgroupMedia).not.toHaveBeenCalled();
  });
});
