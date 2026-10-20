/**
 * @file tests/unit/ui/Card.test.tsx
 * @brief Card tones.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "@/components/ui/Card";

describe("Card", () => {
  it("default tone uses surface background", () => {
    render(<Card data-testid="c">x</Card>);
    expect(screen.getByTestId("c").className).toContain("bg-surface");
    expect(screen.getByTestId("c").className).not.toContain("corner-leaf");
  });

  it("featured tone has corner-leaf", () => {
    render(
      <Card tone="featured" data-testid="c">
        x
      </Card>,
    );
    expect(screen.getByTestId("c")).toHaveClass("corner-leaf");
  });
});
