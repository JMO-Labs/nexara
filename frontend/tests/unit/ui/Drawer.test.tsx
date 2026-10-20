/**
 * @file tests/unit/ui/Drawer.test.tsx
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Drawer } from "@/components/ui/Drawer";

describe("Drawer", () => {
  it("renders a named dialog with focus inside", () => {
    render(
      <Drawer open onClose={() => {}} title="More" side="bottom">
        <button>inner</button>
      </Drawer>,
    );
    const dlg = screen.getByRole("dialog", { name: "More" });
    expect(dlg).toContainElement(document.activeElement as HTMLElement);
  });

  it("Escape calls onClose", async () => {
    const onClose = vi.fn();
    render(
      <Drawer open onClose={onClose} title="More" side="bottom">
        x
      </Drawer>,
    );
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
