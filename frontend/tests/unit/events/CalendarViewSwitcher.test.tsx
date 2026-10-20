/**
 * @file tests/unit/events/CalendarViewSwitcher.test.tsx
 * @brief Tests for the calendar view switcher (month/week/day/list).
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { CalendarViewSwitcher } from "@/components/events/CalendarViewSwitcher";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("CalendarViewSwitcher", () => {
  it("renders 4 view buttons", () => {
    const onChange = vi.fn();
    wrap(<CalendarViewSwitcher value="month" onChange={onChange} />);
    expect(screen.getByRole("button", { name: /month/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /week/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /day/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /list/i })).toBeInTheDocument();
  });

  it("invokes onChange when a button is clicked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    wrap(<CalendarViewSwitcher value="month" onChange={onChange} />);
    const weekBtn = screen.getByRole("button", { name: /week/i });
    await user.click(weekBtn);
    expect(onChange).toHaveBeenCalledWith("week");
  });
});
