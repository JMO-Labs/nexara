/**
 * @file tests/unit/ui/Tooltip.test.tsx
 * @brief Tooltip hover delay, focus behaviour and standalone fallback.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tooltip, TooltipProvider } from "@/components/ui/Tooltip";

/*
 * Fake-timer tests use sync fireEvent/focus: user-event's async wrapper
 * awaits a setTimeout(0) that vitest fake timers never flush (hangs).
 */

const tree = (
  <TooltipProvider>
    <Tooltip content="Save">
      <button>btn</button>
    </Tooltip>
  </TooltipProvider>
);

describe("Tooltip", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows nothing on hover before 400ms, then shows content", () => {
    vi.useFakeTimers();
    render(tree);
    fireEvent.pointerMove(screen.getByText("btn"));
    act(() => {
      vi.advanceTimersByTime(399);
    });
    expect(screen.queryByRole("tooltip")).toBeNull();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByRole("tooltip")).toHaveTextContent("Save");
  });

  it("shows content immediately on keyboard focus", () => {
    vi.useFakeTimers();
    render(tree);
    act(() => {
      screen.getByText("btn").focus();
    });
    expect(screen.getByRole("tooltip")).toHaveTextContent("Save");
  });

  it("works without an explicit provider", async () => {
    render(
      <Tooltip content="Save">
        <button>btn</button>
      </Tooltip>,
    );
    await userEvent.tab();
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Save");
  });
});
