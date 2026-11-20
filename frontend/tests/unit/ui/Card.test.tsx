/**
 * @file tests/unit/ui/Card.test.tsx
 * @brief Card glass-item surface.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "@/components/ui/Card";

describe("Card", () => {
  it("uses the glass-item surface with rounded-[24px]", () => {
    render(<Card data-testid="c">x</Card>);
    expect(screen.getByTestId("c")).toHaveClass("glass-item", "rounded-[24px]");
  });
});
