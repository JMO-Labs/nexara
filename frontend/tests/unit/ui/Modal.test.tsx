/**
 * @file tests/unit/ui/Modal.test.tsx
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "@/components/ui/Modal";

describe("Modal", () => {
  it("renders a named dialog with focus inside", () => {
    render(
      <Modal open onClose={() => {}} title="Edit">
        <button>inner</button>
      </Modal>,
    );
    const dlg = screen.getByRole("dialog", { name: "Edit" });
    expect(dlg).toContainElement(document.activeElement as HTMLElement);
  });

  it("Escape calls onClose", async () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Edit">
        x
      </Modal>,
    );
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
