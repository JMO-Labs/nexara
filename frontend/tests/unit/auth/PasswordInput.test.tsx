/**
 * @file tests/unit/auth/PasswordInput.test.tsx
 * @brief Show/hide toggle flips the input type and its own label.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PasswordInput } from "@/components/auth/PasswordInput";

describe("PasswordInput", () => {
  it("reveals and hides the password", () => {
    render(<PasswordInput label="Password" />);
    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(input).toHaveAttribute("type", "text");
    const hide = screen.getByRole("button", { name: "Hide password" });
    expect(hide).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(hide);
    expect(input).toHaveAttribute("type", "password");
  });
});
