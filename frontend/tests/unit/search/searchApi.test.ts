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

  it("searchAll flattens galleries and polls buckets", async () => {
    const item = (id: string) => ({
      id,
      title: id,
      snippet: "",
      created_at: "2026-01-01T00:00:00Z",
    });
    (apiGet as ReturnType<typeof vi.fn>).mockResolvedValue({
      query: "x",
      results: {
        galleries: { items: [item("g1")], total: 3, next_cursor: null },
        polls: {
          items: [item("p1"), item("p2")],
          total: 2,
          next_cursor: null,
        },
      },
    });

    const res = await searchAll("x");

    expect(res.items.map((i) => [i.id, i.type])).toEqual([
      ["g1", "galleries"],
      ["p1", "polls"],
      ["p2", "polls"],
    ]);
    expect(res.totals).toEqual({ galleries: 3, polls: 2 });
  });
});
