/**
 * @file tests/unit/admin/useAdminAI.test.tsx
 * @brief Tests for admin AI API client functions.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as client from "@/lib/api/client";
import * as ai from "@/lib/api/adminAI";

vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof client>()),
  apiGet: vi.fn().mockResolvedValue({}),
  apiPut: vi.fn().mockResolvedValue({}),
  apiPost: vi.fn().mockResolvedValue({}),
}));

describe("adminAI api", () => {
  beforeEach(() => vi.clearAllMocks());

  it("hits the expected endpoints", async () => {
    await ai.getAIConfig();
    await ai.getAIMetrics();
    await ai.updateAIConfig({ sass_level: 3 });
    await ai.testAIConnection();
    expect(client.apiGet).toHaveBeenCalledWith("/api/v1/admin/ai/config");
    expect(client.apiGet).toHaveBeenCalledWith("/api/v1/admin/ai/metrics");
    expect(client.apiPut).toHaveBeenCalledWith("/api/v1/admin/ai/config", {
      sass_level: 3,
    });
    expect(client.apiPost).toHaveBeenCalledWith(
      "/api/v1/admin/ai/test-connection",
    );
  });
});
