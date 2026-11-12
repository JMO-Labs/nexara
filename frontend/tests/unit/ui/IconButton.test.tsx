/**
 * @file tests/unit/ui/IconButton.test.tsx
 * @brief IconButton accessible name and optional tooltip.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IconButton } from "@/components/ui/IconButton";
import { TooltipProvider } from "@/components/ui/Tooltip";

describe("IconButton", () => {
  it("is named by aria-label", () => {
    render(<IconButton aria-label="Close">x</IconButton>);
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });

  it("shows no tooltip when tooltip prop is absent", async () => {
    render(
      <TooltipProvider>
        <IconButton aria-label="Close">x</IconButton>
      </TooltipProvider>,
    );
    await userEvent.tab();
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("shows tooltip with shortcut on keyboard focus", async () => {
    render(
      <TooltipProvider>
        <IconButton aria-label="Search" tooltip="Search" shortcut="Ctrl+K">
          x
        </IconButton>
      </TooltipProvider>,
    );
    await userEvent.tab();
    const tip = await screen.findByRole("tooltip");
    expect(tip).toHaveTextContent("Search");
    expect(tip).toHaveTextContent("Ctrl+K");
  });

  it("shows tooltip on hover", async () => {
    render(
      <TooltipProvider>
        <IconButton aria-label="Close" tooltip="Close dialog">
          x
        </IconButton>
      </TooltipProvider>,
    );
    await userEvent.hover(screen.getByRole("button", { name: "Close" }));
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Close dialog",
    );
  });
});
