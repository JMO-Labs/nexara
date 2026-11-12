/**
 * @file tests/unit/ui/Popover.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui";

// jsdom lacks ResizeObserver (used by Radix popper).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

describe("Popover", () => {
  it("opens content on trigger click", async () => {
    render(
      <Popover>
        <PopoverTrigger>open</PopoverTrigger>
        <PopoverContent>hello</PopoverContent>
      </Popover>,
    );
    expect(screen.queryByText("hello")).toBeNull();
    await userEvent.click(screen.getByText("open"));
    expect(await screen.findByText("hello")).toBeInTheDocument();
  });
});
