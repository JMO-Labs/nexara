/**
 * @file tests/unit/calendar/CalendarSubscriptions.test.tsx
 * @brief Export-as-iCal button and next-sync display.
 */
import * as React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExportIcalButton } from "@/components/events/event-detail/ExportIcalButton";

describe("ExportIcalButton", () => {
  it("links to the event .ics endpoint as a download", () => {
    render(<ExportIcalButton eventId="ev 1" />);
    const link = screen.getByRole("link", { name: /export as ical/i });
    expect(link.getAttribute("href")).toBe("/api/v1/events/ev%201/ical");
    expect(link.hasAttribute("download")).toBe(true);
  });
});
