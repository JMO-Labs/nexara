/**
 * @file tests/unit/events/MonthCalendar.test.tsx
 * @brief Day grid for a fixed month (fake timers) and navigation handlers.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { MonthCalendar } from "@/components/events/MonthCalendar";
import { TooltipProvider } from "@/components/ui";
import { renderWithProviders } from "../../utils/renderWithProviders";

const NOW = new Date(2026, 3, 15, 12, 0, 0);
const MONTH = new Date(2026, 3, 1);

function setup(onMonthChange = vi.fn()) {
  renderWithProviders(
    <TooltipProvider>
      <MonthCalendar events={[]} month={MONTH} onMonthChange={onMonthChange} />
    </TooltipProvider>,
  );
  return onMonthChange;
}

describe("MonthCalendar", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the month title and all 35 grid days for April 2026", () => {
    setup();
    expect(screen.getByText("April 2026")).toBeInTheDocument();
    // Grid runs Sun Mar 29 through Sat May 2.
    expect(screen.getAllByLabelText(/^\w+day, \w+ \d+$/)).toHaveLength(35);
    expect(screen.getByLabelText("Sunday, March 29")).toBeInTheDocument();
    expect(screen.getByLabelText("Wednesday, April 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Thursday, April 30")).toBeInTheDocument();
    expect(screen.getByLabelText("Saturday, May 2")).toBeInTheDocument();
  });

  it("highlights today via the fake clock", () => {
    setup();
    const today = screen.getByLabelText("Wednesday, April 15");
    expect(today.firstElementChild?.className).toContain("bg-accent");
    const other = screen.getByLabelText("Thursday, April 16");
    expect(other.firstElementChild?.className).not.toContain("bg-accent");
  });

  it("navigates to previous and next month", () => {
    const onChange = setup();
    fireEvent.click(screen.getByLabelText("Previous month"));
    expect(onChange).toHaveBeenLastCalledWith(new Date(2026, 2, 1));
    fireEvent.click(screen.getByLabelText("Next month"));
    expect(onChange).toHaveBeenLastCalledWith(new Date(2026, 4, 1));
  });

  it("Today button jumps to the current date", () => {
    const onChange = setup();
    fireEvent.click(screen.getByLabelText("Today"));
    expect(onChange).toHaveBeenCalledWith(NOW);
  });
});
