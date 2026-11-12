/**
 * @file tests/unit/feed/ComposerToolbar.test.tsx
 * @brief ComposerToolbar: ARIA labels and handlers.
 */
import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { ComposerToolbar } from "@/components/feed/ComposerToolbar";
import { renderWithProviders } from "../../utils/renderWithProviders";

describe("ComposerToolbar", () => {
  it("exposes labelled buttons; attach and poll are disabled", () => {
    renderWithProviders(
      <ComposerToolbar posting={false} onSubmit={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Attach media" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add poll" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Post" })).toBeInTheDocument();
  });

  it("fires onCancel and onSubmit", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    renderWithProviders(
      <ComposerToolbar
        posting={false}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    fireEvent.click(screen.getByRole("button", { name: "Post" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("does not submit while posting", () => {
    const onSubmit = vi.fn();
    renderWithProviders(
      <ComposerToolbar posting onSubmit={onSubmit} onCancel={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
