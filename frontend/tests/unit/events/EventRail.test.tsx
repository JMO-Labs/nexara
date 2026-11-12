/**
 * @file tests/unit/events/EventRail.test.tsx
 * @brief Event rail: day grouping, ordering, selection callback, empty states.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventRail } from "@/components/events/EventRail";
import { makeEvent } from "./fixtures";

const later = makeEvent({
  id: "b",
  title: "Concert",
  location: "Hall",
  starts_at: "2026-05-12T19:00:00",
  ends_at: "2026-05-12T21:00:00",
});
const earlier = makeEvent({ id: "a", title: "Picnic" });

function rail(
  events: ReturnType<typeof makeEvent>[],
  selectedDay: Date | null = null,
  onSelect = vi.fn(),
) {
  render(
    <EventRail
      events={events}
      selectedDay={selectedDay}
      selectedEventId={null}
      subgroupNames={new Map()}
      onSelectEvent={onSelect}
    />,
  );
  return onSelect;
}

describe("EventRail", () => {
  it("renders events sorted ascending, grouped by day", () => {
    rail([later, earlier]);
    const titles = screen
      .getAllByRole("button")
      .map((b) => b.textContent ?? "");
    expect(titles[0]).toContain("Picnic");
    expect(titles[1]).toContain("Concert");
    expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(2);
    expect(screen.getByText(/Hall/)).toBeInTheDocument();
  });

  it("selecting a row calls onSelectEvent with the event", async () => {
    const onSelect = rail([earlier]);
    await userEvent.click(screen.getByRole("button", { name: /Picnic/ }));
    expect(onSelect).toHaveBeenCalledWith(earlier);
  });

  it("shows month empty state", () => {
    rail([]);
    expect(screen.getByText("Nothing this month")).toBeInTheDocument();
  });

  it("shows day empty state when a day is selected", () => {
    rail([], new Date(2026, 4, 10));
    expect(screen.getByText("No events on May 10")).toBeInTheDocument();
  });
});
