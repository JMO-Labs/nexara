/**
 * @file tests/unit/components/events/EventsSidePanel.test.tsx
 * @brief Side panel: "Up next" rail plus the selected-day list; no mini month.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventsSidePanel } from "@/components/events/events-page/EventsSidePanel";

const picnic: any = {
  id: "1",
  title: "Picnic",
  starts_at: "2025-01-10T12:00:00",
  ends_at: "2025-01-10T13:00:00",
};
const concert: any = {
  id: "2",
  title: "Concert",
  starts_at: "2025-01-12T19:00:00",
  ends_at: "2025-01-12T21:00:00",
};

function setup(over: Record<string, unknown> = {}) {
  const props = {
    upcoming: [picnic, concert],
    railEvents: [picnic],
    selectedDay: new Date(2025, 0, 10),
    selectedEventId: null,
    subgroupNames: new Map<string, string>(),
    onSelectEvent: vi.fn(),
    onClearDay: vi.fn(),
    ...over,
  };
  render(<EventsSidePanel {...(props as any)} />);
  return props;
}

describe("EventsSidePanel", () => {
  it("has an Up next panel listing upcoming events", async () => {
    const p = setup();
    expect(
      screen.getByRole("heading", { name: "Up next", level: 2 }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Concert/ }));
    expect(p.onSelectEvent).toHaveBeenCalledWith(concert);
  });

  it("has no mini month or countdown", () => {
    setup();
    expect(screen.queryByRole("button", { name: /next month/i })).toBeNull();
    expect(screen.queryByText("January 2025")).toBeNull();
  });

  it("titles the day panel with the selected day and can clear it", async () => {
    const p = setup();
    expect(
      screen.getByRole("heading", { name: "Fri, Jan 10", level: 2 }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(p.onClearDay).toHaveBeenCalled();
  });

  it("falls back to This month when no day is selected", () => {
    setup({ selectedDay: null });
    expect(
      screen.getByRole("heading", { name: "This month", level: 2 }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });

  it("Clear is a glass pill", () => {
    setup();
    expect(screen.getByRole("button", { name: "Clear" }).className).toContain(
      "glass-btn",
    );
  });

  it("hides the selected-day panel in list view", () => {
    setup({ showDayPanel: false });
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "Fri, Jan 10", level: 2 }),
    ).toBeNull();
  });

  it("empty day offers a New event pill wired to onCreate", async () => {
    const onCreate = vi.fn();
    setup({ railEvents: [], onCreate });
    await userEvent.click(screen.getByRole("button", { name: "New event" }));
    expect(onCreate).toHaveBeenCalled();
  });

  it("shows an empty line when nothing is upcoming", () => {
    setup({ upcoming: [] });
    expect(screen.getByText("Nothing coming up")).toBeInTheDocument();
  });
});
