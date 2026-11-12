/**
 * @file tests/unit/admin/interestsApi.test.ts
 * @brief Tests for interests admin API functions.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as client from "@/lib/api/client";
import { getInterestAnalytics } from "@/lib/api/interests";

// Automock the transport but keep the real seg() path encoder.
vi.mock("@/lib/api/client", async (orig) => {
  const real = await orig<typeof import("@/lib/api/client")>();
  const mocked = Object.fromEntries(
    Object.entries(real).map(([k, v]) => [
      k,
      typeof v === "function" ? vi.fn() : v,
    ]),
  );
  return { ...mocked, seg: real.seg };
});

describe("interestsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getInterestAnalytics", () => {
    it("should call apiGet with correct path", async () => {
      const mockAnalytics = [
        { category_slug: "hobby", value: "cooking", count: 15 },
        { category_slug: "hobby", value: "photography", count: 12 },
        { category_slug: "sport", value: "soccer", count: 8 },
      ];
      vi.mocked(client.apiGet).mockResolvedValue(mockAnalytics);

      const result = await getInterestAnalytics();

      expect(client.apiGet).toHaveBeenCalledWith(
        "/api/v1/interests/admin/interests/analytics",
      );
      expect(result).toEqual(mockAnalytics);
    });
  });
});
