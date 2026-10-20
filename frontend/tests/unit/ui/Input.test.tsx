/**
 * @file tests/unit/ui/Input.test.tsx
 * @brief Input/Textarea label linking and error semantics.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";

describe("Input", () => {
  it("links label", () => {
    render(<Input label="Email" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("error sets aria-invalid and description", () => {
    render(<Input label="Email" error="Required" />);
    const el = screen.getByLabelText("Email");
    expect(el).toHaveAttribute("aria-invalid", "true");
    expect(el).toHaveAccessibleDescription("Required");
  });

  it("textarea mirrors behavior", () => {
    render(<Textarea label="Bio" error="Too short" />);
    const el = screen.getByLabelText("Bio");
    expect(el).toHaveAttribute("aria-invalid", "true");
    expect(el).toHaveAccessibleDescription("Too short");
  });
});
