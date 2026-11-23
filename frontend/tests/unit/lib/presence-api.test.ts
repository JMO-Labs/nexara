/**
 * @file tests/unit/lib/presence-api.test.ts
 * @brief Presence client hits the /api/v1 path with the id list.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

const apiPost = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiPost: (...a: unknown[]) => apiPost(...a),
}));

import { fetchPresence } from "@/lib/api/presence";

describe("fetchPresence", () => {
  beforeEach(() => apiPost.mockReset());
  it("posts to /api/v1/presence", async () => {
    apiPost.mockResolvedValue({ online: [], last_seen: {} });
    await fetchPresence(["a"]);
    expect(apiPost).toHaveBeenCalledWith("/api/v1/presence", {
      user_ids: ["a"],
    });
  });
});
