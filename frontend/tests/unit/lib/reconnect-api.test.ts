/**
 * @file tests/unit/lib/reconnect-api.test.ts
 * @brief Reconnect client hits the versioned API path.
 */
import { describe, expect, it, vi } from "vitest";

const m = vi.hoisted(() => ({ apiPost: vi.fn() }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  ...m,
}));

import { snoozeReconnect } from "@/lib/api/reconnect";

describe("reconnect api paths", () => {
  it("snooze posts to /api/v1/reconnect/snooze with target_id", () => {
    snoozeReconnect("u1");
    expect(m.apiPost).toHaveBeenCalledWith("/api/v1/reconnect/snooze", {
      target_id: "u1",
    });
    expect(m.apiPost.mock.calls[0][0]).toMatch(/^\/api\/v1\//);
  });
});
