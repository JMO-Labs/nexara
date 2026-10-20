/**
 * @file tests/unit/ui/Checkbox.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Checkbox } from "@/components/ui";

describe("Checkbox", () => {
  it("toggles on click", async () => {
    render(<Checkbox aria-label="Agree" />);
    const cb = screen.getByRole("checkbox", { name: "Agree" });
    await userEvent.click(cb);
    expect(cb).toHaveAttribute("aria-checked", "true");
  });
});
