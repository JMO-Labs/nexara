/**
 * @file tests/unit/ui/page/Toolbar.test.tsx
 * @brief Toolbar glass row.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Toolbar } from "@/components/ui/page";

describe("Toolbar", () => {
  it("renders children in a glass row", () => {
    render(
      <Toolbar className="x" data-testid="tb">
        <span>child</span>
      </Toolbar>,
    );
    const el = screen.getByTestId("tb");
    expect(el).toHaveClass("glass", "rounded-full", "flex-wrap", "x");
    expect(screen.getByText("child")).toBeInTheDocument();
  });
});
