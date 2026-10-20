/**
 * @file tests/unit/ui/Switch.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Switch } from "@/components/ui";

describe("Switch", () => {
  it("toggles on click", async () => {
    render(<Switch aria-label="Notify" />);
    const sw = screen.getByRole("switch", { name: "Notify" });
    expect(sw).toHaveAttribute("aria-checked", "false");
    await userEvent.click(sw);
    expect(sw).toHaveAttribute("aria-checked", "true");
  });
});
