/**
 * @file tests/unit/events/celebrations.test.tsx
 * @brief Calendar celebrations: mapping to all-day entries and icon titles.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  CELEBRATIONS_CALENDAR_ID,
  celebrationEvents,
  celebrationOf,
} from "@/lib/celebrations";
import { EventTitle } from "@/components/events/EventTitle";
import type { CalendarCelebration } from "@/lib/api/celebrations";

const pet: CalendarCelebration = {
  date: "2026-12-12",
  occasion: "gotcha_day",
  subject_type: "household",
  subject_id: "h1",
  name: "Biscuit",
  is_pet: true,
  link: "/app/household/h1",
};

describe("calendar celebrations", () => {
  it("become all-day entries on the Birthdays calendar", () => {
    const [ev] = celebrationEvents([pet]);
    expect(ev.title).toBe("Biscuit's gotcha day");
    expect(ev.is_all_day).toBe(true);
    expect(ev.calendar_id).toBe(CELEBRATIONS_CALENDAR_ID);
    expect(ev.starts_at.startsWith("2026-12-12")).toBe(true);
    expect(celebrationOf(ev)?.link).toBe("/app/household/h1");
    expect(celebrationOf({ ...ev, id: "real-event" })).toBeNull();
  });

  it("titles carry an icon only for celebrations", () => {
    const [ev] = celebrationEvents([
      { ...pet, occasion: "birthday", is_pet: false, name: "Ruth" },
    ]);
    const { container, rerender } = render(<EventTitle ev={ev} />);
    expect(screen.getByText("Ruth's birthday")).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeNull();
    rerender(<EventTitle ev={{ ...ev, id: "e1", title: "Picnic" }} />);
    expect(container.querySelector("svg")).toBeNull();
  });
});
