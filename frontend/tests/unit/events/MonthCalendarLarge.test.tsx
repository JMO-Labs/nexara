/**
 * @file tests/unit/events/MonthCalendarLarge.test.tsx
 * @brief Keyboard navigation and selection for the large month grid.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MonthCalendarLarge } from "@/components/events/MonthCalendarLarge";

function setup(onSelectDay = vi.fn()) {
  render(
    <MonthCalendarLarge
      events={[]}
      month={new Date(2026, 3, 1)}
      selectedDay={null}
      selectedEventId={null}
      subgroupNames={new Map()}
      onSelectDay={onSelectDay}
      onSelectEvent={() => {}}
    />,
  );
  return onSelectDay;
}

describe("MonthCalendarLarge keyboard", () => {
  it("arrow keys move focus between days", () => {
    setup();
    const start = screen.getByLabelText("Wednesday, April 15");
    start.focus();
    fireEvent.keyDown(start, { key: "ArrowRight" });
    expect(screen.getByLabelText("Thursday, April 16")).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "ArrowDown" });
    expect(screen.getByLabelText("Thursday, April 23")).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "ArrowLeft" });
    expect(screen.getByLabelText("Wednesday, April 22")).toHaveFocus();
  });

  it("Enter selects the focused day", () => {
    const onSelectDay = setup();
    const cell = screen.getByLabelText("Wednesday, April 15");
    fireEvent.keyDown(cell, { key: "Enter" });
    expect(onSelectDay).toHaveBeenCalledTimes(1);
    expect(onSelectDay.mock.calls[0][0].getDate()).toBe(15);
  });
});
