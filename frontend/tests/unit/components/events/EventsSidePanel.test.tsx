/**
 * @file tests/unit/components/events/EventsSidePanel.test.tsx
 * @brief Side panel hosts the mini calendar driven by page month state.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventsSidePanel } from "@/components/events/events-page/EventsSidePanel";

vi.mock("@/components/events/EventRail", () => ({ EventRail: () => <div /> }));
vi.mock("@/components/events/EventCountdown", () => ({
  EventCountdown: () => <div />,
}));

const picnic: any = {
  id: "1",
  title: "Picnic",
  starts_at: "2025-01-10T12:00:00",
  ends_at: "2025-01-10T13:00:00",
};

function setup() {
  const props = {
    nextEvent: null,
    events: [picnic],
    railEvents: [],
    month: new Date(2025, 0, 1),
    onMonthChange: vi.fn(),
    selectedDay: null,
    selectedEventId: null,
    subgroupNames: new Map<string, string>(),
    onSelectEvent: vi.fn(),
    onClearDay: vi.fn(),
  };
  render(<EventsSidePanel {...props} />);
  return props;
}

describe("EventsSidePanel calendar", () => {
  it("shows the page month and day click expands that day inline", async () => {
    const p = setup();
    expect(screen.getByText("January 2025")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /January 10/ }));
    await userEvent.click(screen.getByRole("button", { name: "Picnic" }));
    expect(p.onSelectEvent).toHaveBeenCalledWith(picnic);
  });

  it("prev/next month buttons drive onMonthChange", async () => {
    const p = setup();
    await userEvent.click(screen.getByRole("button", { name: /next month/i }));
    expect(p.onMonthChange).toHaveBeenCalledWith(new Date(2025, 1, 1));
  });
});
