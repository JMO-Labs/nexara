/**
 * @file tests/unit/search/searchApi.test.ts
 * @brief Verify search API client URL building and types.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchAll } from "@/lib/api/search";

vi.mock("@/lib/api/client", () => ({
  apiGet: vi.fn(),
}));

import { apiGet } from "@/lib/api/client";

describe("search API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("searchAll builds correct URL with query and types", async () => {
    (apiGet as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    });

    await searchAll("test query", { types: ["posts", "users"] });

    const url = (apiGet as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(url).toContain("q=test");
    expect(url).toContain("types=posts%2Cusers");
  });

  it("searchAll URL-encodes query", async () => {
    (apiGet as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    });

    await searchAll("hello & goodbye", {});

    const url = (apiGet as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(url).toContain("q=hello");
    expect(url).toContain("%26");
  });

  it("searchAll omits cursor if null or undefined", async () => {
    (apiGet as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    });

    await searchAll("test", { cursor: null });

    const call = (apiGet as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(call).not.toContain("cursor=");
  });

  it("searchAll includes cursor if provided", async () => {
    (apiGet as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    });

    await searchAll("test", { cursor: "abc123" });

    const url = (apiGet as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(url).toContain("cursor=abc123");
  });

  it("searchAll uses limit parameter", async () => {
    (apiGet as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    });

    await searchAll("test", { limit: 50 });

    const url = (apiGet as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(url).toContain("limit=50");
  });
});

describe("searchAll galleries and polls", () => {
  it("flattens galleries and polls buckets", async () => {
    (apiGet as ReturnType<typeof vi.fn>).mockResolvedValue({
      query: "x",
      results: {
        galleries: {
          items: [{ id: "g1", title: "G", snippet: "", created_at: "t" }],
          total: 3,
          next_cursor: null,
        },
        polls: {
          items: [
            {
              id: "pl1",
              title: "P",
              snippet: "",
              created_at: "t",
              parent_id: "p1",
            },
          ],
          total: 2,
          next_cursor: null,
        },
      },
    });

    const res = await searchAll("x");

    expect(res.items.map((i) => i.type)).toEqual(["galleries", "polls"]);
    expect(res.items[1].parent_id).toBe("p1");
    expect(res.totals).toEqual({ galleries: 3, polls: 2 });
  });
});
