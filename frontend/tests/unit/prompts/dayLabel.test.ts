// @vitest-environment node
/**
 * @file tests/unit/prompts/dayLabel.test.ts
 * @brief dayLabel treats date-only strings as local days (TZ-sensitive).
 */
import { describe, it, expect } from "vitest";
import { dayLabel } from "@/components/prompts/stackPlacement";

describe("dayLabel date-only", () => {
  it("2026-11-23 is Today on 2026-11-23 evening local, any zone", () => {
    const now = new Date(2026, 10, 23, 20, 0); // local evening (UTC may be next day)
    expect(dayLabel("2026-11-23", now)).toBe("Today");
    expect(dayLabel("2026-11-22", now)).toBe("Yesterday");
  });
  it("holds under America/New_York", () => {
    const prev = process.env.TZ;
    process.env.TZ = "America/New_York";
    try {
      const now = new Date(2026, 10, 23, 21, 0);
      expect(dayLabel("2026-11-23", now)).toBe("Today");
    } finally {
      process.env.TZ = prev;
    }
  });
});
