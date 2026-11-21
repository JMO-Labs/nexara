/**
 * @file tests/unit/components/events/calendarNav.test.ts
 * @brief periodTitle: friendly toolbar title for each calendar view.
 */
import { describe, it, expect } from "vitest";
import { periodTitle } from "@/components/events/events-page/calendarNav";

describe("periodTitle", () => {
  const month = new Date(2026, 10, 1);
  const weekStart = new Date(2026, 10, 15);
  const day = new Date(2026, 10, 21);

  it("month view shows the month and year", () => {
    expect(periodTitle("month", month, weekStart, day)).toBe("November 2026");
    expect(periodTitle("list", month, weekStart, day)).toBe("November 2026");
  });

  it("week view shows the Sunday to Saturday range", () => {
    expect(periodTitle("week", month, weekStart, day)).toBe("Nov 15 – Nov 21");
  });

  it("day view shows the weekday and date", () => {
    expect(periodTitle("day", month, weekStart, day)).toBe("Saturday, Nov 21");
  });

  it("day view without a selected day falls back to the month", () => {
    expect(periodTitle("day", month, weekStart, null)).toBe("November 2026");
  });
});
