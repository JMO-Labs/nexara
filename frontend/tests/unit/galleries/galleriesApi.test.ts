/**
 * @file tests/unit/galleries/galleriesApi.test.ts
 * @brief bulkAddItems posts media_ids to the bulk endpoint.
 */
import { describe, it, expect, vi } from "vitest";
import * as client from "@/lib/api/client";
import { bulkAddItems } from "@/lib/api/galleries";

vi.mock("@/lib/api/client", async (orig) => {
  const real = await orig<typeof import("@/lib/api/client")>();
  return { ...real, apiPost: vi.fn() };
});

describe("bulkAddItems", () => {
  it("POSTs media_ids to /items/bulk", async () => {
    vi.mocked(client.apiPost).mockResolvedValue([]);
    await bulkAddItems("g1", ["a", "b"]);
    expect(client.apiPost).toHaveBeenCalledWith(
      "/api/v1/galleries/g1/items/bulk",
      { media_ids: ["a", "b"] },
    );
  });
});
