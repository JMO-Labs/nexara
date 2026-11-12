/**
 * @file tests/unit/components/calendar/CalendarWidget.test.tsx
 * @brief CalendarWidget: day click/keyboard expands inline list; navigation.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CalendarWidget } from "@/components/calendar/CalendarWidget";

const events: any[] = [
  {
    id: "1",
    title: "Picnic",
    starts_at: "2025-01-10T12:00:00",
    ends_at: "2025-01-10T13:00:00",
  },
];
const month = new Date(2025, 0, 1);
const day10 = () => screen.getByRole("button", { name: /January 10/ });
const ui = (over = {}) => {
  const p = {
    events,
    month,
    onMonthChange: vi.fn(),
    onSelectEvent: vi.fn(),
    ...over,
  };
  render(<CalendarWidget {...p} />);
  return p;
};

describe("CalendarWidget", () => {
  it("starts collapsed", () => {
    ui();
    expect(day10().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Picnic")).toBeNull();
  });

  it("click expands the day's events and click again collapses", async () => {
    ui();
    await userEvent.click(day10());
    expect(day10().getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Picnic")).toBeTruthy();
    await userEvent.click(day10());
    expect(day10().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Picnic")).toBeNull();
  });

  it("Enter and Space toggle", async () => {
    ui();
    day10().focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByText("Picnic")).toBeTruthy();
    await userEvent.keyboard(" ");
    expect(screen.queryByText("Picnic")).toBeNull();
  });

  it("shows empty message for a day without events", async () => {
    ui();
    await userEvent.click(screen.getByRole("button", { name: /January 11/ }));
    expect(screen.getByText(/no events/i)).toBeTruthy();
  });

  it("expanded event item selects the event", async () => {
    const p = ui();
    await userEvent.click(day10());
    await userEvent.click(screen.getByRole("button", { name: "Picnic" }));
    expect(p.onSelectEvent).toHaveBeenCalledWith(events[0]);
  });

  it("prev/next navigate months", async () => {
    const p = ui();
    await userEvent.click(
      screen.getByRole("button", { name: /previous month/i }),
    );
    expect(p.onMonthChange).toHaveBeenCalledWith(new Date(2024, 11, 1));
    await userEvent.click(screen.getByRole("button", { name: /next month/i }));
    expect(p.onMonthChange).toHaveBeenCalledWith(new Date(2025, 1, 1));
  });
});
