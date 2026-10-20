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
    for (const v of ["month", "week", "day", "list"]) {
      expect(
        screen.getByRole("radio", { name: new RegExp(v, "i") }),
      ).toBeInTheDocument();
    }
    expect(screen.getByRole("radio", { name: /month/i })).toBeChecked();
  });

  it("invokes onChange when another view is clicked", async () => {
    const onChange = vi.fn();
    render(<CalendarViewSwitcher value="month" onChange={onChange} />);
    await userEvent.setup().click(screen.getByRole("radio", { name: /week/i }));
    expect(onChange).toHaveBeenCalledWith("week");
  });

  it("does not deselect the active view", async () => {
    const onChange = vi.fn();
    render(<CalendarViewSwitcher value="month" onChange={onChange} />);
    await userEvent
      .setup()
      .click(screen.getByRole("radio", { name: /month/i }));
    expect(onChange).not.toHaveBeenCalled();
  });
});
