/**
 * @file tests/unit/events/CalendarFilterBar.test.tsx
 * @brief Filter bar: month nav, create action and calendar toggling.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CalendarFilterBar } from "@/components/events/CalendarFilterBar";
import type { Calendar } from "@/lib/api/calendars";
import { renderWithProviders } from "../../utils/renderWithProviders";

const cal = (over: Partial<Calendar>): Calendar => ({
  id: "c1",
  kind: "community",
  name: "Town Hall",
  color: "#112233",
  owner_id: null,
  subgroup_id: null,
  external_provider: null,
  external_id: null,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

const calendars = [
  cal({}),
  cal({ id: "c2", kind: "personal", name: "Mine", color: "#445566" }),
];

function setup() {
  const props = {
    month: new Date(2026, 4, 15),
    onMonthChange: vi.fn(),
    selected: ["c1"],
    onSelectedChange: vi.fn(),
    calendars,
    onCreate: vi.fn(),
  };
  renderWithProviders(<CalendarFilterBar {...props} />);
  return props;
}

describe("CalendarFilterBar", () => {
  it("renders month title and filter trigger", () => {
    setup();
    expect(screen.getByText("May")).toBeInTheDocument();
    expect(screen.getByText("Calendar, 2026")).toBeInTheDocument();
    expect(screen.getByText("Calendars")).toBeInTheDocument();
  });

  it("navigates months and fires create", async () => {
    const p = setup();
    await userEvent.click(screen.getByLabelText("Previous month"));
    expect(p.onMonthChange.mock.calls[0][0].getMonth()).toBe(3);
    await userEvent.click(screen.getByLabelText("Next month"));
    expect(p.onMonthChange.mock.calls[1][0].getMonth()).toBe(5);
    await userEvent.click(screen.getByRole("button", { name: "New event" }));
    expect(p.onCreate).toHaveBeenCalledTimes(1);
  });

  it("lists calendars in the popover and toggling calls onChange", async () => {
    const p = setup();
    const trigger = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("aria-haspopup") === "dialog")!;
    await userEvent.click(trigger);
    expect(await screen.findByText("Town Hall")).toBeInTheDocument();
    expect(screen.getByText("Mine")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /Mine/ }));
    expect(p.onSelectedChange).toHaveBeenCalledWith(["c1", "c2"]);
    await userEvent.click(screen.getByRole("checkbox", { name: /Town Hall/ }));
    expect(p.onSelectedChange).toHaveBeenLastCalledWith([]);
  });
});
