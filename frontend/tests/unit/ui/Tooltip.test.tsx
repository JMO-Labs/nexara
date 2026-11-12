/**
 * @file tests/unit/ui/Tooltip.test.tsx
 * @brief Tooltip hover delay, focus behaviour and standalone fallback.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tooltip, TooltipProvider } from "@/components/ui/Tooltip";

function setupFake() {
  vi.useFakeTimers({ shouldAdvanceTime: false });
  return userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
}

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

  it("shows nothing on hover before 400ms, then shows content", async () => {
    const user = setupFake();
    render(tree);
    await user.hover(screen.getByText("btn"));
    act(() => {
      vi.advanceTimersByTime(399);
    });
    expect(screen.queryByRole("tooltip")).toBeNull();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByRole("tooltip")).toHaveTextContent("Save");
  });

  it("shows content immediately on keyboard focus", async () => {
    const user = setupFake();
    render(tree);
    await user.tab();
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
