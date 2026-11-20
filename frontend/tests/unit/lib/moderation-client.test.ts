/**
 * @file tests/unit/lib/moderation-client.test.ts
 * @brief Moderation API client targets /api/v1 endpoints.
 */
import { describe, it, expect, vi } from "vitest";
import * as client from "@/lib/api/client";
import * as mod from "@/lib/api/moderation";

describe("moderation client", () => {
  it("uses /api/v1-prefixed paths", async () => {
    const get = vi.spyOn(client, "apiGet").mockResolvedValue({} as never);
    const post = vi.spyOn(client, "apiPost").mockResolvedValue({} as never);
    const del = vi.spyOn(client, "apiDelete").mockResolvedValue({} as never);
    await mod.listReports("pending");
    await mod.reportAction("r 1", "dismiss");
    await mod.createReport({
      target_type: "post",
      target_id: "p1",
      reason: "spam",
    } as never);
    await mod.blockUser("u 1");
    await mod.unblockUser("u 1");
    expect(get.mock.calls[0][0]).toBe(
      "/api/v1/admin/moderation/reports?status=pending",
    );
    expect(post.mock.calls.map((c) => c[0])).toEqual([
      "/api/v1/admin/moderation/reports/r%201/action",
      "/api/v1/moderation/reports",
      "/api/v1/users/u%201/block",
    ]);
    expect(del.mock.calls[0][0]).toBe("/api/v1/users/u%201/block");
  });
});
