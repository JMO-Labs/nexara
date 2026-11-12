/**
 * @file tests/unit/admin/CSSEditor.test.tsx
 * @brief CSSEditor shows the security warning and propagates edits.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CSSEditor } from "@/components/admin/CSSEditor";

describe("CSSEditor", () => {
  it("shows the warning", () => {
    render(<CSSEditor value="" onChange={() => {}} />);
    expect(
      screen.getByText(/CSS can break site layout\. Use carefully\./),
    ).toBeInTheDocument();
  });

  it("calls onChange on typing", async () => {
    const onChange = vi.fn();
    render(<CSSEditor value="" onChange={onChange} />);
    await userEvent.type(screen.getByLabelText("Custom CSS"), "a");
    expect(onChange).toHaveBeenCalledWith("a");
  });
});
