/**
 * @file tests/unit/lib/galleries-bulk.test.ts
 * @brief bulkAddItems posts media_ids to /items/bulk.
 */
import { describe, it, expect, vi } from "vitest";
import { apiPost } from "@/lib/api/client";
import { bulkAddItems } from "@/lib/api/galleries";

vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiPost: vi.fn().mockResolvedValue([]),
}));

describe("bulkAddItems", () => {
  it("POSTs media_ids to the bulk endpoint", async () => {
    await bulkAddItems("g1", ["m1", "m2"]);
    expect(apiPost).toHaveBeenCalledWith("/api/v1/galleries/g1/items/bulk", {
      media_ids: ["m1", "m2"],
    });
  });
});
