/**
 * @file tests/unit/components/calendar/CalendarWidget.test.tsx
 * @brief CalendarWidget: day click/keyboard expands inline event list.
 */
import { describe, it, expect } from "vitest";
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

describe("CalendarWidget", () => {
  it("starts collapsed", () => {
    render(<CalendarWidget events={events} month={month} />);
    expect(day10().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Picnic")).toBeNull();
  });

  it("click expands the day's events and click again collapses", async () => {
    render(<CalendarWidget events={events} month={month} />);
    await userEvent.click(day10());
    expect(day10().getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Picnic")).toBeTruthy();
    await userEvent.click(day10());
    expect(day10().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Picnic")).toBeNull();
  });

  it("Enter and Space toggle", async () => {
    render(<CalendarWidget events={events} month={month} />);
    day10().focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByText("Picnic")).toBeTruthy();
    await userEvent.keyboard(" ");
    expect(screen.queryByText("Picnic")).toBeNull();
  });

  it("shows empty message for a day without events", async () => {
    render(<CalendarWidget events={events} month={month} />);
    await userEvent.click(screen.getByRole("button", { name: /January 11/ }));
    expect(screen.getByText(/no events/i)).toBeTruthy();
  });
});
