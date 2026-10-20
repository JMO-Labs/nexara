/**
 * @file tests/unit/ui/Tooltip.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tooltip, TooltipProvider } from "@/components/ui/Tooltip";

// jsdom lacks ResizeObserver (used by Radix popper).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

describe("Tooltip", () => {
  it("shows content on hover", async () => {
    render(
      <TooltipProvider>
        <Tooltip content="Save">
          <button>btn</button>
        </Tooltip>
      </TooltipProvider>,
    );
    await userEvent.hover(screen.getByText("btn"));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Save");
  });

  it("shows content on keyboard focus", async () => {
    render(
      <TooltipProvider>
        <Tooltip content="Save">
          <button>btn</button>
        </Tooltip>
      </TooltipProvider>,
    );
    await userEvent.tab();
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Save");
  });
});
