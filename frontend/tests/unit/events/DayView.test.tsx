/**
 * @file tests/unit/events/DayView.test.tsx
 * @brief Day view: timed events, all-day strip, other-day and empty cases.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DayView } from "@/components/events/DayView";
import { makeEvent } from "./fixtures";

const day = new Date(2026, 4, 10);

function view(events: ReturnType<typeof makeEvent>[], onSelect = vi.fn()) {
  render(
    <DayView
      day={day}
      events={events}
      selectedEventId={null}
      subgroupNames={new Map()}
      onSelectEvent={onSelect}
    />,
  );
  return onSelect;
}

describe("DayView", () => {
  it("renders header and a timed event for the day", async () => {
    const ev = makeEvent();
    const onSelect = view([ev]);
    expect(screen.getByText("Sunday")).toBeInTheDocument();
    expect(screen.getByText("May 10, 2026")).toBeInTheDocument();
    const block = screen.getByRole("button", { name: /Picnic/ });
    await userEvent.click(block);
    expect(onSelect).toHaveBeenCalledWith(ev);
  });

  it("shows all-day events in the all-day strip", () => {
    view([
      makeEvent({
        id: "e2",
        title: "Holiday",
        is_all_day: true,
        starts_at: "2026-05-10T00:00:00",
        ends_at: "2026-05-10T23:59:59",
      }),
    ]);
    expect(screen.getByText("All day")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Holiday" })).toBeInTheDocument();
  });

  it("empty state: no events, no all-day strip, other-day ignored", () => {
    view([
      makeEvent({
        title: "Elsewhere",
        starts_at: "2026-05-12T10:00:00",
        ends_at: "2026-05-12T11:00:00",
      }),
    ]);
    expect(screen.queryByText("Elsewhere")).not.toBeInTheDocument();
    expect(screen.queryByText("All day")).not.toBeInTheDocument();
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});
