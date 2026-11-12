/**
 * @file tests/unit/events/ListView.test.tsx
 * @brief Grouped rendering, ordering, selection and empty state of ListView.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { ListView } from "@/components/events/ListView";
import type { EventItem } from "@/lib/api/events";
import { renderWithProviders } from "../../utils/renderWithProviders";

function mk(id: string, title: string, starts: string, ends: string) {
  return {
    id,
    title,
    starts_at: starts,
    ends_at: ends,
    is_all_day: false,
    visibility: "community",
    subgroup_id: null,
    color: null,
  } as unknown as EventItem;
}

const events = [
  mk("b", "Later", "2026-04-16T12:00:00", "2026-04-16T13:00:00"),
  mk("c", "Evening", "2026-04-15T18:00:00", "2026-04-15T19:00:00"),
  mk("a", "Morning", "2026-04-15T09:00:00", "2026-04-15T10:00:00"),
];

function setup(list: EventItem[], onSelectEvent = vi.fn()) {
  renderWithProviders(
    <ListView
      events={list}
      selectedEventId={null}
      subgroupNames={new Map()}
      onSelectEvent={onSelectEvent}
    />,
  );
  return onSelectEvent;
}

describe("ListView", () => {
  it("shows empty state when there are no events", () => {
    setup([]);
    expect(screen.getByText("No events scheduled")).toBeInTheDocument();
  });

  it("groups events under date headings, sorted by time", () => {
    setup(events);
    const headings = screen.getAllByRole("heading", { level: 3 });
    expect(headings.map((h) => h.textContent)).toEqual([
      "Wednesday, April 15",
      "Thursday, April 16",
    ]);
    const titles = screen.getAllByRole("button").map((b) => b.textContent);
    expect(titles[0]).toContain("Morning");
    expect(titles[1]).toContain("Evening");
    expect(titles[2]).toContain("Later");
  });

  it("calls onSelectEvent with the clicked event", () => {
    const onSelect = setup(events);
    fireEvent.click(screen.getByText("Later"));
    expect(onSelect).toHaveBeenCalledWith(events[0]);
  });
});
