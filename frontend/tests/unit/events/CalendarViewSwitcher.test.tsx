/**
 * @file tests/unit/events/CalendarViewSwitcher.test.tsx
 * @brief Tests for the calendar view switcher (month/week/day/list).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CalendarViewSwitcher } from "@/components/events/CalendarViewSwitcher";

describe("CalendarViewSwitcher", () => {
  it("renders 4 views with the current one checked", () => {
    render(<CalendarViewSwitcher value="month" onChange={vi.fn()} />);
    expect(
      screen.getByRole("radiogroup", { name: "Calendar view" }),
    ).toBeInTheDocument();
    for (const v of ["Month", "Week", "Day", "List"]) {
      expect(screen.getByRole("radio", { name: v })).toBeInTheDocument();
    }
    expect(screen.getByRole("radio", { name: "Month" })).toBeChecked();
  });

  it("marks the active view with the ink pill, not bg-accent", () => {
    render(<CalendarViewSwitcher value="week" onChange={vi.fn()} />);
    const cls = screen.getByRole("radio", { name: "Week" }).className;
    expect(cls).toContain("bg-surface-strong");
    expect(cls).not.toContain("bg-accent");
  });

  it("invokes onChange when another view is clicked", async () => {
    const onChange = vi.fn();
    render(<CalendarViewSwitcher value="month" onChange={onChange} />);
    await userEvent.setup().click(screen.getByRole("radio", { name: /week/i }));
    expect(onChange).toHaveBeenCalledWith("week");
  });
});
