/**
 * @file tests/unit/lib/galleries-api.test.ts
 * @brief bulkAddItems posts media_ids to /items/bulk.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { bulkAddItems } from "@/lib/api/galleries";

describe("bulkAddItems", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("POSTs media_ids to /galleries/{id}/items/bulk", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("[]", {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await bulkAddItems("g1", ["m1", "m2"]);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/galleries\/g1\/items\/bulk$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ media_ids: ["m1", "m2"] });
  });
});
