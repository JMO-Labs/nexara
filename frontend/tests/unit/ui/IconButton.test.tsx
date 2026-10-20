/**
 * @file tests/unit/ui/IconButton.test.tsx
 * @brief IconButton exposes its aria-label as accessible name.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IconButton } from "@/components/ui/IconButton";

describe("IconButton", () => {
  it("is named by aria-label", () => {
    render(<IconButton aria-label="Close">x</IconButton>);
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });
});
