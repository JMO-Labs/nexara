/**
 * @file tests/unit/lib/memories-api.test.ts
 * @brief On-this-day client hits the versioned API path.
 */
import { describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", () => ({ apiGet }));

import { getOnThisDay } from "@/lib/api/memories";

describe("getOnThisDay", () => {
  it("calls /api/v1/memories/on-this-day", () => {
    getOnThisDay();
    expect(apiGet).toHaveBeenCalledWith("/api/v1/memories/on-this-day");
  });
});
